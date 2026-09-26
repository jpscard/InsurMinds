"""Fábrica de provedores de LLM."""
from __future__ import annotations

from ..config import Settings, get_settings
from .base import LLMError, LLMProvider, LLMTruncated, parse_json
from .providers import AnthropicProvider, GeminiProvider, OfflineProvider, OpenAIProvider

PROVIDERS = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "offline": OfflineProvider,
}


def get_provider(name: str | None = None, model: str | None = None,
                 settings: Settings | None = None) -> LLMProvider:
    s = settings or get_settings()
    name = (name or s.llm_provider).lower().strip()
    if name not in PROVIDERS:
        raise LLMError(f"Provedor desconhecido: {name}. Opções: {', '.join(PROVIDERS)}")
    common = dict(model=model or s.llm_model, temperature=s.llm_temperature,
                  max_tokens=s.llm_max_tokens, timeout_s=s.llm_timeout_s,
                  max_retries=s.llm_max_retries)
    if name == "offline":
        return OfflineProvider(**common)
    key = {"anthropic": s.anthropic_api_key, "openai": s.openai_api_key,
           "gemini": s.gemini_api_key}[name]
    return PROVIDERS[name](api_key=key, **common)


__all__ = ["LLMError", "LLMProvider", "LLMTruncated", "get_provider", "parse_json", "PROVIDERS"]
