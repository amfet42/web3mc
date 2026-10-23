# web3mc - multicall library for web3py

Based on makerdao's [multicall contract](https://github.com/makerdao/multicall)and
[brownie](https://github.com/eth-brownie/brownie) implementation with batching and asynchronous support. Works
directly with web3py contract functions and parameters

## Installation

```shell
pip install web3mc
```

## Quickstart

Basic usage

(this is default value if empty - set by web3py)
```shell
export WEB3_HTTP_PROVIDER_URI=http://localhost:8545
```

```python
from web3.auto import w3
from web3mc.auto import multicall

abi = [{"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "payable": False,
        "stateMutability": "view", "type": "function", },
       {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "payable": False,
        "stateMutability": "view", "type": "function", },
       {"constant": True, "inputs": [{"name": "", "type": "address"}], "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}], "payable": False, "stateMutability": "view", "type": "function"}]

weth_erc20 = w3.eth.contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", abi=abi)

calls = [weth_erc20.functions.name(), weth_erc20.functions.symbol(), weth_erc20.functions.balanceOf("vitalik.eth")]

result = multicall.aggregate(calls)
print(result)  # ['Wrapped Ether', 'WETH', 26992040046283229929]
```

Call multiple contracts with same abi (implementation)

```python
...
weth_erc20 = w3.eth.contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", abi=abi)

calls = [weth_erc20.functions.name(),weth_erc20.functions.symbol(),weth_erc20.functions.balanceOf("vitalik.eth")] * 2
# WBTC, USDC
addresses = ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"] * 3 + ["0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599"] * 3

result = multicall.aggregate(calls, use_try=True, addresses=addresses)  # tryAggregate()
print(result)  # ['Wrapped BTC', 'WBTC', 0, 'USD Coin', 'USDC', 396267093705]

```

## Parameters

### Environment variable

- `WEB3_HTTP_PROVIDER_URI` - can be overwritten directly (from web3py)

### Custom parameters

```python
from web3mc import Multicall

multicall = Multicall(
    provider_url="<your custom provider url>",  # Overrides env parameter
    batch=100,  # maximum calls per batch; must be a positive integer
    max_retries=3,  # maximum total attempts, including the first attempt
    gas_limit=15_000_000,  # gas limit for calls
    _semaphore=1000,  # maximum concurrent batches per aggregate call
)

```

`batch`, `max_retries`, and `_semaphore` must be positive integers. Failed attempts
cancel and await outstanding batches before retrying. Results retain input order.

## Testing
Install the locked dependencies and run the offline regression tests:

```shell
poetry install
poetry run pytest tests -m "not integration"
```

To run the full suite, set `WEB3_HTTP_PROVIDER_URI` to an Ethereum mainnet RPC endpoint:

```shell
export WEB3_HTTP_PROVIDER_URI=https://your-ethereum-rpc-endpoint
poetry run pytest tests
```

Integration tests are skipped when the endpoint is unset. Historical-block tests require
archive data and support for state overrides; RPC errors are reported as failures.
