#!/usr/bin/env python3

from time import sleep

from scenarios.utils import ensure_miner
from warnet.test_framework_bridge import WarnetTestFramework

from ipaddress import IPv4Address, IPv6Address, ip_address
from kubernetes import client, config

def cli_help():
    return "review subset theory; run this to see logs: kubectl logs pod/rpc-0"


class InspectIP(WarnetTestFramework):
    def set_test_params(self):
        # This is just a minimum
        self.num_nodes = 0


    def run_test(self):
        config.load_incluster_config()
        v1 = client.CoreV1Api()

        endpoints = v1.read_namespaced_endpoints(name="warnet-tank-000000-service",
                                                 namespace="warnet")
        self.log.info("_____warnet-tank-000000-service_____")
        self.log.info(f"subsets: {endpoints.subsets}")
        self.log.info(f"subsets[0].addresses: {endpoints.subsets[0].addresses}")
        self.log.info(f"endpoints.subsets[0].addresses[0].ip{endpoints.subsets[0].addresses[0].ip}")

        endpoints = v1.read_namespaced_endpoints(name="warnet-tank-000001-service",
                                                 namespace="warnet")
        self.log.info("_____warnet-tank-000001-service_____")
        self.log.info(f"subsets: {endpoints.subsets}")
        self.log.info(f"subsets[0].addresses: {endpoints.subsets[0].addresses}")
        self.log.info(f"endpoints.subsets[0].addresses[0].ip{endpoints.subsets[0].addresses[0].ip}")


        endpoints = v1.read_namespaced_endpoints(name="warnet-tank-000002-service",
                                                 namespace="warnet")
        self.log.info("_____warnet-tank-000002-service_____")
        self.log.info(f"subsets: {endpoints.subsets}")
        self.log.info(f"subsets[0].addresses: {endpoints.subsets[0].addresses}")
        self.log.info(f"endpoints.subsets[0].addresses[0].ip{endpoints.subsets[0].addresses[0].ip}")


if __name__ == "__main__":
    InspectIP().main()
