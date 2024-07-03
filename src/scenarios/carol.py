#!/usr/bin/env python3

from time import sleep
from warnet.test_framework_bridge import WarnetTestFramework
import zmq


def cli_help():
    return "Carol sends messages to the message relay service"


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
        while not self.warnet.network_connected():
            sleep(1)

        context = zmq.Context()

        sender = context.socket(zmq.PUB)
        sender.connect("tcp://msg-relay-service:5555")

        counter = 0
        while counter < 10:
            message = f"Carol message number {counter}"
            sender.send_string(message)
            counter += 1
            sleep(1)


if __name__ == "__main__":
    Carol().main()
