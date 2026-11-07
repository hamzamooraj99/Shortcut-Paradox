import pytest

import fading_trails.llm as llm


@pytest.fixture(autouse=True)
def no_real_keys(monkeypatch):
    """Never let a real API key reach a test: a failing test prints the request headers."""
    monkeypatch.setattr(llm, "load_env", lambda: None)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("ADAPTION_API_KEY", "test-key")
