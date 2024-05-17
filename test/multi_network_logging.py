#!/usr/bin/env python3

import os
import sys
import time

from pathlib import Path
from test_base import TestBase


graph_file_path = Path(os.path.dirname(__file__)) / "data" / "v25_x_12.graphml"

alice_base = TestBase()

if alice_base.backend == "compose":
    print(f"Test ignored: {os.path.basename(__file__)} does not test the 'compose' backend")
    sys.exit(0)

alice_base.start_server()
print(alice_base.warcli(f"network start {graph_file_path}"))
print(alice_base.wait_for_rpc(f"network connected"))
time.sleep(20)
print(alice_base.wait_for_rpc(f"network connected"))
alice_base.wait_for_all_tanks_status(target="running")
alice_base.wait_for_all_edges()

bob_base = TestBase()
bob_base.start_server()
print(bob_base.warcli(f"network start {graph_file_path}"))
print(bob_base.wait_for_rpc(f"network connected"))
time.sleep(20)
print(bob_base.wait_for_rpc(f"network connected"))
bob_base.wait_for_all_tanks_status(target="running")
bob_base.wait_for_all_edges()

alice_base.stop_server()
bob_base.stop_server()
