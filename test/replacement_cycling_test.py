#!/usr/bin/env python3
import contextlib
import os
import re
import time
from pathlib import Path
from test_base import TestBase

graph_file_path = Path(os.path.dirname(__file__)) / "data" / "12_node_ring.graphml"


def assert_equal(thing1, thing2, *args):
    if thing1 != thing2 or any(thing1 != arg for arg in args):
        raise AssertionError("not(%s)" % " == ".join(str(arg) for arg in (thing1, thing2) + args))


def debug_log_size(debug_log_path, **kwargs) -> int:
    with open(debug_log_path, **kwargs) as dl:
        dl.seek(0, 2)
        return dl.tell()


@contextlib.contextmanager
def assert_debug_log(debug_log_path, expected_msgs, unexpected_msgs=None, timeout=2):
    if unexpected_msgs is None:
        unexpected_msgs = []
    assert_equal(type(expected_msgs), list)
    assert_equal(type(unexpected_msgs), list)

    timeout_factor = 1
    time_end = time.time() + timeout * timeout_factor
    # Must use same encoding that is used to read() below
    prev_size = debug_log_size(debug_log_path, encoding="utf-8")

    yield

    while True:
        found = True
        with open(debug_log_path, encoding="utf-8", errors="replace") as dl:
            dl.seek(prev_size)
            log = dl.read()
        print_log = " - " + "\n - ".join(log.splitlines())
        for unexpected_msg in unexpected_msgs:
            if re.search(re.escape(unexpected_msg), log, flags=re.MULTILINE):
                raise AssertionError(
                    'Unexpected message "{}" partially matches log:\n\n{}\n\n'.format(
                        unexpected_msg, print_log))
        for expected_msg in expected_msgs:
            if re.search(re.escape(expected_msg), log, flags=re.MULTILINE) is None:
                found = False
        if found:
            return
        if time.time() >= time_end:
            break
        time.sleep(0.05)
    raise AssertionError(
        'Expected messages "{}" does not partially match log:'
        '\n\n{}\n\n'.format(str(expected_msgs), print_log))


def log_exists(test_base: TestBase):
    def f():
        path = test_base.tmpdir / "tmp.log"
        return path.exists()
    return f


def success_exists(test_base: TestBase, log_string):
    def f():
        path = test_base.tmpdir / "tmp.log"
        found = False
        if path.exists():
            with open(path, 'r') as file:
                for line in file:
                    if log_string in line:
                        found = True
                        break
        return found
    return f


# def get_last_line(file_path):
#     with open(file_path, 'rb') as f:
#         f.seek(-2, os.SEEK_END)
#         while f.read(1) != b'\n':  # Until EOL is found.
#             f.seek(-2, 1)  # Jump back the read byte plus one more.
#         return f.readline().decode()  # Read the last line.



base = TestBase()

base.start_server()
print(base.warcli(f"network start {graph_file_path}"))
base.wait_for_all_tanks_status(target="running")
base.wait_for_all_edges()

out = base.warcli(f"scenarios run replacement_cycling --network_name={base.network_name}")
print(f"Out: {out}")

base.wait_for_predicate(log_exists(base))
base.wait_for_predicate(success_exists(base, "Finished: replacement_cycling.py"))
print(f"Finished: {os.path.basename(__file__)}")

base.stop_server()