import asyncio
import functools
import itertools
import logging
import time
from typing import Any

from eth_typing import ChecksumAddress, HexStr
from eth_utils import to_checksum_address
from web3 import AsyncHTTPProvider, AsyncWeb3, HTTPProvider, Web3
from web3.contract.contract import ContractFunction
from web3.exceptions import ContractLogicError
from web3.types import BlockIdentifier

from .abi import multicall2_abi, multicall3_abi
from .call import Call, decode_return_data
from .constants import (
    MAX_GAS_LIMIT,
    MULTICALL2_ADDRESSES,
    MULTICALL2_BYTECODE,
    MULTICALL3_ADDRESSES,
    MULTICALL3_BYTECODE,
    NO_STATE_OVERRIDE,
)
from .exceptions import MaxRetriesExceeded

logger = logging.getLogger(__name__)


class Multicall:
    def __init__(
        self,
        provider_url: str | None = None,
        batch: int = 100,
        max_retries: int = 3,
        gas_limit: int = 15_000_000,
        _semaphore: int = 1000,
    ):
        self.web3 = Web3(HTTPProvider(provider_url))
        self.async_web3 = AsyncWeb3(AsyncHTTPProvider(provider_url))

        self.batch = batch
        self.max_retries = max_retries
        self._semaphore = _semaphore
        self.gas_limit = gas_limit

        self.chain_id: int = self.web3.eth.chain_id
        if self.chain_id in MULTICALL3_ADDRESSES:
            self.async_contract = self.async_web3.eth.contract(
                address=to_checksum_address(MULTICALL3_ADDRESSES[self.chain_id]), abi=multicall3_abi
            )
            self.version = 3
        elif self.chain_id in MULTICALL2_ADDRESSES:
            self.async_contract = self.async_web3.eth.contract(
                address=to_checksum_address(MULTICALL2_ADDRESSES[self.chain_id]), abi=multicall2_abi
            )
            self.version = 2
        else:
            raise ValueError("Connected to unknown chain id!")

        if self.chain_id in MAX_GAS_LIMIT:
            logger.info("Using network max gas limit")
            self.gas_limit = MAX_GAS_LIMIT[self.chain_id]

    def aggregate(
        self,
        calls: list[ContractFunction],
        block_identifier: BlockIdentifier = "latest",
        use_try: bool = False,
        addresses: list[ChecksumAddress] | None = None,
    ) -> list[Any]:
        """
        Calls aggregate or tryAggregate on web3multicall but lets user (optionally) specify a list of target addresses
        corresponding to each ContractFunction. This is useful to optimize in cases where we might only want to load
        a few abis with function signatures but call the same functions on different contracts using the same ABI.
        (ContractFunction is heavy to instantiate)

        :param calls: list of contract function calls with parameters
        :param block_identifier: web3 block identifier
        :param use_try: use aggregate or tryAggregate
        :param addresses: optional list of target addresses corresponding to a list of calls
        :return: result of aggregation
        """
        start = time.time()
        result = asyncio.run(
            self._aggregate(calls, use_try=use_try, block_identifier=block_identifier, target_address_list=addresses)
        )
        logger.debug(f"Multicall took {time.time() - start} seconds")
        return result

    async def async_aggregate(
        self,
        calls: list[ContractFunction],
        block_identifier: BlockIdentifier = "latest",
        use_try: bool = False,
        addresses: list[ChecksumAddress] | None = None,
    ) -> list[Any]:
        """
        Calls aggregate or tryAggregate on web3multicall but lets user (optionally) specify a list of target addresses
        corresponding to each ContractFunction. This is useful to optimize in cases where we might only want to load
        a few abis with function signatures but call the same functions on different contracts using the same ABI.
        (ContractFunction is heavy to instantiate)

        :param calls: list of contract function calls with parameters
        :param block_identifier: web3 block identifier
        :param use_try: use aggregate or tryAggregate
        :param addresses: optional list of target addresses corresponding to a list of calls
        :return: result of aggregation
        """
        start = time.time()
        result = await self._aggregate(
            calls, use_try=use_try, block_identifier=block_identifier, target_address_list=addresses
        )
        logger.debug(f"Multicall took {time.time() - start} seconds")
        return result

    def _call_parameters(self, block_identifier: BlockIdentifier):
        parameters = {"transaction": {"gas": self.gas_limit}, "block_identifier": block_identifier}

        # always override if possible
        if self.chain_id not in NO_STATE_OVERRIDE:
            parameters["state_override"] = {
                self.async_contract.address: {"code": MULTICALL3_BYTECODE if self.version == 3 else MULTICALL2_BYTECODE}
            }
        return parameters

    async def _call_aggregate(
        self,
        use_try: bool,
        call_data: list[tuple[ChecksumAddress, HexStr]],
        block_identifier: BlockIdentifier,
    ) -> tuple[int, bytes | bytearray] | bytes | bytearray:
        if use_try:
            return await self.async_contract.functions.tryAggregate(False, call_data).call(
                **self._call_parameters(block_identifier)
            )
        return await self.async_contract.functions.aggregate(call_data).call(**self._call_parameters(block_identifier))

    async def _parse_aggregate(
        self,
        use_try: bool,
        call_data: list[tuple[ChecksumAddress, HexStr]],
        return_types: list[list[str]],
        block_identifier: BlockIdentifier,
    ) -> list:
        result = await self._call_aggregate(use_try, call_data, block_identifier)

        output_data = []
        if use_try:
            successes, results = list(map(list, zip(*result)))

            for success, result, return_type in zip(successes, results, return_types):
                if not success:
                    output_data.append(None)
                else:
                    output_data.append(decode_return_data(result, return_type, self.web3.codec))
        else:
            _, results = result
            for result, return_type in zip(results, return_types):
                output_data.append(decode_return_data(result, return_type, self.web3.codec))

        return output_data

    async def _aggregate(
        self,
        call_list: list[ContractFunction],
        use_try: bool,
        block_identifier: BlockIdentifier,
        target_address_list: list[ChecksumAddress] | None = None,
    ) -> list:
        if target_address_list:
            assert len(target_address_list) == len(call_list), "Lists of addresses and calls should have same length."

        call = Call(call_list, target_address_list)
        batch = self.batch
        retries = 0
        tasks = []

        for i in range(0, len(call.encoded_data), batch):
            call_data = call.encoded_data[i : i + batch]
            return_types = call.return_types[i : i + batch]
            tasks.append(functools.partial(self._parse_aggregate, use_try, call_data, return_types, block_identifier))

        while True:
            if retries > self.max_retries - 1:
                raise MaxRetriesExceeded(f"Failed to call web3multicall after {retries} attempts.")

            task_group = asyncio.gather(*[t() for t in tasks])
            async with asyncio.Semaphore(self._semaphore):
                try:
                    results = await task_group

                except (ContractLogicError, ValueError) as e:
                    logger.error(f"Error calling web3multicall:'{e}', retrying")
                    task_group.cancel()
                    retries += 1
                    continue

            return list(itertools.chain(*results))
