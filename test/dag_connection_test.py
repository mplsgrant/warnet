#!/usr/bin/env python3

import os
from functools import partial
from pathlib import Path

from test_base import TestBase, assert_log

graph_file_path = Path(os.path.dirname(__file__)) / "data" / "ten_semi_unconnected.graphml"

base = TestBase()

base.start_server()
print(base.warcli(f"network start {graph_file_path}"))
base.wait_for_all_tanks_status(target="running")
base.wait_for_all_edges()

# Start scenario
base.warcli(f"scenarios run connect_dag --network_name={base.network_name}")

assert_dag = partial(assert_log, base.tmpdir / "tmp.log",
                     ["Successfully ran the connect_day.py scenario."], ["AssertionError"])

base.wait_for_predicate(assert_dag)

base.stop_server()
