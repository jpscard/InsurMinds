from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable

from ..llm import LLMProvider


@dataclass
class TraceStep:
    agente: str
    acao: str
    duracao_s: float
    detalhe: str = ""


@dataclass
class Trace:
    """Registro das etapas executadas, exibido na interface para transparência."""

    steps: list[TraceStep] = field(default_factory=list)
    # Chamado a cada etapa concluída: permite mostrar o progresso ao vivo na interface.
    listener: Callable[[TraceStep], None] | None = field(default=None, repr=False, compare=False)

    def add(self, agente: str, acao: str, inicio: float, detalhe: str = "") -> None:
        step = TraceStep(agente, acao, round(time.perf_counter() - inicio, 2), detalhe)
        self.steps.append(step)
        if self.listener:
            self.listener(step)


class Agent:
    """Agente especializado: uma responsabilidade, um prompt, um provedor de LLM."""

    nome = "Agente"

    def __init__(self, llm: LLMProvider, trace: Trace | None = None):
        self.llm = llm
        self.trace = trace or Trace()
        self.log = logging.getLogger(f"agente.{self.nome}")
