"""Agente de Triagem: confirma se o documento é D&O e identifica seu tipo."""
from __future__ import annotations

import time

from .base import Agent
from .heuristics import triage_heuristic
from .prompts import TRIAGEM_SYSTEM

# A triagem só precisa do início do documento: cabeçalho e objeto do seguro.
_TRIAGE_CHARS = 6000


class TriageAgent(Agent):
    nome = "Triagem"

    def run(self, text: str) -> dict:
        t0 = time.perf_counter()
        if self.llm.is_offline:
            result = triage_heuristic(text)
        else:
            try:
                result = self.llm.complete_json(TRIAGEM_SYSTEM, text[:_TRIAGE_CHARS])
            except Exception as exc:  # noqa: BLE001 - triagem não deve bloquear o fluxo
                self.log.warning("Triagem via LLM falhou (%s); usando heurística", exc)
                result = triage_heuristic(text)
                result["justificativa"] += " (fallback após erro no LLM)"
        self.trace.add(self.nome, "Classificação do documento", t0,
                       f"D&O={result.get('eh_do')} · tipo={result.get('tipo_documento')}")
        return result
