"""Interface comum para provedores de LLM.

Os agentes dependem apenas de `LLMProvider`, nunca de um SDK específico.
Trocar de provedor é uma mudança de configuração (`LLM_PROVIDER` no .env).
"""
from __future__ import annotations

import json
import logging
import re
import time
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Falha ao chamar o modelo (credencial ausente, rede, cota, resposta inválida)."""


class LLMProvider(ABC):
    name: str = "base"
    default_model: str = ""

    def __init__(self, model: str | None, temperature: float, max_tokens: int,
                 timeout_s: int, max_retries: int):
        self.model = model or self.default_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s
        self.max_retries = max_retries

    @property
    def is_offline(self) -> bool:
        return False

    def list_models(self) -> list[tuple[str, str]]:
        """Modelos de texto disponíveis para a chave em uso, como pares (id, nome de exibição)."""
        return []

    def _list_error(self, exc: Exception) -> LLMError:
        status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
        if status in (401, 403):
            return LLMError(f"{self.name}: chave de API inválida ou sem permissão.")
        return LLMError(f"{self.name}: não foi possível listar os modelos: {exc}")

    @abstractmethod
    def _complete(self, system: str, user: str, json_output: bool) -> str:
        """Chamada crua ao provedor. Implementada por cada subclasse."""

    def complete(self, system: str, user: str, json_output: bool = False) -> str:
        """Chama o modelo com novas tentativas e backoff exponencial."""
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return self._complete(system, user, json_output)
            except LLMError:
                raise  # erros de configuração não adiantam repetir
            except Exception as exc:  # noqa: BLE001 - SDKs lançam tipos variados
                status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
                if status in (400, 401, 403, 404):
                    # chave inválida, modelo inexistente, requisição malformada: repetir não resolve
                    raise LLMError(f"{self.name}: {exc}") from exc
                last_exc = exc
                wait = 2 ** attempt
                log.warning("Falha no %s (tentativa %s/%s): %s. Nova tentativa em %ss",
                            self.name, attempt, self.max_retries, exc, wait)
                if attempt < self.max_retries:
                    time.sleep(wait)
        raise LLMError(f"{self.name}: falhou após {self.max_retries} tentativas: {last_exc}")

    def complete_json(self, system: str, user: str) -> dict:
        """Chama o modelo pedindo JSON e devolve o objeto já decodificado."""
        raw = self.complete(system, user, json_output=True)
        try:
            return parse_json(raw)
        except ValueError:
            # Uma segunda chance: pede ao modelo que corrija o próprio JSON.
            fix = self.complete(
                "Você corrige JSON inválido. Responda apenas com o JSON corrigido.",
                raw, json_output=True,
            )
            return parse_json(fix)

    def describe(self) -> str:
        return f"{self.name} ({self.model})"


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_json(text: str) -> dict:
    """Extrai o primeiro objeto JSON de uma resposta (tolera cercas ``` e texto ao redor)."""
    cleaned = _FENCE.sub("", text.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("Resposta do modelo não contém JSON")
    try:
        return json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido na resposta do modelo: {exc}") from exc
