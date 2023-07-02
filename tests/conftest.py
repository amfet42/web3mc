import pytest
from web3.auto import w3


@pytest.fixture(scope="module")
def abi():
    return [
        {
            "constant": True,
            "inputs": [],
            "name": "name",
            "outputs": [{"name": "", "type": "string"}],
            "payable": False,
            "stateMutability": "view",
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [],
            "name": "totalSupply",
            "outputs": [{"name": "", "type": "uint256"}],
            "payable": False,
            "stateMutability": "view",
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "payable": False,
            "stateMutability": "view",
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [{"name": "", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "", "type": "uint256"}],
            "payable": False,
            "stateMutability": "view",
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [],
            "name": "symbol",
            "outputs": [{"name": "", "type": "string"}],
            "payable": False,
            "stateMutability": "view",
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [{"name": "", "type": "address"}, {"name": "", "type": "address"}],
            "name": "allowance",
            "outputs": [{"name": "", "type": "uint256"}],
            "payable": False,
            "stateMutability": "view",
            "type": "function",
        },
    ]


@pytest.fixture(scope="module")
def weth(abi):
    return w3.eth.contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", abi=abi)


@pytest.fixture(scope="module")
def wbtc(abi):
    return w3.eth.contract("0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", abi=abi)


@pytest.fixture(scope="module")
def dai(abi):
    return w3.eth.contract("0x6B175474E89094C44Da98b954EedeAC495271d0F", abi=abi)


@pytest.fixture(scope="module")
def usdc(abi):
    return w3.eth.contract("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", abi=abi)


@pytest.fixture(scope="module")
def usdt(abi):
    return w3.eth.contract("0xdAC17F958D2ee523a2206206994597C13D831ec7", abi=abi)


@pytest.fixture(scope="module")
def test_contract():
    abi = [
        {
            "stateMutability": "view",
            "type": "function",
            "name": "health",
            "inputs": [{"name": "user", "type": "address"}, {"name": "full", "type": "bool"}],
            "outputs": [{"name": "", "type": "int256"}],
        },
        {
            "stateMutability": "view",
            "type": "function",
            "name": "loans",
            "inputs": [{"name": "arg0", "type": "uint256"}],
            "outputs": [{"name": "", "type": "address"}],
        },
        {
            "stateMutability": "view",
            "type": "function",
            "name": "user_state",
            "inputs": [{"name": "user", "type": "address"}],
            "outputs": [{"name": "", "type": "uint256[4]"}],
        },
    ]
    return w3.eth.contract("0x8472A9A7632b173c8Cf3a86D3afec50c35548e76", abi=abi)
