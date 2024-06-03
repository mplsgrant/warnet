#!/usr/bin/env python3

import os
import time
from pathlib import Path

from test_base import TestBase

dag_unconnected_graph = Path(os.path.dirname(__file__)) / "data" / "dag_unconnected.graphml"
dag_base = TestBase()

if dag_base.backend == "k8s":
    dag_base.start_server()
    print(dag_base.warcli(f"network start {dag_unconnected_graph}"))
    dag_base.wait_for_all_tanks_status(target="running")
    dag_base.wait_for_all_edges()

    # Start scenario
    dag_base.warcli(f"scenarios run get_service_ip --network_name={dag_base.network_name}")

    counter = 0
    while (len(dag_base.rpc("scenarios_list_running")) == 1
           and dag_base.rpc("scenarios_list_running")[0]["active"]):
        time.sleep(1)
        counter += 1
        if counter > 60:
            pid = dag_base.rpc("scenarios_list_running")[0]['pid']
            dag_base.warcli(f"scenarios stop {pid}", False)
            print("get_service_ip_test took longer than one minute. Fail.")
            assert counter < 60
else:
    print(f"get_service_ip_test (connected) does not test {dag_base.backend}")
    
dag_base.stop_server()
