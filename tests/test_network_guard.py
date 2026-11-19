import pytest

from seowolf.crawler.fetcher import PageFetcher
from seowolf.crawler.guarded_transport import GuardedNetworkBackend
from seowolf.crawler.network_guard import BlockedDestinationError, is_public_address, safe_addresses
from seowolf.crawler.options import CrawlOptions
from seowolf.crawler.politeness import HostThrottle
from tests.fixture_server import FixtureSite

__author__ = "@anhafxd"


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.1.2.3",
        "172.16.5.4",
        "192.168.1.1",
        "100.64.0.1",
        "169.254.169.254",
        "0.0.0.0",
        "224.0.0.1",
        "::1",
        "fd00:ec2::254",
        "fe80::1",
        "::ffff:127.0.0.1",
        "64:ff9b::7f00:1",
        "2002:7f00:1::",
    ],
)
def test_private_reserved_and_metadata_ranges_are_not_public(address: str) -> None:
    assert not is_public_address(address)


@pytest.mark.parametrize("address", ["93.184.216.34", "1.1.1.1", "2606:4700:4700::1111"])
def test_public_addresses_are_allowed(address: str) -> None:
    assert is_public_address(address)


async def test_loopback_and_localhost_are_blocked_by_default() -> None:
    with pytest.raises(BlockedDestinationError):
        await safe_addresses("127.0.0.1", 80, allow_private_networks=False)
    with pytest.raises(BlockedDestinationError):
        await safe_addresses("localhost", 80, allow_private_networks=False)
    with pytest.raises(BlockedDestinationError):
        await safe_addresses("metadata.google.internal", 80, allow_private_networks=False)


async def test_private_targets_pass_only_when_explicitly_allowed() -> None:
    assert await safe_addresses("127.0.0.1", 80, allow_private_networks=True) == ["127.0.0.1"]
    assert await safe_addresses("93.184.216.34", 80, allow_private_networks=False) == [
        "93.184.216.34"
    ]


async def test_backend_refuses_to_open_private_sockets() -> None:
    backend = GuardedNetworkBackend(allow_private_networks=False)
    with pytest.raises(BlockedDestinationError):
        await backend.connect_tcp("127.0.0.1", 80)


async def test_real_fetch_to_loopback_is_blocked(fixture_site: FixtureSite) -> None:
    options = CrawlOptions(start_url=fixture_site.url("/"), per_host_delay=0, max_retries=0)
    fetcher = PageFetcher(options, HostThrottle(0, 4))
    try:
        result = await fetcher.fetch(fixture_site.url("/"))
    finally:
        await fetcher.close()
    assert result.error == "blocked_private_network"
    assert result.final.status_code is None
