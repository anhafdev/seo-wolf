from rich.console import Console
from rich.table import Table

from seowolf.signature import SIGNATURE_LINE
from seowolf.storage.repositories_pages import CrawlSummary

__author__ = "@anhafxd"

STATUS_COLOURS = {2: "green", 3: "yellow", 4: "red", 5: "bold red"}


def status_label(status_code: int | None) -> str:
    if status_code is None:
        return "[dim]no response[/]"
    colour = STATUS_COLOURS.get(status_code // 100, "white")
    return f"[{colour}]{status_code}[/]"


def overview_table(summary: CrawlSummary) -> Table:
    table = Table(title="Crawl overview", title_style="bold red", show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("Pages stored", str(summary.page_total))
    table.add_row("Redirects", str(summary.redirect_count))
    table.add_row("Redirect chains (2+ hops)", str(summary.long_chains))
    table.add_row("Redirect loops", str(summary.redirect_loops))
    table.add_row("Sitemap files", str(summary.sitemap_files))
    table.add_row("Sitemap URLs", str(summary.sitemap_urls))
    return table


def status_table(summary: CrawlSummary) -> Table:
    table = Table(title="Status codes", title_style="bold blue")
    table.add_column("Status")
    table.add_column("Pages", justify="right")
    for status_code, count in summary.status_counts:
        table.add_row(status_label(status_code), str(count))
    return table


def indexability_table(summary: CrawlSummary) -> Table:
    table = Table(title="Indexability", title_style="bold blue")
    table.add_column("Reason")
    table.add_column("Pages", justify="right")
    for reason, count in summary.indexability_counts:
        table.add_row(reason, str(count))
    return table


def broken_links_table(summary: CrawlSummary) -> Table:
    table = Table(title="Broken internal links", title_style="bold red")
    table.add_column("Found on", overflow="fold")
    table.add_column("Links to", overflow="fold")
    table.add_column("Status")
    for source_url, target_url, status_code in summary.broken_links:
        table.add_row(source_url, target_url, status_label(status_code))
    return table


def broken_resources_table(summary: CrawlSummary) -> Table:
    table = Table(title="Broken resources and external links", title_style="bold red")
    table.add_column("Kind")
    table.add_column("URL", overflow="fold")
    table.add_column("Status")
    for kind, url, status_code, error in summary.broken_resources:
        table.add_row(kind, url, error or status_label(status_code))
    return table


def show_summary(console: Console, crawl_id: int, status: str, summary: CrawlSummary) -> None:
    console.print()
    console.print(overview_table(summary))
    console.print(status_table(summary))
    console.print(indexability_table(summary))
    if summary.broken_links:
        console.print(broken_links_table(summary))
    if summary.broken_resources:
        console.print(broken_resources_table(summary))
    if summary.slowest_pages:
        slowest = Table(title="Slowest responses", title_style="bold blue")
        slowest.add_column("URL", overflow="fold")
        slowest.add_column("ms", justify="right")
        for url, response_ms in summary.slowest_pages:
            slowest.add_row(url, str(response_ms))
        console.print(slowest)
    state_colour = {"done": "green", "paused": "yellow"}.get(status, "red")
    console.print(f"Crawl [bold]#{crawl_id}[/] finished with status [{state_colour}]{status}[/]")
    if status == "paused":
        console.print(f"Resume any time with [bold]seowolf crawl resume {crawl_id}[/]")
    console.print(f"[dim]{SIGNATURE_LINE}[/]")
