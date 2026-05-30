"""Shared OpenAI client wrapper.

Centralises model selection, response format, and temperature so that callers
only need to supply a system prompt and a user message.
"""

from __future__ import annotations

import json
import os

DEFAULT_MODEL = "gpt-5.4-nano"


class AIClient:
    """Thin wrapper around an OpenAI client with project-wide defaults."""

    def __init__(self, raw_client, *, model: str = DEFAULT_MODEL):
        self._client = raw_client
        self.model = model

    def get_json_response(self, system_prompt: str, user_message: str) -> dict:
        """Return the model's response parsed as a JSON dict.

        Raises on network errors or malformed JSON — callers decide how to
        handle failures.
        """
        response = self._client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0,
        )
        return json.loads(response.choices[0].message.content)


def get_ai_client(model: str = DEFAULT_MODEL) -> AIClient | None:
    """Return an ``AIClient``, or ``None`` if unavailable.

    Returns ``None`` silently when ``OPENAI_KEY`` is unset or the ``openai``
    package is not installed.
    """
    api_key = os.environ.get("OPENAI_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    return AIClient(OpenAI(api_key=api_key), model=model)
