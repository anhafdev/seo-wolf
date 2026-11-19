from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from seowolf.storage.models_projects import Project

__author__ = "@anhafxd"


async def find_project(session: AsyncSession, name: str) -> Project | None:
    return await session.scalar(select(Project).where(Project.name == name))


async def find_or_create_project(session: AsyncSession, name: str, start_url: str) -> Project:
    project = await find_project(session, name)
    if project is not None:
        return project
    project = Project(name=name, start_url=start_url, settings={}, branding={})
    session.add(project)
    await session.flush()
    return project


async def list_projects(session: AsyncSession) -> list[Project]:
    return list(await session.scalars(select(Project).order_by(Project.name)))
