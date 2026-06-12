import uuid
from datetime import date, timedelta

import pytest
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


async def test_expense_tools_smoke():
    from database import AsyncSessionLocal

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

            get_budget = ExpenseManagerParams(
                action="get_budget",
                category="food",
            )
            get_budget_res = await tool.function(soft_user_id, get_budget, session)
            assert isinstance(get_budget_res, ToolResponse)
            assert get_budget_res.status == ToolStatus.SUCCESS
            assert isinstance(get_budget_res.data.get("start_date"), str)
            assert isinstance(get_budget_res.data.get("end_date"), str)

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
            assert res3.data is not None
            assert float(res3.data["total"]) == pytest.approx(20.0)
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


def test_set_budget_requires_category():
    with pytest.raises(ValueError, match="Missing required fields for set_budget"):
        ExpenseManagerParams(
            action="set_budget",
            budget=500.0,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )


def test_get_budget_rejects_write_fields():
    with pytest.raises(ValueError, match="Fields not allowed for get_budget"):
        ExpenseManagerParams(
            action="get_budget",
            category="food",
            budget=500.0,
        )


def test_get_budget_requires_category():
    with pytest.raises(ValueError, match="Missing required fields for get_budget"):
        ExpenseManagerParams(
            action="get_budget",
        )


async def test_agent_run_repository_serializes_dates_in_json_columns():
    from database import AsyncSessionLocal
    from repositories.agent_run_repository import AgentRunRepository

    user_id = f"test_{uuid.uuid4().hex}"

    async with AsyncSessionLocal() as session:
        await _create_test_user(session, user_id)

        try:
            repo = AgentRunRepository(session)
            run_id = await repo.log_run(
                user_id=user_id,
                message="get budget for food",
                action="expense_manager",
                parameters={
                    "action": "get_budget",
                    "category": "food",
                    "requested_on": date.today(),
                },
                result={
                    "status": "success",
                    "message": "Active budget found",
                    "data": {
                        "start_date": date.today(),
                        "end_date": date.today() + timedelta(days=30),
                    },
                },
                latency=1.23,
            )

            assert isinstance(run_id, int)
            assert run_id > 0
        finally:
            await _cleanup_test_user(session, user_id)
