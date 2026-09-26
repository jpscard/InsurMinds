"""Agente de Indexação: monta o índice hierárquico (abordagem PageIndex) de cada apólice.

A estrutura vem do layout (sem LLM). O LLM só escreve os resumos das seções de primeiro nível e
das seções longas, que são o que o Navegador lê para decidir onde procurar. Sem LLM, os resumos
são o início do texto de cada seção.
"""
from __future__ import annotations

import time

from ..indexing import build_tree, flatten, subtree_text
from ..llm import LLMError
from .base import Agent
from .prompts import INDICE_SYSTEM, INDICE_USER

MAX_SECTION_CHARS = 1500   # contexto de cada seção enviado para o resumo
MAX_BATCH_CHARS = 40000    # seções por chamada


class IndexAgent(Agent):
    nome = "Indexação"

    def run(self, pages: list[tuple[int, str]], resumos_llm: bool = True) -> dict:
        t0 = time.perf_counter()
        tree = build_tree(pages)
        nodes = flatten(tree["nos"])
        alvo = [n for n in nodes if n["nivel"] == 1 or len(n["texto"]) > 600]
        if self.llm.is_offline or not alvo or not resumos_llm:
            self.trace.add(self.nome, "Índice por estrutura", t0, f"{len(nodes)} seções · método {tree['metodo']}")
            return tree

        resumidos = 0
        for batch in _batches(alvo):
            secoes = "\n\n".join(f"[{n['id']}] {n['titulo']}\n{subtree_text(n, MAX_SECTION_CHARS)}" for n in batch)
            try:
                out = self.llm.complete_json(INDICE_SYSTEM, INDICE_USER.format(secoes=secoes))
            except (LLMError, ValueError) as exc:
                self.log.warning("Resumos por LLM falharam, mantendo os heurísticos: %s", exc)
                continue
            resumos = out.get("resumos", {}) if isinstance(out, dict) else {}
            for n in batch:
                r = resumos.get(n["id"])
                if isinstance(r, str) and r.strip():
                    n["resumo"] = r.strip()
                    resumidos += 1
        if resumidos:
            tree["metodo"] += "+llm"
        self.trace.add(self.nome, "Índice hierárquico", t0,
                       f"{len(nodes)} seções · {resumidos} resumo(s) pelo LLM")
        return tree


def _batches(nodes: list[dict]):
    batch, size = [], 0
    for n in nodes:
        cost = min(len(subtree_text(n, MAX_SECTION_CHARS)), MAX_SECTION_CHARS) + 100
        if batch and size + cost > MAX_BATCH_CHARS:
            yield batch
            batch, size = [], 0
        batch.append(n)
        size += cost
    if batch:
        yield batch
