"""
Provider-agnostic LLM client wrapping OpenAI / Groq API.

Designed so the underlying model/provider can be swapped by changing the
implementation here without touching any calling code.
"""

from __future__ import annotations

import logging
import json
from typing import Any

from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Thin wrapper over the OpenAI API for structured LLM interactions."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.groq_api_key or settings.gemini_api_key
        self._model = model or settings.llm_model
        self._max_tokens = settings.llm_max_tokens
        self._client: AsyncOpenAI | None = None

        # Determine base URL based on whether it's a Groq key
        self._base_url = "https://api.groq.com/openai/v1" if self._api_key and self._api_key.startswith("gsk_") else None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            if not self._api_key:
                raise ValueError(
                    "API KEY is not set. "
                    "Please set GROQ_API_KEY or GEMINI_API_KEY in your .env file."
                )
            self._client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
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
            response = await self.client.chat.completions.create(
                model=resolved_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=resolved_max,
            )

            response_text = response.choices[0].message.content or ""
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
        """
        resolved_model = model or self._model
        resolved_max = max_tokens or self._max_tokens

        try:
            # Note: Groq supports response_format={"type": "json_object"} 
            # for select models, but it's often safer to rely on prompting for newer models.
            # We'll use json_object for compatibility.
            
            # Ensure "JSON" is mentioned in the system prompt as required by OpenAI API spec for json_object
            if "json" not in system_prompt.lower():
                system_prompt += "\n\nYou must respond with valid JSON."
                
            response = await self.client.chat.completions.create(
                model=resolved_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=resolved_max,
                response_format={"type": "json_object"},
            )
            
            response_text = response.choices[0].message.content or ""
            
            # Strip markdown code fences if present
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
