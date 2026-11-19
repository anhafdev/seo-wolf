import socket
from collections.abc import Iterable
from typing import Any

import httpcore
import httpx

from seowolf.crawler.network_guard import safe_addresses

__author__ = "@anhafxd"


class GuardedNetworkBackend(httpcore.AsyncNetworkBackend):
    def __init__(self, allow_private_networks: bool) -> None:
        self.allow_private_networks = allow_private_networks
        self.inner_backend = httpcore.AnyIOBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        try:
            addresses = await safe_addresses(host, port, self.allow_private_networks)
        except socket.gaierror as problem:
            raise httpcore.ConnectError(f"dns lookup failed for {host}: {problem}") from problem
        last_problem: Exception | None = None
        for address in addresses:
            try:
                return await self.inner_backend.connect_tcp(
                    address,
                    port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except (httpcore.ConnectError, httpcore.ConnectTimeout) as problem:
                last_problem = problem
        raise last_problem or httpcore.ConnectError(f"no address reachable for {host}")

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        raise httpcore.ConnectError("unix sockets are never used by the crawler")

    async def sleep(self, seconds: float) -> None:
        await self.inner_backend.sleep(seconds)


class GuardedTransport(httpx.AsyncHTTPTransport):
    def __init__(self, allow_private_networks: bool, max_connections: int) -> None:
        super().__init__(http2=True, trust_env=False)
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=httpx.create_ssl_context(trust_env=False),
            max_connections=max_connections,
            max_keepalive_connections=max_connections,
            keepalive_expiry=30.0,
            http1=True,
            http2=True,
            network_backend=GuardedNetworkBackend(allow_private_networks),
        )
