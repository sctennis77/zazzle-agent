"""Resolve chat models that OpenAI has shut down.

Daily commissions call the Chat Completions API for comment summaries and
product ideas. gpt-4 and gpt-3.5-turbo stopped accepting requests on
2026-10-23, which is when scheduled generations started failing in a few
seconds. gpt-4o-mini remains callable until 2027-01-14; new work uses the
current replacement so the next shutdown does not stop the gallery again.
"""

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_CHAT_MODEL = "gpt-5.6-terra"

# Exact ids that no longer accept requests, plus the deprecated 4o/4.1 family
# whose shutdown is already scheduled. Prefix checks below cover snapshots.
RETIRED_CHAT_MODELS = {
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-0125",
    "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-instruct",
    "gpt-4",
    "gpt-4-0613",
    "gpt-4-32k",
    "gpt-4-turbo",
    "gpt-4-turbo-preview",
    "gpt-4-turbo-2024-04-09",
    "gpt-4-1106-preview",
    "gpt-4-0125-preview",
    "gpt-4.1",
    "gpt-4.1-2025-04-14",
    "gpt-4.1-mini",
    "gpt-4.1-mini-2025-04-14",
    "gpt-4.1-nano",
    "gpt-4.1-nano-2025-04-14",
    "gpt-4o",
    "gpt-4o-2024-05-13",
    "gpt-4o-2024-08-06",
    "gpt-4o-2024-11-20",
    "gpt-4o-mini",
    "gpt-4o-mini-2024-07-18",
    "o1",
    "o1-2024-12-17",
    "o1-mini",
    "o1-pro",
    "o3-mini",
    "o3-mini-2025-01-31",
    "o4-mini",
    "o4-mini-2025-04-16",
}


def resolve_chat_model(model: Optional[str]) -> str:
    """Map a configured chat model onto one the API still serves."""
    if _is_retired(model):
        logger.warning(
            "Chat model '%s' is retired or unset; using '%s'",
            model or "(unset)",
            DEFAULT_CHAT_MODEL,
        )
        return DEFAULT_CHAT_MODEL
    assert model is not None
    return model


def get_idea_model() -> str:
    """Return the chat model used for product ideas and comment summaries."""
    return resolve_chat_model(os.getenv("OPENAI_IDEA_MODEL", DEFAULT_CHAT_MODEL))


def chat_request_kwargs(model: str) -> Dict[str, Any]:
    """Build Chat Completions kwargs for a resolved model.

    GPT-5.6 defaults to medium reasoning, which is wasted spend for a
    structured theme/title/description reply and can omit plain text content.
    """
    kwargs: Dict[str, Any] = {"model": model}
    if model.startswith("gpt-5") or model.startswith("gpt-6"):
        kwargs["reasoning_effort"] = "none"
    return kwargs


def _is_retired(model: Optional[str]) -> bool:
    if not model:
        return True
    if model in RETIRED_CHAT_MODELS:
        return True
    return model.startswith(("gpt-3.5", "gpt-4-", "o1-", "o3-", "o4-"))
