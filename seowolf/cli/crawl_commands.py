import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from seowolf.cli.crawl_runner import CrawlNotFoundError, load_summary, resume_crawl, start_crawl
from seowolf.cli.options_loader import (
    OptionsProblem,
    build_options,
    parse_header_pairs,
    read_config_file,
    read_url_list,
)
from seowolf.cli.summary_view import show_summary
from seowolf.settings import load_settings
from seowolf.storage.database import open_database
from seowolf.storage.repositories_crawls import recent_crawls

__author__ = "@anhafxd"

crawl_app = typer.Typer(help="Start, resume and inspect crawls.", no_args_is_help=True)
console = Console()

Repeated = Annotated[list[str] | None, typer.Option()]


def fail(message: str) -> None:
    console.print(f"[bold red]Error:[/] {message}")
    raise typer.Exit(code=2)


@crawl_app.command("start")
def start_command(
    url: Annotated[str | None, typer.Argument(help="Start URL of a site you may audit.")] = None,
    project: Annotated[str | None, typer.Option("--project", "-p", help="Project name.")] = None,
    config: Annotated[Path | None, typer.Option("--config", "-c", help="YAML config.")] = None,
    max_urls: Annotated[int | None, typer.Option(help="Maximum pages to crawl.")] = None,
    max_depth: Annotated[int | None, typer.Option(help="Maximum click depth.")] = None,
    concurrency: Annotated[int | None, typer.Option(help="Parallel requests (1-64).")] = None,
    delay: Annotated[float | None, typer.Option(help="Seconds between requests per host.")] = None,
    timeout: Annotated[float | None, typer.Option(help="Request timeout in seconds.")] = None,
    include: Repeated = None,
    exclude: Repeated = None,
    sitemap: Repeated = None,
    header: Annotated[list[str] | None, typer.Option(help="Extra header 'Name: value'.")] = None,
    url_list: Annotated[Path | None, typer.Option(help="File with one URL per line.")] = None,
    list_mode: Annotated[bool, typer.Option(help="Audit only the listed URLs.")] = False,
    all_subdomains: Annotated[bool, typer.Option(help="Treat subdomains as internal.")] = False,
    query_policy: Annotated[str | None, typer.Option(help="keep, strip_listed, strip_all.")] = None,
    trailing_slash: Annotated[str | None, typer.Option(help="keep, add or remove.")] = None,
    user_agent: Annotated[str | None, typer.Option(help="Custom User-Agent string.")] = None,
    ignore_robots: Annotated[bool, typer.Option(help="Ignore robots.txt (own sites).")] = False,
    follow_nofollow: Annotated[bool, typer.Option(help="Follow rel=nofollow links.")] = False,
    no_resources: Annotated[bool, typer.Option(help="Skip image, CSS and JS checks.")] = False,
    no_external: Annotated[bool, typer.Option(help="Skip external link checks.")] = False,
    store_html: Annotated[bool, typer.Option(help="Keep raw HTML (capped per page).")] = False,
    allow_private_networks: Annotated[
        bool, typer.Option(help="Allow private and loopback targets (CLI only).")
    ] = False,
) -> None:
    try:
        config_project, config_values = read_config_file(config)
        overrides = {
            "max_urls": max_urls,
            "max_depth": max_depth,
            "concurrency": concurrency,
            "per_host_delay": delay,
            "timeout_seconds": timeout,
            "include_patterns": include,
            "exclude_patterns": exclude,
            "sitemap_urls": sitemap,
            "custom_headers": parse_header_pairs(header or []),
            "url_list": read_url_list(url_list),
            "list_mode": list_mode or None,
            "subdomain_policy": "all_subdomains" if all_subdomains else None,
            "query_policy": query_policy,
            "trailing_slash": trailing_slash,
            "user_agent": user_agent,
            "respect_robots": False if ignore_robots else None,
            "follow_nofollow": follow_nofollow or None,
            "check_resources": False if no_resources else None,
            "check_external_links": False if no_external else None,
            "store_html": store_html or None,
            "allow_private_networks": allow_private_networks or None,
        }
        options = build_options(url, config_values, overrides)
    except OptionsProblem as problem:
        fail(problem.message)
        return
    if not options.respect_robots:
        console.print(
            "[bold yellow]Warning:[/] robots.txt is ignored. Only do this on sites you own."
        )
    if options.allow_private_networks:
        console.print("[yellow]Private network targets are allowed for this crawl.[/]")
    crawl_id, status, summary = asyncio.run(
        start_crawl(load_settings(), project or config_project, options, console)
    )
    show_summary(console, crawl_id, status, summary)
    if status == "failed":
        raise typer.Exit(code=1)


@crawl_app.command("resume")
def resume_command(crawl_id: Annotated[int, typer.Argument(help="Crawl number.")]) -> None:
    try:
        crawl_number, status, summary = asyncio.run(
            resume_crawl(load_settings(), crawl_id, console)
        )
    except CrawlNotFoundError as problem:
        fail(str(problem))
        return
    show_summary(console, crawl_number, status, summary)


@crawl_app.command("summary")
def summary_command(crawl_id: Annotated[int, typer.Argument(help="Crawl number.")]) -> None:
    try:
        summary = asyncio.run(load_summary(load_settings(), crawl_id))
    except CrawlNotFoundError as problem:
        fail(str(problem))
        return
    show_summary(console, crawl_id, "stored", summary)


async def crawl_rows(limit: int) -> list[tuple[str, ...]]:
    engine, sessions = await open_database(load_settings().resolved_database_url())
    try:
        async with sessions() as session:
            rows = await recent_crawls(session, limit=limit)
    finally:
        await engine.dispose()
    return [
        (
            str(crawl.id),
            project.name,
            crawl.status,
            str(crawl.totals.get("pages_done", 0)),
            crawl.created_at.strftime("%Y-%m-%d %H:%M"),
        )
        for crawl, project in rows
    ]


@crawl_app.command("list")
def list_command(limit: Annotated[int, typer.Option(help="How many crawls.")] = 20) -> None:
    table = Table(title="Saved crawls", title_style="bold red")
    for heading in ("#", "Project", "Status", "Pages", "Created"):
        table.add_column(heading)
    for row in asyncio.run(crawl_rows(limit)):
        table.add_row(*row)
    console.print(table)
