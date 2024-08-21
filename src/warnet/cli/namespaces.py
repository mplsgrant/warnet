import os
import tempfile
from pathlib import Path

import click
import yaml

from .process import stream_command, run_command

NAMESPACES_DIR = Path("namespaces")
DEFAULT_NAMESPACES = "two_namespaces_two_users"
NAMESPACES_FILE = "namespaces.yaml"
DEFAULTS_FILE = "defaults.yaml"
HELM_COMMAND = "helm upgrade --install"
BITCOIN_CHART_LOCATION = "./resources/charts/namespaces"

@click.group(name="namespaces")
def namespaces():
    """Namespaces commands"""


@namespaces.command()
@click.argument("namespaces", default=DEFAULT_NAMESPACES)
def deploy(namespaces: str):
    """Deploy namespaces with users from a <namespaces_file>"""
    full_path = os.path.join(NAMESPACES_DIR, namespaces)
    namespaces_file_path = os.path.join(full_path, NAMESPACES_FILE)
    defaults_file_path = os.path.join(full_path, DEFAULTS_FILE)

    namespaces_file = {}
    with open(namespaces_file_path) as f:
        namespaces_file = yaml.safe_load(f)

    # validate names before deploying
    names = [n.get("name") for n in namespaces_file["namespaces"]]
    for n in names:
        if not n.startswith("warnet-"):
            print(f"Failled to create namespace: {n}. Namespaces must start with a 'warnet-' prefix.")

    # deploy namespaces
    for namespace in namespaces_file["namespaces"]:
        print(f"Deploying namespace: {namespace.get('name')}")
        try:
            temp_override_file_path = ""
            namespace_name = namespace.get("name")
            # all the keys apart from name
            namespace_config_override = {k: v for k, v in namespace.items() if k != "name"}

            cmd = f"{HELM_COMMAND} {namespace_name} {BITCOIN_CHART_LOCATION} -f {defaults_file_path}"

            if namespace_config_override:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".yaml", delete=False
                ) as temp_file:
                    yaml.dump(namespace_config_override, temp_file)
                    temp_override_file_path = temp_file.name
                cmd = f"{cmd} -f {temp_override_file_path}"

            if not stream_command(cmd):
                print(f"Failed to run Helm command: {cmd}")
                return
        except Exception as e:
            print(f"Error: {e}")
            return

@namespaces.command()
def list():
    """List all namespaces with 'warnet-' prefix"""
    cmd = "kubectl get namespaces -o jsonpath='{.items[*].metadata.name}'"
    res = run_command(cmd)
    all_namespaces = res.split()
    warnet_namespaces = [ns for ns in all_namespaces if ns.startswith("warnet-")]

    if warnet_namespaces:
        print("Warnet namespaces:")
        for ns in warnet_namespaces:
            print(f"- {ns}")
    else:
        print("No warnet namespaces found.")

@namespaces.command()
@click.option("--all", "destroy_all", is_flag=True, help="Destroy all warnet- prefixed namespaces")
@click.argument("namespace", required=False)
def destroy(destroy_all: bool, namespace: str):
    """Destroy a specific namespace or all warnet- prefixed namespaces"""
    if destroy_all:
        cmd = "kubectl get namespaces -o jsonpath='{.items[*].metadata.name}'"
        res = run_command(cmd)

        # Get the list of namespaces
        all_namespaces = res.split()
        warnet_namespaces = [ns for ns in all_namespaces if ns.startswith("warnet-")]

        if not warnet_namespaces:
            print("No warnet namespaces found to destroy.")
            return

        for ns in warnet_namespaces:
            destroy_cmd = f"kubectl delete namespace {ns}"
            if not stream_command(destroy_cmd):
                print(f"Failed to destroy namespace: {ns}")
            else:
                print(f"Destroyed namespace: {ns}")
    elif namespace:
        if not namespace.startswith("warnet-"):
            print("Error: Can only destroy namespaces with 'warnet-' prefix")
            return

        destroy_cmd = f"kubectl delete namespace {namespace}"
        if not stream_command(destroy_cmd):
            print(f"Failed to destroy namespace: {namespace}")
        else:
            print(f"Destroyed namespace: {namespace}")
    else:
        print("Error: Please specify a namespace or use --all flag.")