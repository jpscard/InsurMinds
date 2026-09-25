"""Agente de Extração: transforma o texto da apólice em um `ApoliceDO` estruturado.

Documentos longos (condições gerais podem ter 60+ páginas) são divididos em
blocos por página; cada bloco é extraído separadamente e os resultados
parciais são consolidados (map-reduce).
"""
from __future__ import annotations

import time

from pydantic import ValidationError

from ..ingestion import DocumentText
from ..schema import ApoliceDO
from ..utils import norm_key
from .base import Agent
from .heuristics import extract_heuristic
from .prompts import EXTRACAO_CHUNK_CONTEXT, EXTRACAO_SYSTEM, EXTRACAO_USER


def chunk_pages(doc: DocumentText, max_chars: int) -> list[str]:
    """Agrupa páginas inteiras em blocos de até `max_chars` (não corta páginas ao meio)."""
    chunks, cur, size = [], [], 0
    for p in doc.pages:
        block = f"[Página {p.number}]\n{p.text}"
        if cur and size + len(block) > max_chars:
            chunks.append("\n\n".join(cur))
            cur, size = [], 0
        cur.append(block)
        size += len(block)
    if cur:
        chunks.append("\n\n".join(cur))
    return chunks


def merge_partials(parts: list[ApoliceDO]) -> ApoliceDO:
    """Consolida extrações parciais: 1º valor não nulo para escalares, união sem duplicatas para listas."""
    if not parts:
        return ApoliceDO()
    out = parts[0].model_copy(deep=True)
    for p in parts[1:]:
        for f in type(out.identificacao).model_fields:
            if getattr(out.identificacao, f) in (None, "") and getattr(p.identificacao, f):
                setattr(out.identificacao, f, getattr(p.identificacao, f))
        for f in ("limite_maximo_garantia", "premio_total", "base_cobertura", "data_retroatividade",
                  "prazo_complementar", "territorialidade", "custos_defesa", "observacoes"):
            if getattr(out, f) in (None, "") and getattr(p, f):
                setattr(out, f, getattr(p, f))
        out.coberturas += p.coberturas
        out.exclusoes += p.exclusoes
        out.franquias += p.franquias
        out.segurados += p.segurados
        out.clausulas_relevantes += p.clausulas_relevantes
    return dedupe(out)


def dedupe(ap: ApoliceDO) -> ApoliceDO:
    def uniq(items, key):
        seen, res = set(), []
        for it in items:
            k = norm_key(key(it))
            if k and k not in seen:
                seen.add(k)
                res.append(it)
        return res

    ap.coberturas = uniq(ap.coberturas, lambda c: c.nome)
    ap.exclusoes = uniq(ap.exclusoes, lambda e: e.titulo)
    ap.franquias = uniq(ap.franquias, lambda f: f.aplicacao)
    ap.segurados = uniq(ap.segurados, lambda s: s)
    ap.clausulas_relevantes = uniq(ap.clausulas_relevantes, lambda s: s[:80])
    return ap


class ExtractionAgent(Agent):
    nome = "Extração"

    def __init__(self, llm, trace=None, chunk_chars: int = 60000):
        super().__init__(llm, trace)
        self.chunk_chars = chunk_chars

    def _extract_chunk(self, text: str, arquivo: str, i: int, n: int) -> ApoliceDO:
        contexto = EXTRACAO_CHUNK_CONTEXT.format(i=i, n=n) if n > 1 else ""
        user = EXTRACAO_USER.format(schema=ApoliceDO.json_schema_str(), contexto=contexto,
                                    arquivo=arquivo, texto=text)
        data = self.llm.complete_json(EXTRACAO_SYSTEM, user)
        try:
            return ApoliceDO.model_validate(data)
        except ValidationError as exc:
            # Pede ao modelo para corrigir o JSON segundo os erros de validação.
            self.log.warning("JSON fora do esquema; solicitando correção")
            fix = self.llm.complete_json(
                EXTRACAO_SYSTEM,
                f"O JSON abaixo não segue o esquema. Erros:\n{exc}\n\nEsquema:\n"
                f"{ApoliceDO.json_schema_str()}\n\nJSON:\n{data}\n\nDevolva o JSON corrigido.",
            )
            return ApoliceDO.model_validate(fix)

    def run(self, doc: DocumentText) -> ApoliceDO:
        t0 = time.perf_counter()
        if self.llm.is_offline:
            ap = dedupe(extract_heuristic(doc.text))
            self.trace.add(self.nome, "Extração heurística (offline)", t0,
                           f"{len(ap.coberturas)} coberturas · {len(ap.exclusoes)} exclusões")
            return ap

        chunks = chunk_pages(doc, self.chunk_chars)
        parts = []
        for i, ch in enumerate(chunks, start=1):
            parts.append(self._extract_chunk(ch, doc.filename, i, len(chunks)))
        ap = merge_partials(parts)
        self.trace.add(self.nome, f"Extração via {self.llm.describe()}", t0,
                       f"{len(chunks)} bloco(s) · {len(ap.coberturas)} coberturas · {len(ap.exclusoes)} exclusões")
        return ap
