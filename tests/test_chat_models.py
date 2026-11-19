"""Tests for remapping retired OpenAI chat models."""

from app.utils.chat_models import (
    DEFAULT_CHAT_MODEL,
    chat_request_kwargs,
    get_idea_model,
    resolve_chat_model,
)


def test_retired_gpt4_and_gpt35_map_to_current_default():
    assert resolve_chat_model("gpt-4") == DEFAULT_CHAT_MODEL
    assert resolve_chat_model("gpt-3.5-turbo") == DEFAULT_CHAT_MODEL
    assert resolve_chat_model("gpt-4o-mini") == DEFAULT_CHAT_MODEL
    assert resolve_chat_model("gpt-4-turbo-2024-04-09") == DEFAULT_CHAT_MODEL
    assert resolve_chat_model(None) == DEFAULT_CHAT_MODEL
    assert resolve_chat_model("") == DEFAULT_CHAT_MODEL


def test_live_model_is_left_alone():
    assert resolve_chat_model("gpt-5.6-sol") == "gpt-5.6-sol"
    assert resolve_chat_model(DEFAULT_CHAT_MODEL) == DEFAULT_CHAT_MODEL


def test_idea_model_ignores_retired_env(monkeypatch):
    monkeypatch.setenv("OPENAI_IDEA_MODEL", "gpt-3.5-turbo")
    assert get_idea_model() == DEFAULT_CHAT_MODEL


def test_idea_model_honors_live_env(monkeypatch):
    monkeypatch.setenv("OPENAI_IDEA_MODEL", "gpt-5.6-luna")
    assert get_idea_model() == "gpt-5.6-luna"


def test_reasoning_models_disable_reasoning_effort():
    assert chat_request_kwargs("gpt-5.6-terra") == {
        "model": "gpt-5.6-terra",
        "reasoning_effort": "none",
    }
    assert chat_request_kwargs("gpt-4o") == {"model": "gpt-4o"}
