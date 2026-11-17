"""Global pytest configuration ensuring hermetic offline test execution."""

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def force_mock_offline_llm(monkeypatch: pytest.MonkeyPatch):
    """Prevent tests from hitting live Gemini API via v2/.env GOOGLE_API_KEY."""
    monkeypatch.setenv("GOOGLE_API_KEY", "mock_offline")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
