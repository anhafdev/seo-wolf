from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from seowolf.crawler.options import CrawlOptions

__author__ = "@anhafxd"


class OptionsProblem(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def read_config_file(path: Path | None) -> tuple[str | None, dict[str, Any]]:
    if path is None:
        return None, {}
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as problem:
        raise OptionsProblem(f"could not read {path}: {problem}") from problem
    if not isinstance(content, dict):
        raise OptionsProblem(f"{path} must contain a YAML mapping")
    project_name = content.get("project")
    crawl_section = content.get("crawl", {k: v for k, v in content.items() if k != "project"})
    if not isinstance(crawl_section, dict):
        raise OptionsProblem(f"the crawl section in {path} must be a mapping")
    return project_name, crawl_section


def read_url_list(path: Path | None) -> list[str]:
    if path is None:
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as problem:
        raise OptionsProblem(f"could not read {path}: {problem}") from problem
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def parse_header_pairs(values: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for value in values:
        name, separator, content = value.partition(":")
        if not separator or not name.strip():
            raise OptionsProblem(f"header {value!r} must look like 'Name: value'")
        headers[name.strip()] = content.strip()
    return headers


def build_options(
    start_url: str | None, config: dict[str, Any], overrides: dict[str, Any]
) -> CrawlOptions:
    merged = dict(config)
    for key, value in overrides.items():
        if value is None or value == [] or value == {}:
            continue
        merged[key] = value
    if start_url:
        merged["start_url"] = start_url
    if "start_url" not in merged and merged.get("url_list"):
        merged["start_url"] = merged["url_list"][0]
    if "start_url" not in merged:
        raise OptionsProblem("give a start URL, a url_list or a config file with start_url")
    try:
        return CrawlOptions.model_validate(merged)
    except ValidationError as problem:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in problem.errors()
        )
        raise OptionsProblem(details) from problem
