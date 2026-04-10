import asyncio
import uuid

from sqlalchemy import delete

from core.tool_response import ToolResponse, ToolStatus
from core.tools_registry import bulid_tools_registry
from domains.project.schemas import CreateProjectParams, DeleteProjectParams


async def _create_test_user(session, user_id: str) -> None:
    from repositories.user_repository import UserRepository

    repo = UserRepository(session)
    await repo.create_user(user_id)


async def _cleanup_test_user(session, user_id: str) -> None:
    from models import User

    await session.execute(delete(User).where(User.user_id == user_id))
    await session.commit()


async def _ensure_tables(engine, Base) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def test_project_tools_smoke():
    asyncio.run(_test_project_tools_smoke())


async def _test_project_tools_smoke():
    from database import AsyncSessionLocal, engine, Base

    await _ensure_tables(engine, Base)

    try:
        async with AsyncSessionLocal() as session:
            tools = bulid_tools_registry(session)

            create_tool = tools["create_project"]
            delete_tool = tools["delete_project"]

            user_id = f"test_{uuid.uuid4().hex}"
            await _create_test_user(session, user_id)

            try:
                # Path 1: create + delete by project name.
                create_params = CreateProjectParams(
                    name="SmokeProject",
                    description="project domain smoke test",
                )
                create_result = await create_tool.function(user_id, create_params, session)
                assert isinstance(create_result, ToolResponse)
                assert create_result.status == ToolStatus.SUCCESS
                assert "created successfully" in create_result.message.lower()

                delete_params = DeleteProjectParams(name="SmokeProject")
                delete_result = await delete_tool.function(user_id, delete_params, session)
                assert isinstance(delete_result, ToolResponse)
                assert delete_result.status == ToolStatus.SUCCESS
                assert "deleted successfully" in delete_result.message.lower()

                # Path 2: create + delete by project id.
                create_params_by_id = CreateProjectParams(  
                    name="SmokeProjectById",
                    description="project delete by id path",
                )
                create_result_by_id = await create_tool.function(user_id, create_params_by_id, session)
                assert isinstance(create_result_by_id, ToolResponse)
                assert create_result_by_id.status == ToolStatus.SUCCESS
                assert "created successfully" in create_result_by_id.message.lower()

                project_id = int(create_result_by_id.data["project_id"])
                delete_params_by_id = DeleteProjectParams(project_id=project_id)
                delete_result_by_id = await delete_tool.function(user_id, delete_params_by_id, session)
                assert isinstance(delete_result_by_id, ToolResponse)
                assert delete_result_by_id.status == ToolStatus.SUCCESS
                assert "deleted successfully" in delete_result_by_id.message.lower()
            finally:
                await _cleanup_test_user(session, user_id)
    finally:
        # Prevent cross-event-loop pool reuse when multiple asyncio.run tests execute in one pytest run.
        await engine.dispose()
