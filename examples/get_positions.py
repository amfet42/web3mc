import logging

from web3.auto import w3

from web3mc.auto import multicall

multicall_logger = logging.getLogger("web3multicall")
multicall_logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
multicall_logger.addHandler(ch)

# crvUSD controllers
controllers = {
    "sfrxETH": "0x8472A9A7632b173c8Cf3a86D3afec50c35548e76",
    "wstETH": "0x100dAa78fC509Db39Ef7D04DE0c1ABD299f4C6CE",
    "WBTC": "0x4e59541306910aD6dC1daC0AC9dFB29bD9F15c67",
    "WETH": "0xA920De414eA4Ab66b97dA1bFE9e6EcA7d4219635",
}

abi = [
    {
        "stateMutability": "view",
        "type": "function",
        "name": "n_loans",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
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
        "name": "debt",
        "inputs": [{"name": "user", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
    },
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
        "name": "user_state",
        "inputs": [{"name": "user", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256[4]"}],
    },
]


def main():
    for collateral, address in controllers.items():
        print(f"Importing positions for {collateral} controller")

        controller = w3.eth.contract(address=address, abi=abi)
        n_loans = controller.functions.n_loans().call()

        calls = []
        for i in range(n_loans):
            calls.append(controller.functions.loans(i))
        users = multicall.aggregate(calls)

        calls = []
        for user in users:
            calls.append(controller.functions.user_state(user))
        for user in users:
            calls.append(controller.functions.health(user, False))

        data = multicall.aggregate(calls)

        print(f"{'i':^5}|{'user':^45}|{'collateral':^30}|{'stablecoin':^30}|{'debt':^30}|{'N':^5}|{'health':^30}")
        print("_" * 175)
        for i, user in enumerate(users):
            print(
                f"{i:^5}|{user:^45}|{data[i][0]:^30}|{data[i][1]:^30}|{data[i][2]:^30}|{data[i][3]:^5}|"
                f"{data[n_loans+i]:^30}"
            )


if __name__ == "__main__":
    main()
