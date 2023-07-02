from unittest.mock import patch

import pytest
from eth_utils import to_checksum_address
from web3.constants import ADDRESS_ZERO

from web3mc import Multicall
from web3mc.abi import multicall2_abi
from web3mc.auto import multicall
from web3mc.constants import MULTICALL2_ADDRESSES
from web3mc.exceptions import MaxRetriesExceeded


class TestAggregate:
    @pytest.mark.parametrize("use_try", (True, False))
    def test_single(self, weth, use_try):
        calls = [weth.functions.name(), weth.functions.symbol(), weth.functions.decimals()]
        assert multicall.aggregate(calls, use_try=use_try) == ["Wrapped Ether", "WETH", 18]

    @pytest.mark.parametrize("use_try", (True, False))
    def test_single(self, weth, use_try):
        calls = [
            weth.functions.name(),
            weth.functions.symbol(),
            weth.functions.decimals(),
            weth.functions.balanceOf(ADDRESS_ZERO),
            weth.functions.allowance(ADDRESS_ZERO, ADDRESS_ZERO),
        ]
        result = multicall.aggregate(calls, use_try=use_try)

        assert len(result) == 5
        assert result[:3] == ["Wrapped Ether", "WETH", 18]

    @pytest.mark.parametrize("use_try", (True, False))
    def test_multiple(self, weth, wbtc, use_try):
        calls = [
            weth.functions.name(),
            weth.functions.symbol(),
            weth.functions.decimals(),
            wbtc.functions.name(),
            wbtc.functions.symbol(),
            wbtc.functions.decimals(),
        ]
        assert multicall.aggregate(calls, use_try=use_try) == ["Wrapped Ether", "WETH", 18, "Wrapped BTC", "WBTC", 8]

    @pytest.mark.parametrize("use_try", (True, False))
    def test_multiple_with_address(self, weth, wbtc, dai, usdc, usdt, use_try):
        calls = [weth.functions.name(), weth.functions.symbol(), weth.functions.decimals()] * 5
        addresses = (
            [weth.address] * 3 + [wbtc.address] * 3 + [dai.address] * 3 + [usdc.address] * 3 + [usdt.address] * 3
        )
        assert multicall.aggregate(calls, use_try=use_try, addresses=addresses) == [
            "Wrapped Ether",
            "WETH",
            18,
            "Wrapped BTC",
            "WBTC",
            8,
            "Dai Stablecoin",
            "DAI",
            18,
            "USD Coin",
            "USDC",
            6,
            "Tether USD",
            "USDT",
            6,
        ]

    @pytest.mark.parametrize("use_try", (True, False))
    @pytest.mark.parametrize("block_number", (17_000_000, 8_000_000))
    def test_block_number(self, weth, wbtc, block_number, use_try):
        calls = [
            weth.functions.name(),
            weth.functions.symbol(),
            weth.functions.decimals(),
            wbtc.functions.name(),
            wbtc.functions.symbol(),
            wbtc.functions.decimals(),
        ]
        assert multicall.aggregate(calls, block_identifier=block_number) == [
            "Wrapped Ether",
            "WETH",
            18,
            "Wrapped BTC",
            "WBTC",
            8,
        ]

    @pytest.mark.parametrize("use_try", (True, False))
    def test_return_list(self, weth, test_contract, use_try):
        user = test_contract.functions.loans(0).call()
        calls = [
            weth.functions.name(),
            weth.functions.symbol(),
            weth.functions.decimals(),
            test_contract.functions.user_state(user),
        ]

        result = multicall.aggregate(calls, use_try=use_try)
        assert len(result) == 4
        assert type(result[3]) == list

    @pytest.mark.parametrize("use_try", (True, False))
    def test_fail(self, weth, test_contract, use_try):
        calls = [
            weth.functions.name(),
            weth.functions.symbol(),
            weth.functions.decimals(),
            test_contract.functions.health("0x1234567891011121314151617181920212223242", False),
        ]

        if use_try:
            res = multicall.aggregate(calls, use_try=True)
            assert res == ["Wrapped Ether", "WETH", 18, None]

        else:
            with pytest.raises(MaxRetriesExceeded):
                multicall.aggregate(calls)

    @pytest.mark.parametrize("use_try", (True, False))
    def test_multiple_batches(self, weth, wbtc, dai, usdc, usdt, use_try):
        m = Multicall(batch=3)

        calls = [weth.functions.name(), weth.functions.symbol(), weth.functions.decimals()] * 5
        addresses = (
            [weth.address] * 3 + [wbtc.address] * 3 + [dai.address] * 3 + [usdc.address] * 3 + [usdt.address] * 3
        )
        assert m.aggregate(calls, use_try=use_try, addresses=addresses) == [
            "Wrapped Ether",
            "WETH",
            18,
            "Wrapped BTC",
            "WBTC",
            8,
            "Dai Stablecoin",
            "DAI",
            18,
            "USD Coin",
            "USDC",
            6,
            "Tether USD",
            "USDT",
            6,
        ]

    @pytest.mark.parametrize("use_try", (True, False))
    def test_call_different_length(self, weth, use_try):
        calls = [
            weth.functions.name(),
            weth.functions.symbol(),
            weth.functions.decimals(),
            weth.functions.name(),
            weth.functions.symbol(),
            weth.functions.decimals(),
        ]
        addresses = [weth.address] * 3

        with pytest.raises(AssertionError) as e:
            _ = multicall.aggregate(calls, use_try=use_try, addresses=addresses)

            assert str(e) == "Lists of addresses and calls should have same length."

    @pytest.mark.parametrize("use_try", (True, False))
    def test_v2(self, weth, use_try):
        calls = [weth.functions.name(), weth.functions.symbol(), weth.functions.decimals()]

        with patch.object(
            multicall,
            "async_contract",
            multicall.async_web3.eth.contract(
                address=to_checksum_address(MULTICALL2_ADDRESSES[multicall.chain_id]), abi=multicall2_abi
            ),
        ):
            assert multicall.async_contract.address == "0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696"
            assert multicall.aggregate(calls, use_try=use_try) == ["Wrapped Ether", "WETH", 18]
