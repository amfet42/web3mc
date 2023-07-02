from web3.auto import w3

from web3mc.auto import multicall

abi = [
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
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
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
]


def main():
    weth = w3.eth.contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", abi=abi)
    wbtc = w3.eth.contract("0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", abi=abi)

    calls = [
        weth.functions.name(),
        weth.functions.symbol(),
        weth.functions.balanceOf("vitalik.eth"),
        wbtc.functions.name(),
        wbtc.functions.symbol(),
        wbtc.functions.balanceOf("vitalik.eth"),
    ]

    results = multicall.aggregate(calls)
    print(results)  # something like ['Wrapped Ether', 'WETH', 26992040046283229929, 'Wrapped BTC', 'WBTC', 0]

    # <-------------------------  Another way ------------------------->
    # only weth contract is initialized
    calls = [
        weth.functions.name(),
        weth.functions.symbol(),
        weth.functions.balanceOf("vitalik.eth"),
    ] * 2
    addresses = ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"] * 3 + ["0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599"] * 3

    results = multicall.aggregate(calls, addresses=addresses)
    print(results)  # something like ['Wrapped Ether', 'WETH', 26992040046283229929, 'Wrapped BTC', 'WBTC', 0]


if __name__ == "__main__":
    main()
