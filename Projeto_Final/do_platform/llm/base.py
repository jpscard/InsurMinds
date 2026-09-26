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


class LLMTruncated(LLMError):
    """A resposta foi cortada pelo limite de tokens de saída (JSON incompleto)."""


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
        """Chama o modelo com novas tentativas e backoff exponencial.

        Só repete o que pode se resolver sozinho (instabilidade, sobrecarga, limite por minuto).
        Cota diária esgotada, chave inválida ou modelo inexistente param na hora, com mensagem clara."""
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return self._complete(system, user, json_output)
            except LLMError:
                raise  # erros de configuração não adiantam repetir
            except Exception as exc:  # noqa: BLE001 - SDKs lançam tipos variados
                status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
                texto = str(exc)
                if status in (400, 401, 403, 404):
                    # chave inválida, modelo inexistente, requisição malformada: repetir não resolve
                    raise LLMError(f"{self.name}: {_resumo(texto)}") from exc
                if status == 429 and _cota_esgotada(texto):
                    raise LLMError(f"{self.name}: a cota do provedor para o modelo {self.model} acabou (limite do "
                                   f"plano). Escolha outro modelo em Modelo de IA, tente mais tarde ou use uma "
                                   f"chave com faturamento.") from exc
                last_exc = exc
                wait = 2 ** attempt
                if status == 429:  # limite por minuto: espera o que o provedor pedir (até 30 s)
                    wait = min(max(wait, _espera_sugerida(texto)), 30)
                log.warning("Falha no %s (tentativa %s/%s): %s. Nova tentativa em %ss",
                            self.name, attempt, self.max_retries, _resumo(texto), wait)
                if attempt < self.max_retries:
                    time.sleep(wait)
        status = getattr(last_exc, "status_code", None) or getattr(last_exc, "code", None)
        if status in (503, 529) or "overloaded" in str(last_exc).lower() or "high demand" in str(last_exc).lower():
            raise LLMError(f"{self.name}: o modelo {self.model} está sobrecarregado no momento. Tente de novo em "
                           f"instantes ou escolha outro modelo.") from last_exc
        raise LLMError(f"{self.name}: falhou após {self.max_retries} tentativas: {_resumo(str(last_exc))}")

    def complete_json(self, system: str, user: str) -> dict:
        """Chama o modelo pedindo JSON e devolve o objeto já decodificado."""
        raw = self.complete(system, user, json_output=True)  # LLMTruncated sobe: corrigir não resolve
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


def _resumo(texto: str, limite: int = 220) -> str:
    """Mensagem de erro do SDK sem o JSON inteiro: só a parte legível."""
    m = re.search(r"'message': '([^']+)'", texto) or re.search(r'"message":\s*"([^"]+)"', texto)
    msg = (m.group(1) if m else texto).split("\n")[0].strip()
    return msg if len(msg) <= limite else msg[:limite] + "…"


def _cota_esgotada(texto: str) -> bool:
    """429 que não se resolve esperando alguns segundos: cota diária ou falta de créditos."""
    t = texto.lower()
    return any(k in t for k in ("perday", "per day", "insufficient_quota", "billing", "credit balance"))


def _espera_sugerida(texto: str) -> float:
    m = re.search(r"retry in ([\d.]+)s", texto) or re.search(r"retryDelay'?:\s*'(\d+)s", texto)
    return float(m.group(1)) if m else 0


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
