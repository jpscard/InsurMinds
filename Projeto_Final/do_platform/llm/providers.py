"""Implementações concretas dos provedores de LLM.

Os SDKs são importados sob demanda: só é preciso instalar o do provedor em uso.
"""
from __future__ import annotations

from .base import LLMError, LLMProvider


class AnthropicProvider(LLMProvider):
    name = "anthropic"
    default_model = "claude-sonnet-5"

    def __init__(self, api_key: str | None, **kw):
        super().__init__(**kw)
        if not api_key:
            raise LLMError("ANTHROPIC_API_KEY não definida no .env")
        try:
            import anthropic
        except ImportError as exc:
            raise LLMError("Instale o SDK: pip install anthropic") from exc
        self._client = anthropic.Anthropic(api_key=api_key, timeout=self.timeout_s, max_retries=0)

    def list_models(self) -> list[tuple[str, str]]:
        try:
            # A API devolve os modelos do mais recente para o mais antigo
            return [(m.id, m.display_name or m.id) for m in self._client.models.list(limit=100)]
        except Exception as exc:  # noqa: BLE001
            raise self._list_error(exc) from exc

    def _complete(self, system: str, user: str, json_output: bool) -> str:
        if json_output:
            system += "\n\nResponda SOMENTE com um objeto JSON válido, sem texto antes ou depois."
        with self._client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            # Os modelos Claude atuais não aceitam parâmetros de amostragem (temperature);
            # a estabilidade vem do prompt e da validação do esquema.
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            msg = stream.get_final_message()
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


class OpenAIProvider(LLMProvider):
    name = "openai"
    default_model = "gpt-4.1-mini"

    # O endpoint de modelos lista tudo (áudio, imagem, embeddings...); só interessam os de chat.
    _CHAT_PREFIXES = ("gpt-", "o1", "o3", "o4", "chatgpt-")
    _NON_CHAT = ("audio", "realtime", "tts", "transcribe", "image", "search", "embedding",
                 "instruct", "moderation", "codex", "computer-use")
    # Modelos de raciocínio só aceitam a temperatura padrão
    _NO_TEMPERATURE = ("o1", "o3", "o4", "gpt-5")

    def __init__(self, api_key: str | None, **kw):
        super().__init__(**kw)
        if not api_key:
            raise LLMError("OPENAI_API_KEY não definida no .env")
        try:
            import openai
        except ImportError as exc:
            raise LLMError("Instale o SDK: pip install openai") from exc
        self._client = openai.OpenAI(api_key=api_key, timeout=self.timeout_s, max_retries=0)

    def list_models(self) -> list[tuple[str, str]]:
        try:
            models = list(self._client.models.list())
        except Exception as exc:  # noqa: BLE001
            raise self._list_error(exc) from exc
        chat = [m for m in models if m.id.startswith(self._CHAT_PREFIXES)
                and not any(x in m.id for x in self._NON_CHAT)]
        chat.sort(key=lambda m: m.created, reverse=True)
        return [(m.id, m.id) for m in chat]

    def _complete(self, system: str, user: str, json_output: bool) -> str:
        kwargs = {}
        if json_output:
            kwargs["response_format"] = {"type": "json_object"}
            system += "\n\nResponda em JSON."
        if not self.model.startswith(self._NO_TEMPERATURE):
            kwargs["temperature"] = self.temperature
        resp = self._client.chat.completions.create(
            model=self.model,
            max_completion_tokens=self.max_tokens,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            **kwargs,
        )
        return resp.choices[0].message.content or ""


class GeminiProvider(LLMProvider):
    name = "gemini"
    default_model = "gemini-2.5-flash"

    def __init__(self, api_key: str | None, **kw):
        super().__init__(**kw)
        if not api_key:
            raise LLMError("GEMINI_API_KEY não definida no .env")
        try:
            from google import genai
        except ImportError as exc:
            raise LLMError("Instale o SDK: pip install google-genai") from exc
        self._client = genai.Client(api_key=api_key)

    _NON_TEXT = ("embedding", "image", "tts", "live", "audio", "aqa", "computer-use", "customtools",
                 "robotics")

    def list_models(self) -> list[tuple[str, str]]:
        try:
            models = list(self._client.models.list())
        except Exception as exc:  # noqa: BLE001
            raise self._list_error(exc) from exc
        out = []
        for m in models:
            mid = (m.name or "").removeprefix("models/")
            if ("generateContent" in (m.supported_actions or []) and mid.startswith("gemini")
                    and not any(x in mid for x in self._NON_TEXT)):
                out.append((mid, m.display_name or mid))
        return out

    def _complete(self, system: str, user: str, json_output: bool) -> str:
        from google.genai import types

        cfg = types.GenerateContentConfig(
            system_instruction=system,
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
            response_mime_type="application/json" if json_output else "text/plain",
        )
        resp = self._client.models.generate_content(model=self.model, contents=user, config=cfg)
        return resp.text or ""


class OfflineProvider(LLMProvider):
    """Modo sem LLM: os agentes usam regras heurísticas.

    Serve para demonstrar a interface e rodar testes sem chave de API.
    Não é o modo de uso pretendido: a qualidade de extração é bem inferior.
    """

    name = "offline"
    default_model = "heurístico"

    @property
    def is_offline(self) -> bool:
        return True

    def _complete(self, system: str, user: str, json_output: bool) -> str:
        raise LLMError("Provedor offline não gera texto; os agentes devem usar o caminho heurístico.")
