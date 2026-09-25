"""Agente de Consulta: responde perguntas em linguagem natural sobre as apólices armazenadas.

Recuperação híbrida: dados estruturados (JSON) + trechos das páginas originais
selecionados por sobreposição de palavras-chave (um RAG leve, sem embeddings,
suficiente para o volume de um MVP).
"""
from __future__ import annotations

import json
import math
import re
import time
from collections import Counter

from ..utils import norm_key
from .base import Agent
from .prompts import CONSULTA_SYSTEM, CONSULTA_USER


def _tokens(text: str) -> list[str]:
    return [t for t in norm_key(text).split() if len(t) > 2]


def rank_passages(question: str, passages: list[dict], k: int = 6) -> list[dict]:
    """Ranqueia trechos (dicts com 'texto') por BM25 simplificado."""
    q = set(_tokens(question))
    if not q or not passages:
        return []
    docs = [_tokens(p["texto"]) for p in passages]
    n = len(docs)
    avg = sum(map(len, docs)) / n or 1
    df = Counter(t for d in docs for t in set(d))
    scored = []
    for p, d in zip(passages, docs):
        tf = Counter(d)
        s = 0.0
        for t in q:
            if t in tf:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * tf[t] * 2.2 / (tf[t] + 1.2 * (0.25 + 0.75 * len(d) / avg))
        if s > 0:
            scored.append((s, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:k]]


def split_passages(pages: list[dict], size: int = 1200) -> list[dict]:
    """Divide páginas em parágrafos de ~size caracteres, mantendo a referência da página."""
    out = []
    for pg in pages:
        buf = ""
        for para in re.split(r"\n\s*\n|\n(?=\d+[\.\)])", pg["texto"]):
            if len(buf) + len(para) > size and buf:
                out.append({**pg, "texto": buf.strip()})
                buf = ""
            buf += para + "\n"
        if buf.strip():
            out.append({**pg, "texto": buf.strip()})
    return out


class QAAgent(Agent):
    nome = "Consulta"

    def run(self, pergunta: str, apolices: dict[str, dict], paginas: list[dict]) -> dict:
        """`apolices`: rótulo -> dados estruturados; `paginas`: [{rotulo, pagina, texto}]."""
        t0 = time.perf_counter()
        trechos = rank_passages(pergunta, split_passages(paginas))
        if self.llm.is_offline:
            resposta = ("Modo offline: sem LLM não é possível redigir uma resposta. "
                        "Abaixo estão os trechos mais relevantes encontrados.")
        else:
            tx = "\n\n".join(f"[{t['rotulo']} · pág. {t['pagina']}]\n{t['texto']}" for t in trechos) or "(nenhum)"
            user = CONSULTA_USER.format(apolices=json.dumps(apolices, ensure_ascii=False)[:60000],
                                        trechos=tx, pergunta=pergunta)
            resposta = self.llm.complete(CONSULTA_SYSTEM, user)
        self.trace.add(self.nome, "Resposta à pergunta", t0, f"{len(trechos)} trecho(s) recuperado(s)")
        return {"resposta": resposta, "trechos": trechos}
