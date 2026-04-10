import asyncio
import uuid
from datetime import date, timedelta

from sqlalchemy import delete

from core.tools_registry import bulid_tools_registry
from core.tool_response import ToolResponse, ToolStatus
from domains.expense.schemas import ExpenseManagerParams


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


def test_expense_tools_smoke():
    asyncio.run(_test_expense_tools_smoke())


async def _test_expense_tools_smoke():
    from database import AsyncSessionLocal, engine, Base

    await _ensure_tables(engine, Base)

    try:
        async with AsyncSessionLocal() as session:
            tools = bulid_tools_registry(session)
            tool = tools["expense_manager"]

            start = date.today() - timedelta(days=1)
            end = date.today() + timedelta(days=30)

            # Soft path
            soft_user_id = f"test_{uuid.uuid4().hex}"
            await _create_test_user(session, soft_user_id)
            try:
                set_budget = ExpenseManagerParams(
                    action="set_budget",
                    category="food",
                    budget=100.0,
                    start_date=start,
                    end_date=end,
                )
                res1 = await tool.function(soft_user_id, set_budget, session)
                assert isinstance(res1, ToolResponse)
                assert res1.status == ToolStatus.SUCCESS
                assert "budget" in res1.message.lower() or "created" in res1.message.lower()

                log = ExpenseManagerParams(
                    action="log",
                    amount=20.0,
                    category="food",
                    note="apple",
                    mode="soft",
                )
                res2 = await tool.function(soft_user_id, log, session)
                assert isinstance(res2, ToolResponse)
                assert res2.status == ToolStatus.SUCCESS
                assert "expense logged" in res2.message.lower()


                analyze = ExpenseManagerParams(
                    action="analyze",
                    category="food",
                    period="this month",
                )
                res3 = await tool.function(soft_user_id, analyze, session)
                assert isinstance(res3, ToolResponse)
                assert res3.status == ToolStatus.SUCCESS
                assert "total expense" in res3.message.lower()
            finally:
                await _cleanup_test_user(session, soft_user_id)

            # Hard reject path
            hard_user_id = f"test_{uuid.uuid4().hex}"
            await _create_test_user(session, hard_user_id)
            try:
                set_budget = ExpenseManagerParams(
                    action="set_budget",
                    category="transport",
                    budget=30.0,
                    start_date=start,
                    end_date=end,
                )
                budget_res = await tool.function(hard_user_id, set_budget, session)
                assert isinstance(budget_res, ToolResponse)
                assert budget_res.status == ToolStatus.SUCCESS
                

                log = ExpenseManagerParams(
                    action="log",
                    amount=40.0,
                    category="transport",
                    note="uber",
                    mode="hard",
                )
                res = await tool.function(hard_user_id, log, session)
                assert isinstance(res, ToolResponse)
                assert res.status == ToolStatus.FAILED
                assert "rejected" in res.message.lower() or "budget exceeded" in res.message.lower()
            finally:
                await _cleanup_test_user(session, hard_user_id)
    finally:
        # Prevent cross-event-loop pool reuse when multiple asyncio.run tests execute in one pytest run.
        await engine.dispose()