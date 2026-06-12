"""/feedback endpoint — 404 for missing runs, 200 for valid feedback."""

import uuid
from sqlalchemy import delete, select
from database import AsyncSessionLocal
from models import User, Agent_Outcomes
from repositories.user_repository import UserRepository
from repositories.agent_run_repository import AgentRunRepository
from repositories.agent_outcomes_repository import AgentOutcomesRepository


async def _seed_run_with_outcome(suffix: str) -> tuple[str, int]:
    """Create user + run + outcome in DB. Returns (user_id, run_id)."""
    uid = f"int-fb-{suffix}-{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as session:
        await UserRepository(session).create_user(uid)
        run_id = await AgentRunRepository(session).log_run(
            user_id=uid, message="test", action="expense_manager",
            parameters={"action": "log"}, result={"status": "success"},
            latency=0.5,
        )
        await AgentOutcomesRepository(session).record_outcome(
            run_id=run_id, user_id=uid, domain="expense",
            task_type="log", was_correct=True,
        )
        await session.commit()
        return uid, run_id


async def _cleanup(user_id: str):
    async with AsyncSessionLocal() as session:
        await session.execute(delete(User).where(User.user_id == user_id))
        await session.commit()


class TestFeedback:

    async def test_missing_run_returns_404(self, async_client, auth_headers):
        """Non-existent run_id -> 404."""
        resp = await async_client.post(
            "/feedback",
            json={"run_id": 9999999, "user_id": "nobody", "was_correct": True},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_valid_feedback_returns_200(self, async_client, auth_headers):
        """Valid run_id -> 200 with success message."""
        uid, run_id = await _seed_run_with_outcome("ok")
        try:
            resp = await async_client.post(
                "/feedback",
                json={
                    "run_id": run_id,
                    "user_id": uid,
                    "was_correct": False,
                    "correction": "Wrong action",
                },
                headers=auth_headers,
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "feedback recorded successfully"
        finally:
            await _cleanup(uid)

    async def test_feedback_updates_outcome_was_correct(
        self, async_client, auth_headers
    ):
        """After feedback, the outcome row reflects the correction."""
        uid, run_id = await _seed_run_with_outcome("upd")
        try:
            await async_client.post(
                "/feedback",
                json={
                    "run_id": run_id,
                    "user_id": uid,
                    "was_correct": False,
                },
                headers=auth_headers,
            )

            async with AsyncSessionLocal() as session:
                stmt = select(Agent_Outcomes).where(
                    Agent_Outcomes.run_id == run_id,
                    Agent_Outcomes.user_id == uid,
                )
                result = await session.execute(stmt)
                outcome = result.scalar_one()
                assert outcome.was_correct is False
        finally:
            await _cleanup(uid)
