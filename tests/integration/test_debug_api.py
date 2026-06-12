"""Debug/observability endpoints — empty-state tests."""

import pytest


class TestDebugRuns:

    async def test_runs_returns_200(self, async_client, auth_headers):
        """GET /debug/runs -> 200 (may be empty list)."""
        resp = await async_client.get("/debug/runs", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_runs_accepts_limit_param(self, async_client, auth_headers):
        """GET /debug/runs?limit=5 -> respects limit."""
        resp = await async_client.get(
            "/debug/runs?limit=5", headers=auth_headers
        )
        assert resp.status_code == 200
        assert len(resp.json()) <= 5


class TestDebugOutcomes:

    async def test_outcomes_returns_200(self, async_client, auth_headers):
        """GET /debug/outcomes -> 200."""
        resp = await async_client.get("/debug/outcomes", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestDebugSlowRuns:

    async def test_slow_runs_returns_200(self, async_client, auth_headers):
        """GET /debug/slow_runs -> 200."""
        resp = await async_client.get("/debug/slow_runs", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestDebugConfidence:

    async def test_confidence_without_data_returns_null(
        self, async_client, auth_headers
    ):
        """No feedback yet -> confidence is null, samples may be 0."""
        resp = await async_client.get(
            "/debug/confidence",
            params={"user_id": "new-user", "domain": "expense", "task_type": "log"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["confidence"] is None


class TestDebugCriticResult:

    async def test_critic_result_missing_run_returns_404(
        self, async_client, auth_headers
    ):
        """Non-existent run_id -> 404."""
        resp = await async_client.get(
            "/debug/critic_result/9999999", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_critic_result_optional_user_id(
        self, async_client, auth_headers
    ):
        """user_id query param is optional — still 404 for missing run."""
        resp = await async_client.get(
            "/debug/critic_result/0", headers=auth_headers
        )
        assert resp.status_code == 404
