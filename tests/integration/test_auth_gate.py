"""Verify every protected endpoint rejects unauthenticated requests."""

import pytest


ENDPOINTS = [
    pytest.param("POST", "/chat",
                 {"json": {"user_id": "t", "message": "hello"}},
                 id="chat"),
    pytest.param("POST", "/feedback",
                 {"json": {"run_id": 1, "user_id": "t", "was_correct": True}},
                 id="feedback"),
    pytest.param("GET", "/debug/runs", {}, id="debug_runs"),
    pytest.param("GET", "/debug/outcomes", {}, id="debug_outcomes"),
    pytest.param("GET", "/debug/slow_runs", {}, id="debug_slow_runs"),
    pytest.param("GET", "/debug/confidence",
                 {"params": {"user_id": "t", "domain": "x", "task_type": "y"}},
                 id="debug_confidence"),
]


class TestAuthGate:

    @pytest.mark.parametrize("method,path,kwargs", ENDPOINTS)
    async def test_missing_key_returns_401(
        self, async_client, method, path, kwargs
    ):
        """No X-API-Key header -> 401 Unauthorized."""
        resp = await getattr(async_client, method.lower())(path, **kwargs)
        assert resp.status_code == 401
        assert "X-API-Key" in str(resp.json())

    @pytest.mark.parametrize("method,path,kwargs", ENDPOINTS)
    async def test_wrong_key_returns_403(
        self, async_client, method, path, kwargs
    ):
        """Wrong X-API-Key value -> 403 Forbidden."""
        resp = await getattr(async_client, method.lower())(
            path, headers={"X-API-Key": "bogus-key"}, **kwargs
        )
        assert resp.status_code == 403
        assert "Invalid API key" in str(resp.json())

    async def test_chat_greeting_with_valid_key_returns_200(
        self, async_client, auth_headers
    ):
        """Greeting with valid key -> 200 (Layer 1, no LLM call)."""
        resp = await async_client.post(
            "/chat",
            json={"user_id": "test-user", "message": "hello"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
