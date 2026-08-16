"""Mistral API wrapper used only for explanations."""

from __future__ import annotations

import logging

from src.config import settings
from src.llm.prompt_builder import SafetyPromptBuilder
from src.llm.response_parser import LLMResponseParser, fallback_response

logger = logging.getLogger(__name__)


class MistralSafetyClient:
    def __init__(self) -> None:
        self.prompt_builder = SafetyPromptBuilder()
        self.parser = LLMResponseParser()

    def explain(self, analysis: dict, language: str = "en") -> dict:
        if not settings.MISTRAL_API_KEY:
            return fallback_response(analysis, language=language)
        try:
            try:
                from mistralai import Mistral
                client = Mistral(api_key=settings.MISTRAL_API_KEY)
                prompt = self.prompt_builder.build(analysis, language=language)
                response = client.chat.complete(
                    model=settings.MISTRAL_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=settings.MISTRAL_TEMPERATURE,
                    max_tokens=settings.MISTRAL_MAX_TOKENS,
                )
                return self.parser.parse(response.choices[0].message.content, analysis, language=language)
            except ImportError:
                from mistralai.client import MistralClient
                from mistralai.models.chat_completion import ChatMessage

                client = MistralClient(api_key=settings.MISTRAL_API_KEY)
                prompt = self.prompt_builder.build(analysis, language=language)
                response = client.chat(
                    model=settings.MISTRAL_MODEL,
                    messages=[ChatMessage(role="user", content=prompt)],
                    temperature=settings.MISTRAL_TEMPERATURE,
                    max_tokens=settings.MISTRAL_MAX_TOKENS,
                )
                return self.parser.parse(response.choices[0].message.content, analysis, language=language)
        except Exception as exc:
            logger.warning("Mistral explanation failed, using fallback: %s", exc)
            return fallback_response(analysis, language=language)
