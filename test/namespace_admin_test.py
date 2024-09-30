#!/usr/bin/env python3

import os
from pathlib import Path
from typing import Optional

from test_base import TestBase


class NamespaceAdminTest(TestBase):
    def __init__(self):
        super().__init__()
        self.namespace_dir = (
            Path(os.path.dirname(__file__))
            / "data"
            / "admin"
            / "namespaces"
            / "two_namespaces_two_users"
        )

    def run_test(self):
        try:
            self.setup_namespaces()
            self.setup_service_accounts()
        finally:
            self.cleanup()

    def setup_namespaces(self):
        self.log.info("Setting up the namespaces")
        self.log.info(self.warnet(f"deploy {self.namespace_dir}"))
        self.wait_for_predicate(self.two_namespaces_are_validated)
        self.log.info("Namespace setup complete")

    def setup_service_accounts(self):
        self.log.info("Creating service accounts...")
        self.log.info(self.warnet("admin create-kubeconfigs"))
        self.wait_for_predicate(self.service_accounts_are_validated)

    def get_service_accounts(self) -> Optional[list[dict[str, str]]]:
        self.log.info("Setting up service accounts")
        resp = self.warnet("admin service-accounts list")
        if resp == "Could not find any matching service accounts.":
            return None
        service_accounts = {}
        current_namespace = ""
        for line in resp.splitlines():
            if line.startswith("Service"):
                current_namespace = line.split(": ")[1]
                service_accounts[current_namespace] = []
            if line.startswith("- "):
                sa = line.lstrip("- ")
                service_accounts[current_namespace].append(sa)
        self.log.info(f"Service accounts: {service_accounts}")
        return service_accounts

    def service_accounts_are_validated(self) -> bool:
        self.log.info("Checking service accounts")
        maybe_service_accounts = self.get_service_accounts()
        expected = {
            "wargames-blue-team": ["carol", "default", "mallory"],
            "wargames-red-team": ["alice", "bob", "default"],
        }
        return maybe_service_accounts == expected

    def get_namespaces(self) -> Optional[list[str]]:
        self.log.info("Querying the namespaces...")
        resp = self.warnet("admin namespaces list")
        if resp == "No warnet namespaces found.":
            return None
        namespaces = []
        for line in resp.splitlines():
            if line.startswith("- "):
                namespaces.append(line.lstrip("- "))
        self.log.info(f"Namespaces: {namespaces}")
        return namespaces

    def two_namespaces_are_validated(self) -> bool:
        maybe_namespaces = self.get_namespaces()
        if maybe_namespaces is None:
            return False
        if len(maybe_namespaces) != 2:
            return False
        if "wargames-blue-team" not in maybe_namespaces:
            return False
        return "wargames-red-team" in maybe_namespaces


if __name__ == "__main__":
    test = NamespaceAdminTest()
    test.run_test()
