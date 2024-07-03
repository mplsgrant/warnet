#!/usr/bin/env python3

from time import sleep
from warnet.test_framework_bridge import WarnetTestFramework
import zmq


def cli_help():
    return "Alice listens on the message relay for Carol's messages"


class Carol(WarnetTestFramework):
    def set_test_params(self):
        self.num_nodes = 1

    def add_options(self, parser):
        parser.add_argument(
            "--network_name",
            dest="network_name",
            default="warnet",
            help="",
        )

    def run_test(self):
        context = zmq.Context()

        receiver = context.socket(zmq.SUB)
        receiver.connect("tcp://msg-relay-service:5556")

        while True:
            message = receiver.recv_string()
            self.log.info(f"Alice received message: {message}")


if __name__ == "__main__":
    Carol().main()
