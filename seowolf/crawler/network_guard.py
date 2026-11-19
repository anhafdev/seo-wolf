import asyncio
import socket
from ipaddress import IPv4Address, IPv6Address, ip_address, ip_network

__author__ = "@anhafxd"

NAT64_PREFIX = ip_network("64:ff9b::/96")
METADATA_HOSTS = {"metadata.google.internal", "metadata", "instance-data"}


class BlockedDestinationError(Exception):
    def __init__(self, host: str, addresses: list[str]) -> None:
        self.host = host
        self.addresses = addresses
        listed = ", ".join(addresses) if addresses else "metadata host"
        super().__init__(f"blocked private or reserved destination {host} ({listed})")


def embedded_ipv4(address: IPv6Address) -> IPv4Address | None:
    if address.ipv4_mapped is not None:
        return address.ipv4_mapped
    if address in NAT64_PREFIX:
        return IPv4Address(int(address) & 0xFFFFFFFF)
    if address.sixtofour is not None:
        return address.sixtofour
    return None


def is_public_address(address_text: str) -> bool:
    try:
        address = ip_address(address_text.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(address, IPv6Address):
        inner = embedded_ipv4(address)
        if inner is not None:
            return is_public_address(str(inner))
    return address.is_global and not address.is_multicast


def literal_address(host: str) -> str | None:
    try:
        return str(ip_address(host.split("%", 1)[0]))
    except ValueError:
        return None


async def resolve_addresses(host: str, port: int) -> list[str]:
    bare_host = host.strip("[]")
    literal = literal_address(bare_host)
    if literal is not None:
        return [literal]
    loop = asyncio.get_running_loop()
    results = await loop.getaddrinfo(bare_host, port, type=socket.SOCK_STREAM)
    unique_addresses: list[str] = []
    for result in results:
        address = str(result[4][0])
        if address not in unique_addresses:
            unique_addresses.append(address)
    return unique_addresses


async def safe_addresses(host: str, port: int, allow_private_networks: bool) -> list[str]:
    if not allow_private_networks and host.lower().rstrip(".") in METADATA_HOSTS:
        raise BlockedDestinationError(host, [])
    addresses = await resolve_addresses(host, port)
    if allow_private_networks:
        return addresses
    blocked = [address for address in addresses if not is_public_address(address)]
    if blocked or not addresses:
        raise BlockedDestinationError(host, blocked)
    return addresses
