from pathlib import Path

import pytest
from typer.testing import CliRunner

from seowolf.cli.app import app
from seowolf.cli.options_loader import (
    OptionsProblem,
    build_options,
    parse_header_pairs,
    read_config_file,
)
from tests.fixture_server import FixtureSite

__author__ = "@anhafxd"

runner = CliRunner()


@pytest.fixture
def data_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("SEOWOLF_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("COLUMNS", "160")
    return tmp_path


def test_version_shows_the_signature() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "@anhafxd" in result.output and "SEO Wolf" in result.output


def test_crawl_start_summary_and_list(data_folder: Path, fixture_site: FixtureSite) -> None:
    started = runner.invoke(
        app,
        ["crawl", "start", fixture_site.url("/"), "--allow-private-networks", "--delay", "0"],
    )
    assert started.exit_code == 0, started.output
    assert "Broken internal links" in started.output
    assert "contact.html" in started.output
    assert "finished with status done" in started.output
    listed = runner.invoke(app, ["crawl", "list"])
    assert "127.0.0.1" in listed.output and "done" in listed.output
    summary = runner.invoke(app, ["crawl", "summary", "1"])
    assert summary.exit_code == 0 and "Status codes" in summary.output
    projects = runner.invoke(app, ["project", "list"])
    assert "127.0.0.1" in projects.output


def test_ignore_robots_prints_a_warning(data_folder: Path, fixture_site: FixtureSite) -> None:
    result = runner.invoke(
        app,
        [
            "crawl",
            "start",
            fixture_site.url("/"),
            "--allow-private-networks",
            "--ignore-robots",
            "--delay",
            "0",
            "--max-urls",
            "2",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "robots.txt is ignored" in result.output


def test_unknown_crawl_and_bad_options_fail_cleanly(data_folder: Path) -> None:
    missing = runner.invoke(app, ["crawl", "resume", "999"])
    assert missing.exit_code == 2 and "does not exist" in missing.output
    bad = runner.invoke(app, ["crawl", "start", "ftp://example.com/"])
    assert bad.exit_code == 2 and "start_url" in bad.output


def test_yaml_config_is_merged_with_flags(tmp_path: Path) -> None:
    config_file = tmp_path / "wolf.yaml"
    config_file.write_text(
        "project: shop\ncrawl:\n  start_url: https://example.com/\n  max_urls: 900\n"
        "  exclude_patterns: ['/cart']\n",
        encoding="utf-8",
    )
    project, values = read_config_file(config_file)
    options = build_options(None, values, {"max_urls": 50, "concurrency": None})
    assert project == "shop"
    assert options.max_urls == 50
    assert options.exclude_patterns == ["/cart"]


def test_header_pairs_are_validated() -> None:
    assert parse_header_pairs(["X-Audit: yes"]) == {"X-Audit": "yes"}
    with pytest.raises(OptionsProblem):
        parse_header_pairs(["missing-colon"])
