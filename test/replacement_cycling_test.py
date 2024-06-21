#!/usr/bin/env python3

import os
from pathlib import Path
from test_base import TestBase

graph_file_path = Path(os.path.dirname(__file__)) / "data" / "12_node_ring.graphml"

base = TestBase()

base.start_server()
print(base.warcli(f"network start {graph_file_path}"))
base.wait_for_all_tanks_status(target="running")
base.wait_for_all_edges()

# Start scenario
out = base.warcli(f"scenarios run replacement_cycling --network_name={base.network_name}")

log_path = base.logfilepath

print(f"out: {out}")
print(f"log: {log_path}")

def check_success():
    False

base.stop_server()
