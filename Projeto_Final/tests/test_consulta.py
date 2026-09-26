"""Índice hierárquico (PageIndex) e grafo de consulta (LangGraph), com LLM simulado."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from do_platform.agents import IndexAgent, QAAgent  # noqa: E402
from do_platform.agents.qa import consulta_mermaid  # noqa: E402
from do_platform.config import Settings  # noqa: E402
from do_platform.indexing import build_tree, find, flatten, outline, subtree_text  # noqa: E402
from do_platform.ingestion import load_document  # noqa: E402
from do_platform.llm import get_provider  # noqa: E402
from do_platform.llm.base import LLMProvider  # noqa: E402
from do_platform.pipeline import Pipeline  # noqa: E402

SAMPLES = ROOT / "samples"


class ScriptedLLM(LLMProvider):
    name = "roteiro"

    def __init__(self, respostas):
        super().__init__(model="roteiro-1", temperature=0, max_tokens=100, timeout_s=1, max_retries=1)
        self.respostas = list(respostas)
        self.chamadas: list[tuple[str, str]] = []

    def _complete(self, system, user, json_output):
        self.chamadas.append((system, user))
        r = self.respostas.pop(0)
        return r if isinstance(r, str) else json.dumps(r)


def _pages(name):
    doc = load_document(name, (SAMPLES / name).read_bytes(), Settings())
    return [(p.number, p.text) for p in doc.pages]


@pytest.fixture(scope="module")
def arvores():
    return {"Aurora": build_tree(_pages("apolice_aurora_do.pdf")),
            "Boreal": build_tree(_pages("apolice_boreal_do.pdf"))}


def _titulo(tree, titulo):
    return next(n for n in flatten(tree["nos"]) if n["titulo"] == titulo)


# ─── Índice ─────────────────────────────────────────────────────────────────
def test_indice_detecta_secoes_e_itens(arvores):
    t = arvores["Boreal"]
    assert t["metodo"] == "estrutura"
    exc = _titulo(t, "EXCLUSÕES")
    itens = [f["titulo"] for f in exc["filhos"]]
    assert "6. Segurado contra Segurado" in itens and len(itens) == 8
    assert exc["pagina_inicio"] == 1 and exc["pagina_fim"] == 2
    # rótulo com valor não vira título de seção
    assert not any(n["titulo"].startswith("CNPJ") for n in flatten(t["nos"]))
    # abrir a seção traz o texto das subseções
    assert "Oferta pública" in subtree_text(exc)


def test_indice_numeracao_hierarquica_e_fallback_por_pagina():
    t = build_tree([(1, "CLÁUSULA 5 – EXCLUSÕES\n5.1 Dolo: não cobre.\n5.2 Poluição: não cobre.\n5.2.1 Exceção: custos de defesa.")])
    sec = t["nos"][0]
    assert sec["titulo"].startswith("CLÁUSULA 5")
    filho = sec["filhos"][1]
    assert filho["titulo"] == "5.2. Poluição" and filho["filhos"][0]["titulo"] == "5.2.1. Exceção"
    plano = build_tree([(1, "texto corrido sem títulos"), (2, "mais texto")])
    assert plano["metodo"] == "paginas" and [n["titulo"] for n in plano["nos"]] == ["Página 1", "Página 2"]


def test_indexador_usa_llm_so_para_resumos(arvores):
    llm = ScriptedLLM([{"resumos": {"0010": "Oito exclusões, incluindo Segurado contra Segurado."}}])
    t = IndexAgent(llm).run(_pages("apolice_boreal_do.pdf"))
    assert t["metodo"] == "estrutura+llm"
    assert find(t, "0010")["resumo"].startswith("Oito exclusões")
    assert len(llm.chamadas) == 1
    offline = IndexAgent(get_provider("offline")).run(_pages("apolice_boreal_do.pdf"))
    assert offline["metodo"] == "estrutura" and find(offline, "0016")["resumo"]


def test_indexador_mantem_resumos_heuristicos_se_llm_falhar():
    t = IndexAgent(ScriptedLLM(["isto não é json", "nem isto"])).run(_pages("apolice_boreal_do.pdf"))
    assert t["metodo"] == "estrutura" and all("resumo" in n for n in flatten(t["nos"]))


# ─── Grafo de consulta ──────────────────────────────────────────────────────
def _run(llm, arvores, pergunta="A exclusão de Segurado contra Segurado existe nas duas?"):
    estruturado = {lb: {"identificacao": {"seguradora": lb}} for lb in arvores}
    return QAAgent(llm).run(pergunta, estruturado, [], arvores)


def test_grafo_navega_indice_e_faz_segunda_rodada(arvores):
    exc_a = _titulo(arvores["Aurora"], "EXCLUSÕES")["id"]
    exc_b = _titulo(arvores["Boreal"], "EXCLUSÕES")["id"]
    llm = ScriptedLLM([
        {"rota": "documento", "motivo": "precisa da redação"},
        {"secoes": [{"apolice": "A1", "id": exc_a, "motivo": "exclusões da Aurora"},
                    {"apolice": "A2", "id": "9999", "motivo": "id inexistente é ignorado"}]},
        {"suficiente": False, "falta": "exclusões da Boreal"},
        {"secoes": [{"apolice": "A2", "id": exc_b, "motivo": "exclusões da Boreal"},
                    {"apolice": "A1", "id": exc_a, "motivo": "repetida é ignorada"}]},
        "Só a Boreal exclui Segurado contra Segurado (Boreal · EXCLUSÕES · pág. 2).",
    ])
    out = _run(llm, arvores)
    assert out["rota"] == "documento"
    assert [t["rotulo"] for t in out["trechos"]] == ["Aurora", "Boreal"]
    assert out["trechos"][1]["secao"] == "EXCLUSÕES" and "Segurado contra Segurado" in out["trechos"][1]["texto"]
    etapas = [c["etapa"] for c in out["caminho"]]
    assert etapas == ["Roteador", "Navegador", "Leitor", "Avaliador", "Navegador", "Leitor", "Avaliador", "Respondedor"]
    assert out["resposta"].startswith("Só a Boreal")
    # o navegador recebe o sumário, não o texto inteiro; o respondedor recebe as seções
    assert "[" + exc_b + "] EXCLUSÕES" in llm.chamadas[1][1]
    assert "arbitral definitiva" not in llm.chamadas[1][1]
    assert "arbitral definitiva" in llm.chamadas[-1][1]
    assert not llm.respostas


def test_grafo_rota_estruturada_nao_le_documento(arvores):
    llm = ScriptedLLM([{"rota": "estruturado", "motivo": "LMG está nos dados"}, "A Aurora tem o maior LMG."])
    out = _run(llm, arvores, "Qual tem o maior LMG?")
    assert out["rota"] == "estruturado" and out["trechos"] == []
    assert [c["etapa"] for c in out["caminho"]] == ["Roteador", "Respondedor"]


def test_grafo_cai_na_busca_por_palavras_se_navegacao_falhar(arvores):
    llm = ScriptedLLM([{"rota": "documento"}, "json quebrado", "de novo quebrado", "Resposta pelo BM25."])
    out = _run(llm, arvores, "Segurado contra Segurado")
    assert "Busca por palavras" in [c["etapa"] for c in out["caminho"]]
    assert any("Segurado contra Segurado" in t["texto"] for t in out["trechos"])
    assert out["resposta"] == "Resposta pelo BM25."


def test_grafo_offline_usa_bm25_nas_secoes(arvores):
    out = _run(get_provider("offline"), arvores, "Segurado contra Segurado")
    assert out["rota"] == "lexical"
    top = out["trechos"][0]
    assert top["rotulo"] == "Boreal" and top["secao"] == "6. Segurado contra Segurado"


def test_diagrama_do_grafo():
    mm = consulta_mermaid()
    for no in ("roteador", "navegador", "leitor", "avaliador", "busca_lexical", "respondedor"):
        assert no in mm


# ─── Pipeline: indexação, revisão humana e apólices antigas ─────────────────
def test_pipeline_indexa_preserva_na_revisao_e_gera_para_antigas(tmp_path):
    s = Settings(llm_provider="offline", database_path=tmp_path / "q.db", uploads_dir=tmp_path)
    pipe = Pipeline(settings=s)
    r = pipe.process("apolice_boreal_do.pdf", (SAMPLES / "apolice_boreal_do.pdf").read_bytes())
    assert pipe.repo.get_index(r.apolice_id)["metodo"] == "estrutura"
    assert "Indexação" in [st.agente for st in r.trace.steps]

    novo = pipe.repo.update_data(r.apolice_id, r.apolice)
    assert novo != r.apolice_id and pipe.repo.get_index(novo) is not None

    with pipe.repo._conn() as c:  # simula apólice processada antes da indexação existir
        c.execute("DELETE FROM indices")
    out, _ = pipe.ask("Segurado contra Segurado", [novo])
    assert pipe.repo.get_index(novo) is not None
    assert out["trechos"][0]["secao"] == "6. Segurado contra Segurado"
    assert "EXCLUSÕES" in outline(pipe.repo.get_index(novo))
