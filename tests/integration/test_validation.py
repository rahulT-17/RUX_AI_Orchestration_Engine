"""Input guardrails — max length, required fields, blank rejection."""

import pytest


class TestChatValidation:

    ENDPOINT = "/chat"

    async def test_missing_message(self, async_client, auth_headers):
        """message omitted -> 422."""
        resp = await async_client.post(
            self.ENDPOINT,
            json={"user_id": "test"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_blank_message(self, async_client, auth_headers):
        """message is whitespace -> 422 (validator strips + rejects blank)."""
        resp = await async_client.post(
            self.ENDPOINT,
            json={"user_id": "test", "message": "   "},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_message_too_long(self, async_client, auth_headers):
        """message > MAX_MESSAGE_LENGTH (1000) -> 422."""
        resp = await async_client.post(
            self.ENDPOINT,
            json={"user_id": "test", "message": "x" * 1001},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_user_id_too_long(self, async_client, auth_headers):
        """user_id > MAX_USER_ID_LENGTH (50) -> 422."""
        resp = await async_client.post(
            self.ENDPOINT,
            json={"user_id": "a" * 51, "message": "hello"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_blank_user_id(self, async_client, auth_headers):
        """user_id is empty string -> 422."""
        resp = await async_client.post(
            self.ENDPOINT,
            json={"user_id": "", "message": "hello"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestFeedbackValidation:

    ENDPOINT = "/feedback"

    async def test_missing_run_id(self, async_client, auth_headers):
        """run_id omitted -> 422."""
        resp = await async_client.post(
            self.ENDPOINT,
            json={"user_id": "test", "was_correct": True},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_correction_too_long(self, async_client, auth_headers):
        """correction > MAX_CORRECTION_LENGTH (500) -> 422."""
        resp = await async_client.post(
            self.ENDPOINT,
            json={
                "run_id": 1,
                "user_id": "test",
                "was_correct": False,
                "correction": "x" * 501,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422
