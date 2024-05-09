#!/usr/bin/env python3
# Copyright (c) 2017-2022 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Class for bitcoind node under test"""

import errno
import tempfile
import time
from enum import Enum

from test_framework.authproxy import (
    JSONRPCException,
)
from test_framework.test_node import TestNode
from test_framework.util import (
    wait_until_helper_internal,
)

BITCOIND_PROC_WAIT_TIMEOUT = 60


class FailedToStartError(Exception):
    """Raised when a node fails to start correctly."""


class ErrorMatch(Enum):
    FULL_TEXT = 1
    FULL_REGEX = 2
    PARTIAL_REGEX = 3


class TestNodeBridge(TestNode):
    """A class for representing a Warnet node under test.

    This class contains:

    - state about the node (whether it's running, etc)
    - a Python subprocess.Popen object representing the running process
    - an RPC connection to the node
    - one or more P2P connections to the node


    To make things easier for the test writer, any unrecognised messages will
    be dispatched to the RPC connection."""

    def start(self, extra_args=None, *, cwd=None, stdout=None, stderr=None, env=None, **kwargs):
        """Start the node."""
        self.log.info(f"test_node - start node {self.index} (it should already be started)")

        if extra_args is None:
            extra_args = self.extra_args

        # Add a new stdout and stderr file each time bitcoind is started
        if stderr is None:
            stderr = tempfile.NamedTemporaryFile(dir=self.stderr_dir, delete=False)
        if stdout is None:
            stdout = tempfile.NamedTemporaryFile(dir=self.stdout_dir, delete=False)
        self.stderr = stderr
        self.stdout = stdout

        # if cwd is None:
        #     cwd = self.cwd

        # Delete any existing cookie file -- if such a file exists (eg due to
        # unclean shutdown), it will get overwritten anyway by bitcoind, and
        # potentially interfere with our attempt to authenticate
        #delete_cookie_file(self.datadir_path, self.chain)

        # add environment variable LIBC_FATAL_STDERR_=1 so that libc errors are written to stderr and not the terminal
        # subp_env = dict(os.environ, LIBC_FATAL_STDERR_="1")
        # if env is not None:
        #     subp_env.update(env)

        # self.process = subprocess.Popen(self.args + extra_args, env=subp_env, stdout=stdout, stderr=stderr, cwd=cwd, **kwargs)

        self.running = True
        # self.log.debug("bitcoind started, waiting for RPC to come up")

        # if self.start_perf:
        #     self._start_perf()

    def wait_for_rpc_connection(self):
        """Sets up an RPC connection to the bitcoind process. Returns False if unable to connect."""
        # Poll at a rate of four times per second
        poll_per_s = 4
        for _ in range(poll_per_s * self.rpc_timeout):
            # if self.process.poll() is not None:
            #     # Attach abrupt shutdown error/s to the exception message
            #     self.stderr.seek(0)
            #     str_error = ''.join(line.decode('utf-8') for line in self.stderr)
            #     str_error += "************************\n" if str_error else ''
            #
            #     raise FailedToStartError(self._node_msg(
            #         f'bitcoind exited with status {self.process.returncode} during initialization. {str_error}'))
            try:
                # rpc = get_rpc_proxy(
                #     rpc_url(self.datadir_path, self.index, self.chain, self.rpchost),
                #     self.index,
                #     timeout=self.rpc_timeout // 2,  # Shorter timeout to allow for one retry in case of ETIMEDOUT
                #     coveragedir=self.coverage_dir,
                # )
                self.rpc.getblockcount()
                # If the call to getblockcount() succeeds then the RPC connection is up
                if self.version_is_at_least(190000):
                    # getmempoolinfo.loaded is available since commit
                    # bb8ae2c (version 0.19.0)
                    wait_until_helper_internal(lambda: self.rpc.getmempoolinfo()['loaded'], timeout_factor=self.timeout_factor)
                    # Wait for the node to finish reindex, block import, and
                    # loading the mempool. Usually importing happens fast or
                    # even "immediate" when the node is started. However, there
                    # is no guarantee and sometimes ImportBlocks might finish
                    # later. This is going to cause intermittent test failures,
                    # because generally the tests assume the node is fully
                    # ready after being started.
                    #
                    # For example, the node will reject block messages from p2p
                    # when it is still importing with the error "Unexpected
                    # block message received"
                    #
                    # The wait is done here to make tests as robust as possible
                    # and prevent racy tests and intermittent failures as much
                    # as possible. Some tests might not need this, but the
                    # overhead is trivial, and the added guarantees are worth
                    # the minimal performance cost.
                self.log.debug("RPC successfully started")
                if self.use_cli:
                    return
                # self.rpc = rpc
                self.rpc_connected = True
                self.url = self.rpc.rpc_url
                return
            except JSONRPCException as e:  # Initialization phase
                # -28 RPC in warmup
                # -342 Service unavailable, RPC server started but is shutting down due to error
                if e.error['code'] != -28 and e.error['code'] != -342:
                    raise  # unknown JSON RPC exception
            except ConnectionResetError:
                # This might happen when the RPC server is in warmup, but shut down before the call to getblockcount
                # succeeds. Try again to properly raise the FailedToStartError
                pass
            except OSError as e:
                if e.errno == errno.ETIMEDOUT:
                    pass  # Treat identical to ConnectionResetError
                elif e.errno == errno.ECONNREFUSED:
                    pass  # Port not yet open?
                else:
                    raise  # unknown OS error
            except ValueError as e:  # cookie file not found and no rpcuser or rpcpassword; bitcoind is still starting
                if "No RPC credentials" not in str(e):
                    raise
            time.sleep(1.0 / poll_per_s)
        self._raise_assertion_error(f"Unable to connect to bitcoind after {self.rpc_timeout}s")

    def wait_for_cookie_credentials(self):
        """Ensures auth cookie credentials can be read, e.g. for testing CLI with -rpcwait before RPC connection is up."""
        self.log.info(f"test_node_bridge {self.index}'s wait_for_cookie_credentials: unimplemented")
        # self.log.debug("Waiting for cookie credentials")
        # # Poll at a rate of four times per second.
        # poll_per_s = 4
        # for _ in range(poll_per_s * self.rpc_timeout):
        #     try:
        #         get_auth_cookie(self.datadir_path, self.chain)
        #         self.log.debug("Cookie credentials successfully retrieved")
        #         return
        #     except ValueError:  # cookie file not found and no rpcuser or rpcpassword; bitcoind is still starting
        #         pass            # so we continue polling until RPC credentials are retrieved
        #     time.sleep(1.0 / poll_per_s)
        # self._raise_assertion_error("Unable to retrieve cookie credentials after {}s".format(self.rpc_timeout))

    def stop_node(self, expected_stderr='', *, wait=0, wait_until_stopped=True):
        """Stop the node."""
        self.log.info(f"test_node_bridge {self.index}'s stop_node function: unimplemented")
        # if not self.running:
        #     return
        # self.log.debug("Stopping node")
        # try:
        #     # Do not use wait argument when testing older nodes, e.g. in wallet_backwards_compatibility.py
        #     if self.version_is_at_least(180000):
        #         self.stop(wait=wait)
        #     else:
        #         self.stop()
        # except http.client.CannotSendRequest:
        #     self.log.exception("Unable to stop node.")
        #
        # # If there are any running perf processes, stop them.
        # for profile_name in tuple(self.perf_subprocesses.keys()):
        #     self._stop_perf(profile_name)
        #
        # del self.p2ps[:]
        #
        # assert (not expected_stderr) or wait_until_stopped  # Must wait to check stderr
        # if wait_until_stopped:
        #     self.wait_until_stopped(expected_stderr=expected_stderr)

    def is_node_stopped(self, *, expected_stderr="", expected_ret_code=0):
        """Checks whether the node has stopped.

        Returns True if the node has stopped. False otherwise.
        This method is responsible for freeing resources (self.process)."""
        self.log.info(f"test_node_bridge {self.index}'s is_node_stopped: always returns true")
        return True

        # if not self.running:
        #     return True
        # return_code = self.process.poll()
        # if return_code is None:
        #     return False
        #
        # # process has stopped. Assert that it didn't return an error code.
        # assert return_code == expected_ret_code, self._node_msg(
        #     f"Node returned unexpected exit code ({return_code}) vs ({expected_ret_code}) when stopping")
        # # Check that stderr is as expected
        # self.stderr.seek(0)
        # stderr = self.stderr.read().decode('utf-8').strip()
        # if stderr != expected_stderr:
        #     raise AssertionError("Unexpected stderr {} != {}".format(stderr, expected_stderr))
        #
        # self.stdout.close()
        # self.stderr.close()
        #
        # self.running = False
        # self.process = None
        # self.rpc_connected = False
        # self.rpc = None
        # self.log.debug("Node stopped")
        # return True

    def wait_until_stopped(self, *, timeout=BITCOIND_PROC_WAIT_TIMEOUT, expect_error=False, **kwargs):
        self.log.info(f"test_node_bridge {self.index}'s wait_until_stopped: not implemented")
        # expected_ret_code = 1 if expect_error else 0  # Whether node shutdown return EXIT_FAILURE or EXIT_SUCCESS
        # wait_until_helper_internal(lambda: self.is_node_stopped(expected_ret_code=expected_ret_code, **kwargs), timeout=timeout, timeout_factor=self.timeout_factor)

    def replace_in_config(self, replacements):
        """
        Perform replacements in the configuration file.
        The substitutions are passed as a list of search-replace-tuples, e.g.
            [("old", "new"), ("foo", "bar"), ...]
        """
        self.log.info(f"test_node {self.index}'s replace_in_config: not implemented")
        # with open(self.bitcoinconf, 'r', encoding='utf8') as conf:
        #     conf_data = conf.read()
        # for replacement in replacements:
        #     assert_equal(len(replacement), 2)
        #     old, new = replacement[0], replacement[1]
        #     conf_data = conf_data.replace(old, new)
        # with open(self.bitcoinconf, 'w', encoding='utf8') as conf:
        #     conf.write(conf_data)
