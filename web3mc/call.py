import logging
from functools import cached_property
from typing import Any

from eth_abi.codec import ABICodec
from eth_abi.exceptions import DecodingError
from eth_typing import ChecksumAddress, HexStr
from web3.contract.contract import ContractFunction
from web3.contract.utils import BASE_RETURN_NORMALIZERS, get_abi_output_types, map_abi_data

logger = logging.getLogger(__name__)


class Call:
    def __init__(self, calls: list[ContractFunction], addresses: list[ChecksumAddress] | None):
        self.calls = calls
        self.addresses = addresses

    @cached_property
    def encoded_data(self) -> list[tuple[ChecksumAddress, HexStr]]:
        if self.addresses:
            return [(address, call._encode_transaction_data()) for address, call in zip(self.addresses, self.calls)]
        return [(call.address, call._encode_transaction_data()) for call in self.calls]

    @cached_property
    def return_types(self) -> list[list[str]]:
        return [get_abi_output_types(call.abi) for call in self.calls]


def decode_return_data(return_data: bytes | bytearray, return_type: list[str], codec: ABICodec) -> Any | None:
    try:
        decoded_data = codec.decode(return_type, return_data)
        normalized_data = map_abi_data(BASE_RETURN_NORMALIZERS, return_type, decoded_data)
        if len(normalized_data) == 1:
            return normalized_data[0]
        else:
            return normalized_data
    except DecodingError as e:
        logger.error(f"Failed to decode {return_data} as {return_type}: {e}")
    return None
