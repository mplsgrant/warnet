import subprocess
import sys
import tempfile
from multiprocessing import Process
from pathlib import Path
from typing import Optional

import click
import yaml

from .constants import (
    BITCOIN_CHART_LOCATION,
    CADDY_CHART,
    DEFAULTS_FILE,
    DEFAULTS_NAMESPACE_FILE,
    FORK_OBSERVER_CHART,
    HELM_COMMAND,
    INGRESS_HELM_COMMANDS,
    LOGGING_CRD_COMMANDS,
    LOGGING_HELM_COMMANDS,
    LOGGING_NAMESPACE,
    NAMESPACES_CHART_LOCATION,
    NAMESPACES_FILE,
    NETWORK_FILE,
    SCENARIOS_DIR,
    WARGAMES_NAMESPACE_PREFIX,
)
from .control import _run
from .k8s import (
    get_default_namespace,
    get_default_namespace_or,
    get_mission,
    get_namespaces_by_type,
    wait_for_ingress_controller,
    wait_for_pod_ready,
)
from .process import stream_command

HINT = "\nAre you trying to run a scenario? See `warnet run --help`"


def validate_directory(ctx, param, value):
    directory = Path(value)
    if not directory.is_dir():
        raise click.BadParameter(f"'{value}' is not a valid directory.{HINT}")
    if not (directory / NETWORK_FILE).exists() and not (directory / NAMESPACES_FILE).exists():
        raise click.BadParameter(
            f"'{value}' does not contain a valid network.yaml or namespaces.yaml file.{HINT}"
        )
    return directory


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument(
    "directory",
    type=click.Path(exists=True),
    callback=validate_directory,
)
@click.option("--debug", is_flag=True)
@click.option("--namespace", type=str, help="Specify a namespace in which to deploy the network")
@click.option("--to-all-users", is_flag=True, help="Deploy network to all user namespaces")
@click.argument("unknown_args", nargs=-1)
def deploy(directory, debug, namespace, to_all_users, unknown_args):
    """Deploy a warnet with topology loaded from <directory>"""
    if unknown_args:
        raise click.BadParameter(f"Unknown args: {unknown_args}{HINT}")

    if to_all_users:
        namespaces = get_namespaces_by_type(WARGAMES_NAMESPACE_PREFIX)
        for namespace in namespaces:
            _deploy(directory, debug, namespace.metadata.name, False)
    else:
        _deploy(directory, debug, namespace, to_all_users)


def _deploy(directory, debug, namespace, to_all_users):
    """Deploy a warnet with topology loaded from <directory>"""
    directory = Path(directory)

    if to_all_users:
        namespaces = get_namespaces_by_type(WARGAMES_NAMESPACE_PREFIX)
        processes = []
        for namespace in namespaces:
            p = Process(target=deploy, args=(directory, debug, namespace.metadata.name, False))
            p.start()
            processes.append(p)
        for p in processes:
            p.join()
        return

    if (directory / NETWORK_FILE).exists():
        processes = []
        # Deploy logging CRD first to avoid synchronisation issues
        deploy_logging_crd(directory, debug)

        logging_process = Process(target=deploy_logging_stack, args=(directory, debug))
        logging_process.start()
        processes.append(logging_process)

        network_process = Process(target=deploy_network, args=(directory, debug, namespace))
        network_process.start()

        ingress_process = Process(target=deploy_ingress, args=(directory, debug))
        ingress_process.start()
        processes.append(ingress_process)

        caddy_process = Process(target=deploy_caddy, args=(directory, debug))
        caddy_process.start()
        processes.append(caddy_process)

        # Wait for the network process to complete
        network_process.join()

        # Start the fork observer process immediately after network process completes
        fork_observer_process = Process(target=deploy_fork_observer, args=(directory, debug))
        fork_observer_process.start()
        processes.append(fork_observer_process)

        # Wait for all other processes to complete
        for p in processes:
            p.join()

    elif (directory / NAMESPACES_FILE).exists():
        deploy_namespaces(directory)
    else:
        click.echo(
            "Error: Neither network.yaml nor namespaces.yaml found in the specified directory."
        )


def check_logging_required(directory: Path):
    # check if node-defaults has logging or metrics enabled
    default_file_path = directory / DEFAULTS_FILE
    with default_file_path.open() as f:
        default_file = yaml.safe_load(f)
    if default_file.get("collectLogs", False):
        return True
    if default_file.get("metricsExport", False):
        return True

    # check to see if individual nodes have logging enabled
    network_file_path = directory / NETWORK_FILE
    with network_file_path.open() as f:
        network_file = yaml.safe_load(f)
    nodes = network_file.get("nodes", [])
    for node in nodes:
        if node.get("collectLogs", False):
            return True
        if node.get("metricsExport", False):
            return True

    return False


def deploy_logging_crd(directory: Path, debug: bool) -> bool:
    """
    This function exists so we can parallelise the rest of the loggin stack
    installation
    """
    if not check_logging_required(directory):
        return False

    click.echo(
        "Found collectLogs or metricsExport in network definition, Deploying logging stack CRD"
    )

    for command in LOGGING_CRD_COMMANDS:
        if not stream_command(command):
            print(f"Failed to run Helm command: {command}")
            return False
    return True


def deploy_logging_stack(directory: Path, debug: bool) -> bool:
    if not check_logging_required(directory):
        return False

    click.echo("Deploying logging stack")

    for command in LOGGING_HELM_COMMANDS:
        if not stream_command(command):
            print(f"Failed to run Helm command: {command}")
            return False
    return True


def deploy_caddy(directory: Path, debug: bool):
    network_file_path = directory / NETWORK_FILE
    with network_file_path.open() as f:
        network_file = yaml.safe_load(f)

    namespace = LOGGING_NAMESPACE
    # TODO: get this from the helm chart
    name = "caddy"

    # Only start if configured in the network file
    if not network_file.get(name, {}).get("enabled", False):
        return

    cmd = f"{HELM_COMMAND} {name} {CADDY_CHART} --namespace {namespace} --create-namespace"
    if debug:
        cmd += " --debug"

    if not stream_command(cmd):
        click.echo(f"Failed to run Helm command: {cmd}")
        return

    wait_for_pod_ready(name, namespace)
    click.echo("\nTo access the warnet dashboard run:\n  warnet dashboard")


def deploy_ingress(directory: Path, debug: bool):
    # Deploy ingress if either logging or fork observer is enabled
    network_file_path = directory / NETWORK_FILE
    with network_file_path.open() as f:
        network_file = yaml.safe_load(f)
    fo_enabled = network_file.get("fork_observer", {}).get("enabled", False)
    logging_enabled = check_logging_required(directory)
    if not (fo_enabled or logging_enabled):
        return
    click.echo("Deploying ingress controller")

    for command in INGRESS_HELM_COMMANDS:
        if not stream_command(command):
            print(f"Failed to run Helm command: {command}")
            return False

    wait_for_ingress_controller()

    return True


def deploy_fork_observer(directory: Path, debug: bool) -> bool:
    network_file_path = directory / NETWORK_FILE
    with network_file_path.open() as f:
        network_file = yaml.safe_load(f)

    # Only start if configured in the network file
    if not network_file.get("fork_observer", {}).get("enabled", False):
        return False

    default_namespace = get_default_namespace()
    namespace = LOGGING_NAMESPACE
    cmd = f"{HELM_COMMAND} 'fork-observer' {FORK_OBSERVER_CHART} --namespace {namespace} --create-namespace"
    if debug:
        cmd += " --debug"

    temp_override_file_path = ""
    override_string = ""

    # Add an entry for each node in the graph
    for i, tank in enumerate(get_mission("tank")):
        node_name = tank.metadata.name
        for container in tank.spec.containers:
            if container.name == "bitcoincore":
                for port in container.ports:
                    if port.name == "rpc":
                        rpcport = port.container_port
                    if port.name == "p2p":
                        p2pport = port.container_port
        node_config = f"""
[[networks.nodes]]
id = {i}
name = "{node_name}"
description = "{node_name}.{default_namespace}.svc:{int(p2pport)}"
rpc_host = "{node_name}.{default_namespace}.svc"
rpc_port = {int(rpcport)}
rpc_user = "forkobserver"
rpc_password = "tabconf2024"
"""

        override_string += node_config

    # Create yaml string using multi-line string format
    override_string = override_string.strip()
    v = {"config": override_string}
    v["configQueryinterval"] = network_file.get("fork_observer", {}).get("configQueryinterval", 20)
    yaml_string = yaml.dump(v, default_style="|", default_flow_style=False)

    # Dump to yaml tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_file:
        temp_file.write(yaml_string)
        temp_override_file_path = Path(temp_file.name)

    cmd = f"{cmd} -f {temp_override_file_path}"

    if not stream_command(cmd):
        click.echo(f"Failed to run Helm command: {cmd}")
        return False
    return True


def deploy_network(directory: Path, debug: bool = False, namespace: Optional[str] = None):
    network_file_path = directory / NETWORK_FILE
    namespace = get_default_namespace_or(namespace)

    with network_file_path.open() as f:
        network_file = yaml.safe_load(f)

    needs_ln_init = False
    for node in network_file["nodes"]:
        if (
            "lnd" in node 
            and "channels" in node["lnd"]
            and len(node["lnd"]["channels"]) > 0
        ):
            needs_ln_init = True
            break

    processes = []
    for node in network_file["nodes"]:
        p = Process(target=deploy_single_node, args=(node, directory, debug, namespace))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    if needs_ln_init:
        _run(
            scenario_file=SCENARIOS_DIR / "ln_init.py",
            debug=True,
            source_dir=SCENARIOS_DIR,
            additional_args=None,
            namespace=namespace,
        )


def deploy_single_node(node, directory: Path, debug: bool, namespace: str):
    defaults_file_path = directory / DEFAULTS_FILE
    click.echo(f"Deploying node: {node.get('name')}")
    temp_override_file_path = ""
    try:
        node_name = node.get("name")
        node_config_override = {k: v for k, v in node.items() if k != "name"}

        defaults_file_path = directory / DEFAULTS_FILE
        cmd = f"{HELM_COMMAND} {node_name} {BITCOIN_CHART_LOCATION} --namespace {namespace} -f {defaults_file_path}"
        if debug:
            cmd += " --debug"

        if node_config_override:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_file:
                yaml.dump(node_config_override, temp_file)
                temp_override_file_path = Path(temp_file.name)
            cmd = f"{cmd} -f {temp_override_file_path}"

        if not stream_command(cmd):
            click.echo(f"Failed to run Helm command: {cmd}")
            return
    except Exception as e:
        click.echo(f"Error: {e}")
        return
    finally:
        if temp_override_file_path:
            Path(temp_override_file_path).unlink()


def deploy_namespaces(directory: Path):
    namespaces_file_path = directory / NAMESPACES_FILE
    defaults_file_path = directory / DEFAULTS_NAMESPACE_FILE

    with namespaces_file_path.open() as f:
        namespaces_file = yaml.safe_load(f)

    names = [n.get("name") for n in namespaces_file["namespaces"]]
    for n in names:
        if not n.startswith(WARGAMES_NAMESPACE_PREFIX):
            click.secho(
                f"Failed to create namespace: {n}. Namespaces must start with a '{WARGAMES_NAMESPACE_PREFIX}' prefix.",
                fg="red",
            )
            return

    processes = []
    for namespace in namespaces_file["namespaces"]:
        p = Process(target=deploy_single_namespace, args=(namespace, defaults_file_path))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()


def deploy_single_namespace(namespace, defaults_file_path: Path):
    click.echo(f"Deploying namespace: {namespace.get('name')}")
    temp_override_file_path = ""
    try:
        namespace_name = namespace.get("name")
        namespace_config_override = {k: v for k, v in namespace.items() if k != "name"}

        cmd = f"{HELM_COMMAND} {namespace_name} {NAMESPACES_CHART_LOCATION} -f {defaults_file_path}"

        if namespace_config_override:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_file:
                yaml.dump(namespace_config_override, temp_file)
                temp_override_file_path = Path(temp_file.name)
            cmd = f"{cmd} -f {temp_override_file_path}"

        if not stream_command(cmd):
            click.echo(f"Failed to run Helm command: {cmd}")
            return
    except Exception as e:
        click.echo(f"Error: {e}")
        return
    finally:
        if temp_override_file_path:
            Path(temp_override_file_path).unlink()


def is_windows():
    return sys.platform.startswith("win")


def run_detached_process(command):
    if is_windows():
        # For Windows, use CREATE_NEW_PROCESS_GROUP and DETACHED_PROCESS
        subprocess.Popen(
            command,
            shell=True,
            stdin=None,
            stdout=None,
            stderr=None,
            close_fds=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        )
    else:
        # For Unix-like systems, use nohup and redirect output
        command = f"nohup {command} > /dev/null 2>&1 &"
        subprocess.Popen(command, shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)

    print(f"Started detached process: {command}")
