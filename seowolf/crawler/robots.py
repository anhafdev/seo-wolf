import re
from dataclasses import dataclass, field
from functools import cached_property

from yarl import URL

from seowolf.signature import ROBOTS_AGENT_TOKEN

__author__ = "@anhafxd"

MAX_ROBOTS_BYTES = 512_000


def compile_robots_pattern(pattern: str) -> re.Pattern[str]:
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    expression = ".*".join(re.escape(part) for part in body.split("*"))
    return re.compile(expression + ("$" if anchored else ""))


@dataclass(frozen=True)
class RobotsRule:
    allow: bool
    pattern: str

    @cached_property
    def expression(self) -> re.Pattern[str]:
        return compile_robots_pattern(self.pattern)

    def matches(self, target: str) -> bool:
        return self.expression.match(target) is not None


def rule_beats(candidate: RobotsRule, current: RobotsRule) -> bool:
    if len(candidate.pattern) != len(current.pattern):
        return len(candidate.pattern) > len(current.pattern)
    return candidate.allow and not current.allow


@dataclass
class RobotsGroup:
    agents: list[str] = field(default_factory=list)
    rules: list[RobotsRule] = field(default_factory=list)
    crawl_delay: float | None = None


@dataclass
class RobotsPolicy:
    groups: list[RobotsGroup] = field(default_factory=list)
    sitemaps: list[str] = field(default_factory=list)
    blanket_allow: bool | None = None
    status_code: int | None = None
    body: str = ""

    def matching_groups(self, agent_token: str) -> list[RobotsGroup]:
        token = agent_token.lower()
        named = [group for group in self.groups if token in group.agents]
        return named or [group for group in self.groups if "*" in group.agents]

    def is_allowed(self, url: URL, agent_token: str = ROBOTS_AGENT_TOKEN) -> bool:
        if self.blanket_allow is not None:
            return self.blanket_allow
        target = url.raw_path_qs or "/"
        if target == "/robots.txt":
            return True
        best_rule: RobotsRule | None = None
        for group in self.matching_groups(agent_token):
            for rule in group.rules:
                if not rule.matches(target):
                    continue
                if best_rule is None or rule_beats(rule, best_rule):
                    best_rule = rule
        return best_rule is None or best_rule.allow

    def crawl_delay(self, agent_token: str = ROBOTS_AGENT_TOKEN) -> float | None:
        delays = [
            group.crawl_delay
            for group in self.matching_groups(agent_token)
            if group.crawl_delay is not None
        ]
        return min(delays) if delays else None


def split_robots_line(line: str) -> tuple[str, str] | None:
    content = line.split("#", 1)[0].strip()
    if ":" not in content:
        return None
    name, value = content.split(":", 1)
    return name.strip().lower(), value.strip()


def parse_robots(text: str) -> RobotsPolicy:
    policy = RobotsPolicy(body=text)
    current: RobotsGroup | None = None
    collecting_agents = False
    for line in text.splitlines():
        parsed = split_robots_line(line)
        if parsed is None:
            continue
        name, value = parsed
        if name == "user-agent":
            if current is None or not collecting_agents:
                current = RobotsGroup()
                policy.groups.append(current)
            current.agents.append(value.lower())
            collecting_agents = True
            continue
        if name == "sitemap":
            if value:
                policy.sitemaps.append(value)
            continue
        collecting_agents = False
        if current is None:
            continue
        if name in {"allow", "disallow"} and value:
            current.rules.append(RobotsRule(allow=name == "allow", pattern=value))
        elif name == "crawl-delay":
            current.crawl_delay = parse_crawl_delay(value)
    return policy


def parse_crawl_delay(value: str) -> float | None:
    try:
        delay = float(value)
    except ValueError:
        return None
    return delay if delay >= 0 else None


def policy_from_response(status_code: int | None, body: bytes) -> RobotsPolicy:
    if status_code is not None and 200 <= status_code < 300:
        text = body[:MAX_ROBOTS_BYTES].decode("utf-8", errors="replace").lstrip("﻿")
        policy = parse_robots(text)
        policy.status_code = status_code
        return policy
    if status_code is not None and 400 <= status_code < 500 and status_code != 429:
        return RobotsPolicy(blanket_allow=True, status_code=status_code)
    return RobotsPolicy(blanket_allow=False, status_code=status_code)
