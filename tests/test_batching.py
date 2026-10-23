import asyncio
from collections import Counter
from unittest.mock import AsyncMock, patch

import pytest
from web3.eth import Eth
from web3.exceptions import Web3RPCError

from web3mc import Multicall
from web3mc.exceptions import MaxRetriesExceeded


@pytest.fixture
def make_multicall(monkeypatch):
    monkeypatch.setattr(Eth, "chain_id", property(lambda self: 1))
    return Multicall


@pytest.fixture
def multicall(make_multicall):
    return make_multicall(batch=1)


def make_calls(multicall, count):
    contract = multicall.web3.eth.contract(
        address="0x0000000000000000000000000000000000000001",
        abi=[
            {
                "name": "echo",
                "type": "function",
                "stateMutability": "view",
                "inputs": [{"name": "value", "type": "uint256"}],
                "outputs": [{"name": "", "type": "uint256"}],
            }
        ],
    )
    return [contract.functions.echo(value) for value in range(count)]


def batch_values(multicall, call_data):
    return [multicall.web3.codec.decode(["uint256"], bytes.fromhex(data[10:]))[0] for _, data in call_data]


@pytest.mark.parametrize("use_try", [False, True])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_rpc_error_retries_through_web3(multicall, use_try, asynchronous):
    multicall.async_web3.middleware_onion.clear()
    encoded_value = multicall.web3.codec.encode(["uint256"], [42])
    if use_try:
        encoded_result = multicall.web3.codec.encode(["(bool,bytes)[]"], [[(True, encoded_value)]])
    else:
        encoded_result = multicall.web3.codec.encode(["uint256", "bytes[]"], [123, [encoded_value]])
    error_response = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32005, "message": "temporarily overloaded"}}
    request = AsyncMock(
        side_effect=[error_response, error_response, {"jsonrpc": "2.0", "id": 1, "result": "0x" + encoded_result.hex()}]
    )
    multicall.async_web3.provider.make_request = request
    calls = make_calls(multicall, 1)

    if asynchronous:
        result = asyncio.run(multicall.async_aggregate(calls, use_try=use_try))
    else:
        result = multicall.aggregate(calls, use_try=use_try)

    assert result == [42]
    assert request.await_count == 3
    assert all(call.args[0] == "eth_call" for call in request.await_args_list)


def test_rpc_retry_exhaustion_preserves_cause(multicall):
    error = Web3RPCError("temporarily overloaded")
    multicall._call_aggregate = AsyncMock(side_effect=error)

    with pytest.raises(MaxRetriesExceeded, match="after 3 attempts") as exc:
        multicall.aggregate(make_calls(multicall, 1))

    assert multicall._call_aggregate.await_count == 3
    assert exc.value.__cause__ is error


@pytest.mark.parametrize("limit", [1, 2])
def test_concurrency_limit_and_result_order(make_multicall, limit):
    multicall = make_multicall(batch=1, _semaphore=limit)
    active = peak = 0

    async def parse(use_try, call_data, return_types, block_identifier):
        nonlocal active, peak
        values = batch_values(multicall, call_data)
        active += 1
        peak = max(peak, active)
        try:
            # Later batches finish sooner when the concurrency limit permits it.
            await asyncio.sleep((5 - values[0]) * 0.001)
            return values
        finally:
            active -= 1

    multicall._parse_aggregate = parse
    assert multicall.aggregate(make_calls(multicall, 5)) == list(range(5))
    assert peak == limit
    assert active == 0
    # The same object must also work across successive asyncio.run event loops.
    assert multicall.aggregate(make_calls(multicall, 5)) == list(range(5))


def test_retry_waits_for_previous_batches_to_cancel(make_multicall):
    multicall = make_multicall(batch=1, _semaphore=2)

    async def scenario():
        sibling_started = asyncio.Event()
        sibling_cancelled = asyncio.Event()
        attempts = Counter()

        async def parse(use_try, call_data, return_types, block_identifier):
            value = batch_values(multicall, call_data)[0]
            attempts[value] += 1
            if attempts[value] == 1:
                if value == 0:
                    await sibling_started.wait()
                    raise ValueError("temporary failure")
                sibling_started.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    await asyncio.sleep(0)
                    sibling_cancelled.set()
            assert sibling_cancelled.is_set(), "A retry started before the previous attempt finished cancellation"
            return [value]

        multicall._parse_aggregate = parse
        result = await asyncio.wait_for(multicall.async_aggregate(make_calls(multicall, 2)), timeout=2)
        assert result == [0, 1]
        assert attempts == {0: 2, 1: 2}
        assert sibling_cancelled.is_set()

    asyncio.run(scenario())


@pytest.mark.parametrize("error_type", [RuntimeError, Web3RPCError])
def test_error_cancels_and_drains_other_batches(make_multicall, error_type):
    multicall = make_multicall(batch=1, max_retries=1, _semaphore=2)

    async def scenario():
        sibling_started = asyncio.Event()
        sibling_cancelled = asyncio.Event()
        error = error_type("failed")

        async def parse(use_try, call_data, return_types, block_identifier):
            if batch_values(multicall, call_data)[0] == 0:
                await sibling_started.wait()
                raise error
            sibling_started.set()
            try:
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                sibling_cancelled.set()

        multicall._parse_aggregate = parse
        expected_error = MaxRetriesExceeded if error_type is Web3RPCError else RuntimeError
        with pytest.raises(expected_error):
            await asyncio.wait_for(multicall.async_aggregate(make_calls(multicall, 2)), timeout=2)
        assert sibling_cancelled.is_set()

    asyncio.run(scenario())


def test_caller_cancellation_drains_batches(make_multicall):
    multicall = make_multicall(batch=1, _semaphore=1)

    async def scenario():
        started = asyncio.Event()
        cancelled = asyncio.Event()
        requests = 0

        async def parse(*args):
            nonlocal requests
            requests += 1
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                cancelled.set()

        multicall._parse_aggregate = parse
        task = asyncio.create_task(multicall.async_aggregate(make_calls(multicall, 2)))
        await asyncio.wait_for(started.wait(), timeout=2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=2)
        assert cancelled.is_set()
        assert requests == 1

    asyncio.run(scenario())


@pytest.mark.parametrize("setting", ["batch", "max_retries", "_semaphore"])
@pytest.mark.parametrize("value", [0, -1, 1.5, True])
def test_invalid_settings_fail_before_connecting(setting, value):
    with patch("web3mc.multicall.HTTPProvider", side_effect=AssertionError("Must validate before connecting")):
        with pytest.raises(ValueError, match=f"{setting} must be a positive integer"):
            Multicall(**{setting: value})


@pytest.mark.parametrize("setting", ["batch", "max_retries", "_semaphore"])
def test_invalid_mutated_settings(multicall, setting):
    setattr(multicall, setting, -1)
    with pytest.raises(ValueError, match=f"{setting} must be a positive integer"):
        multicall.aggregate(make_calls(multicall, 1))


@pytest.mark.parametrize("use_try", [False, True])
def test_empty_calls_do_not_send_requests(multicall, use_try):
    multicall._call_aggregate = AsyncMock()
    assert multicall.aggregate([], use_try=use_try) == []
    multicall._call_aggregate.assert_not_awaited()
