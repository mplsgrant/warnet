from time import sleep

from test_framework.test_framework import BitcoinTestFramework

def cli_help():
    return "Keepin' it EZ 🪄"


class EZTesting(BitcoinTestFramework):

    def set_test_params(self):
        self.num_nodes = 0

    def run_test(self):
        while not self.warnet.network_connected():
            self.log.info("Waiting for warnet connection")
            sleep(1)

        current_miner = 0
        self.log.info(f"Node count: {len(self.nodes)}")


if __name__ == "__main__":
    EZTesting().main()
