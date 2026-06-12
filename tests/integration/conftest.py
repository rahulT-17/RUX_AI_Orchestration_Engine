"""Shared fixtures for HTTP-level RUX integration tests.

Uses httpx.AsyncClient + ASGITransport so all async code (DB, handlers)
runs on the same event loop — avoids asyncpg InterfaceError caused by
TestClient's thread-based loop separation.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from starlette.requests import Request
from starlette.responses import Response

from main import app
from core.config import API_KEY
from api.routes import rate_limit_chat, rate_limit_feedback
from api.debug_routes import rate_limit_debug


# ── Rate limit bypass ───────────────────────────────────────────────
async def _no_rate_limit(request: Request, response: Response):
    return None


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def test_app():
    """FastAPI app with rate-limiting disabled for test stability."""
    app.dependency_overrides[rate_limit_chat] = _no_rate_limit
    app.dependency_overrides[rate_limit_feedback] = _no_rate_limit
    app.dependency_overrides[rate_limit_debug] = _no_rate_limit
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(test_app):
    """Async HTTP client bound to the test app — same event loop as DB."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """Valid API key — reads from whatever config is loaded."""
    return {"X-API-Key": API_KEY}


@pytest.fixture
def mock_llm_conversational():
    """LLM returns a conversational (non-action) JSON — for Layer-2/3
    tests where no tool execution is expected.
    """
    patcher = patch.multiple(
        "services.llm_services.LLMService",
        generate=AsyncMock(
            return_value='{"action":"conversational","parameters":{}}'
        ),
        converse=AsyncMock(return_value="Mock conversational reply."),
    )
    with patcher:
        yield


@pytest.fixture
def mock_llm_log_expense():
    """LLM returns a valid expense_manager log action.

    Used for testing the full action -> execution -> response flow
    without needing a real LLM call.
    """
    import json
    patcher = patch.multiple(
        "services.llm_services.LLMService",
        generate=AsyncMock(
            return_value=json.dumps({
                "action": "expense_manager",
                "parameters": {
                    "action": "log",
                    "amount": 100,
                    "category": "food",
                    "mode": "soft",
                },
            })
        ),
        converse=AsyncMock(return_value="Mock conversational reply."),
    )
    with patcher:
        yield
