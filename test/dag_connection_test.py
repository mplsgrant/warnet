#!/usr/bin/env python3

import os
from functools import partial
from pathlib import Path

from test_base import TestBase, assert_log


class DAGConnectionTest(TestBase):
    def __init__(self):
        super().__init__()
        self.graph_file_path = (
            Path(os.path.dirname(__file__)) / "data" / "ten_semi_unconnected.graphml"
        )

    def run_test(self):
        self.start_server()
        try:
            self.setup_network()
            self.run_connect_dag_scenario()
        finally:
            self.stop_server()

    def setup_network(self):
        self.log.info("Setting up network")
        self.log.info(self.warcli(f"network start {self.graph_file_path}"))
        self.wait_for_all_tanks_status(target="running")
        self.wait_for_all_edges()

    def run_connect_dag_scenario(self):
        self.log.info("Running connect_dag scenario")
        self.warcli("scenarios run-file test/framework_tests/connect_dag.py")
        assert_dag = partial(
            assert_log,
            self.logfilepath,
            ["Successfully ran the connect_dag.py scenario using a temporary file"],
            ["Test failed."],
        )
        self.wait_for_predicate(assert_dag)
        self.stop_running_scenario()

    def stop_running_scenario(self):
        running_scenarios = self.rpc("scenarios_list_running")
        if running_scenarios:
            pid = running_scenarios[0]["pid"]
            self.log.warning(f"Stopping scenario with PID {pid}")
            self.warcli(f"scenarios stop {pid}", False)


if __name__ == "__main__":
    test = DAGConnectionTest()
    test.run_test()
