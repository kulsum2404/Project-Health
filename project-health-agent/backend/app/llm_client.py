"""
Provider-agnostic LLM client wrapping Google's Gemini API.

Designed so the underlying model/provider can be swapped by changing the
implementation here without touching any calling code.
"""

from __future__ import annotations

import logging
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Thin wrapper over the Google GenAI SDK for structured LLM interactions."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.gemini_api_key
        self._model = model or settings.llm_model
        self._max_tokens = settings.llm_max_tokens
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            if not self._api_key:
                raise ValueError(
                    "GEMINI_API_KEY is not set. "
                    "Please set it in your .env file or pass it explicitly."
                )
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.3,
    ) -> str:
        """
        Send a prompt to the LLM and return the text response.

        Args:
            system_prompt: System-level instruction for the model.
            user_prompt: The user message / main content.
            model: Override the default model.
            max_tokens: Override the default max tokens.
            temperature: Sampling temperature (lower = more deterministic).

        Returns:
            The model's text response.
        """
        resolved_model = model or self._model
        resolved_max = max_tokens or self._max_tokens

        logger.info(
            "LLM request: model=%s, max_tokens=%d, temp=%.2f",
            resolved_model,
            resolved_max,
            temperature,
        )
        logger.debug("System prompt: %s", system_prompt[:200])
        logger.debug("User prompt: %s", user_prompt[:200])

        try:
            # We use synchronous call for generate_content inside an async function.
            # Ideally in a production async app we could use client.aio.models.generate_content if available,
            # or wrap this in asyncio.to_thread if it's blocking.
            response = self.client.models.generate_content(
                model=resolved_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    max_output_tokens=resolved_max,
                )
            )

            response_text = response.text or ""
            logger.info("LLM response: %d chars", len(response_text))
            return response_text

        except Exception as e:
            logger.error("LLM request failed: %s", e)
            raise

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """
        Send a prompt expecting a JSON response. Parses and returns a dict.

        The system prompt should instruct the model to respond with valid JSON.
        """
        import json

        resolved_model = model or self._model
        resolved_max = max_tokens or self._max_tokens

        try:
            response = self.client.models.generate_content(
                model=resolved_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    max_output_tokens=resolved_max,
                    response_mime_type="application/json",
                )
            )
            
            response_text = response.text or ""
            
            # Strip markdown code fences if present (some models still inject them even with application/json)
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned = "\n".join(lines)

            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM JSON response: %s", e)
            logger.debug("Raw response: %s", response_text)
            raise ValueError(f"LLM returned invalid JSON: {e}") from e
        except Exception as e:
            logger.error("LLM json request failed: %s", e)
            raise


# ── Module-level singleton ────────────────────────────────────────────────

_default_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Return a module-level singleton LLM client."""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
