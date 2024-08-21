import json
from importlib.resources import files
from typing import Any, Dict

from kubernetes import client, config
from kubernetes.config import ConfigException
from kubernetes.dynamic import DynamicClient

from .process import stream_command

WAR_MANIFESTS = files("manifests")


def get_static_client() -> client.CoreV1Api:
    try:
        config.load_kube_config()
        return client.CoreV1Api()
    except ConfigException as e:
        raise


def get_dynamic_client():
    config.load_kube_config()
    return DynamicClient(client.ApiClient())


def get_pods(namespace: str):
    try:
        sclient = get_static_client()
        return sclient.list_namespaced_pod(namespace)
    except ConfigException as e:
        raise


def get_mission(mission):
    pods = get_pods("warnet")
    crew = []
    for pod in pods.items:
        if "mission" in pod.metadata.labels and pod.metadata.labels["mission"] == mission:
            crew.append(pod)
    return crew


def get_edges():
    sclient = get_static_client()
    configmap = sclient.read_namespaced_config_map(name="edges", namespace="warnet")
    return json.loads(configmap.data["data"])


def create_kubernetes_object(
    kind: str, metadata: Dict[str, Any], spec: Dict[str, Any] = None
) -> Dict[str, Any]:
    obj = {
        "apiVersion": "v1",
        "kind": kind,
        "metadata": metadata,
    }
    if spec is not None:
        obj["spec"] = spec
    return obj


def create_namespace() -> dict:
    return {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": "warnet"}}


def set_kubectl_context(namespace: str):
    """
    Set the default kubectl context to the specified namespace.
    """
    command = f"kubectl config set-context --current --namespace={namespace}"
    result = stream_command(command)
    if result:
        print(f"Kubectl context set to namespace: {namespace}")
    else:
        print(f"Failed to set kubectl context to namespace: {namespace}")
    return result


def deploy_base_configurations():
    base_configs = [
        "namespace.yaml",
        "rbac-config.yaml",
    ]

    for bconfig in base_configs:
        command = f"kubectl apply -f {WAR_MANIFESTS}/{bconfig}"
        if not stream_command(command):
            print(f"Failed to apply {bconfig}")
            return False
    return True


def apply_kubernetes_yaml(yaml_file: str):
    command = f"kubectl apply -f {yaml_file}"
    return stream_command(command)


def delete_namespace(namespace: str):
    command = f"kubectl delete namespace {namespace}"
    return stream_command(command)
