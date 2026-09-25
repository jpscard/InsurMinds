"""Orquestrador: coordena os agentes nas etapas do fluxo.

    Recebimento -> Ingestão/OCR -> Triagem -> Extração -> Validação -> Armazenamento
                                                         ↓
                          Consulta (QA)  ←  Repositório  →  Comparação

A interface (Streamlit) e a linha de comando usam apenas esta classe.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field

from .agents import (ComparisonAgent, ExtractionAgent, QAAgent, Trace, TriageAgent,
                     ValidationAgent)
from .comparison import ComparisonResult, policy_label
from .config import Settings, get_settings
from .ingestion import load_document
from .llm import LLMProvider, get_provider
from .schema import ApoliceDO
from .storage import Repository

log = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    apolice_id: int
    arquivo: str
    apolice: ApoliceDO
    triagem: dict
    alertas: list[dict]
    trace: Trace
    reaproveitado: bool = False
    avisos: list[str] = field(default_factory=list)


class Pipeline:
    def __init__(self, llm: LLMProvider | None = None, settings: Settings | None = None,
                 repo: Repository | None = None):
        self.settings = settings or get_settings()
        self.llm = llm or get_provider(settings=self.settings)
        self.repo = repo or Repository(self.settings.database_path)

    def process(self, filename: str, data: bytes, force: bool = False) -> ProcessResult:
        """Executa o fluxo completo para um documento e o persiste."""
        trace = Trace()

        t0 = time.perf_counter()
        doc = load_document(filename, data, self.settings)
        trace.add("Ingestão", "Leitura do documento", t0,
                  f"{len(doc.pages)} pág. · {doc.ocr_pages} via OCR · {doc.char_count:,} caracteres")

        existing = self.repo.find_by_hash(doc.sha256)
        if existing and not force:
            row = self.repo.get_row(existing)
            return ProcessResult(existing, filename, self.repo.get(existing),
                                 json.loads(row["triagem_json"] or "{}"),
                                 json.loads(row["alertas_json"] or "[]"), trace, reaproveitado=True)

        triagem = TriageAgent(self.llm, trace).run(doc.text)
        avisos = []
        if not triagem.get("eh_do", True):
            avisos.append("A triagem indica que o documento pode não ser uma apólice D&O. "
                          "O processamento continuou, mas confira os resultados.")

        ap = ExtractionAgent(self.llm, trace, self.settings.chunk_chars).run(doc)
        ap, alertas = ValidationAgent(self.llm, trace).run(ap)

        t0 = time.perf_counter()
        aid = self.repo.save(filename, doc.sha256, ap,
                             [(p.number, p.method, p.text) for p in doc.pages],
                             triagem, alertas, self.llm.describe())
        trace.add("Armazenamento", "Gravação no SQLite", t0, f"id={aid}")
        return ProcessResult(aid, filename, ap, triagem, alertas, trace, avisos=avisos)

    def labels_for(self, ids: list[int]) -> dict[int, str]:
        labels: dict[int, str] = {}
        for aid in ids:
            row = self.repo.get_row(aid)
            lb = policy_label(self.repo.get(aid), row["arquivo"])
            while lb in labels.values():
                lb += f" #{aid}"
            labels[aid] = lb
        return labels

    def compare(self, ids: list[int]) -> tuple[ComparisonResult, dict, Trace]:
        trace = Trace()
        labels = self.labels_for(ids)
        apolices = {labels[i]: self.repo.get(i) for i in ids}
        res, analise = ComparisonAgent(self.llm, trace).run(apolices)
        self.repo.save_comparison(ids, analise, self.llm.describe())
        return res, analise, trace

    def ask(self, pergunta: str, ids: list[int]) -> tuple[dict, Trace]:
        trace = Trace()
        labels = self.labels_for(ids)
        estruturado = {labels[i]: self.repo.get(i).model_dump(exclude_none=True) for i in ids}
        paginas = [{"rotulo": labels[i], "pagina": p["numero"], "texto": p["texto"]}
                   for i in ids for p in self.repo.pages(i)]
        return QAAgent(self.llm, trace).run(pergunta, estruturado, paginas), trace
