from typing import Annotated

import typer
from rich.console import Console

from seowolf.cli.crawl_commands import crawl_app
from seowolf.cli.project_commands import project_app
from seowolf.signature import REPOSITORY_URL, SIGNATURE_LINE

__author__ = "@anhafxd"

app = typer.Typer(
    name="seowolf",
    help="SEO Wolf: self-hosted SEO crawler and site auditor.",
    no_args_is_help=True,
    add_completion=False,
    epilog=SIGNATURE_LINE,
)
app.add_typer(crawl_app, name="crawl")
app.add_typer(project_app, name="project")


def show_version(requested: bool) -> None:
    if requested:
        Console().print(f"[bold red]{SIGNATURE_LINE}[/]\n{REPOSITORY_URL}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", "-V", callback=show_version, is_eager=True, help="Show version."),
    ] = False,
) -> None:
    return None


def run() -> None:
    app()
