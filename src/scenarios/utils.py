from ipaddress import IPv4Address, IPv6Address, ip_address
from kubernetes import client, config


def ensure_miner(node):
    wallets = node.listwallets()
    if "miner" not in wallets:
        node.createwallet("miner", descriptors=True)
    return node.get_wallet_rpc("miner")


def get_service_ip(service_name: str, namespace: str = "warnet") -> IPv4Address | IPv6Address:
    config.load_incluster_config()
    v1 = client.CoreV1Api()
    service = v1.read_namespaced_service(name=service_name, namespace=namespace)
    return ip_address(service.spec.cluster_ip)
