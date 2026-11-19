import asyncio

import typer
from rich.console import Console
from rich.table import Table

from seowolf.settings import load_settings
from seowolf.storage.database import open_database
from seowolf.storage.repositories_projects import list_projects

__author__ = "@anhafxd"

project_app = typer.Typer(help="Manage saved projects.", no_args_is_help=True)
console = Console()


async def project_rows() -> list[tuple[str, str, str]]:
    engine, sessions = await open_database(load_settings().resolved_database_url())
    try:
        async with sessions() as session:
            projects = await list_projects(session)
    finally:
        await engine.dispose()
    return [
        (project.name, project.start_url, project.created_at.strftime("%Y-%m-%d"))
        for project in projects
    ]


@project_app.command("list")
def list_command() -> None:
    table = Table(title="Projects", title_style="bold red")
    for heading in ("Name", "Start URL", "Created"):
        table.add_column(heading)
    for row in asyncio.run(project_rows()):
        table.add_row(*row)
    console.print(table)
