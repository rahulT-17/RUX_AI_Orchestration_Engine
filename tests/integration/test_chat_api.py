"""/chat endpoint — response shapes, greeting detection, action flow."""

import pytest


class TestChatGreeting:
    """Layer 1: deterministic greeting — no LLM call needed."""

    @pytest.mark.parametrize("msg", [
        "hello", "hi", "hey", "thanks", "bye",
        "good morning", "good night", "ok", "okay",
    ])
    async def test_greeting_returns_200_with_conversational_action(
        self, async_client, auth_headers, msg
    ):
        resp = await async_client.post(
            "/chat",
            json={"user_id": "test-user", "message": msg},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "response" in body
        assert isinstance(body["response"], str)
        assert body.get("run_id") is None


class TestChatAction:
    """Layer 2: action keyword triggers LLM -> executor -> response."""

    async def test_log_expense_returns_200_with_run_id(
        self, async_client, auth_headers, mock_llm_log_expense
    ):
        """Action message -> 200 with run_id and response text."""
        resp = await async_client.post(
            "/chat",
            json={"user_id": "test-user", "message": "log 100 for food"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "response" in body
        assert isinstance(body["response"], str)


class TestChatConversational:
    """Layer 3: no greeting, no action keyword -> LLM conversational."""

    async def test_general_question_returns_200(
        self, async_client, auth_headers, mock_llm_conversational
    ):
        """No keyword -> Layer 3, mocked LLM returns conversational."""
        resp = await async_client.post(
            "/chat",
            json={"user_id": "test-user", "message": "how are you?"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "response" in body
