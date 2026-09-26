"""Testes automatizados. Não exigem chave de API: usam o modo offline e um LLM simulado.

Execute:  pytest -q
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from do_platform.agents import ComparisonAgent, ExtractionAgent, ValidationAgent  # noqa: E402
from do_platform.agents.extraction import chunk_pages, merge_partials  # noqa: E402
from do_platform.config import Settings  # noqa: E402
from do_platform.ingestion import DocumentText, IngestionError, PageText, load_document  # noqa: E402
from do_platform.llm import get_provider, parse_json  # noqa: E402
from do_platform.llm.base import LLMProvider  # noqa: E402
from do_platform.pipeline import Pipeline  # noqa: E402
from do_platform.schema import ApoliceDO, Cobertura, Exclusao, Identificacao, Valor  # noqa: E402
from do_platform.utils import normalize_date, parse_money, similarity  # noqa: E402

SAMPLES = ROOT / "samples"


@pytest.fixture(scope="session", autouse=True)
def amostras():
    if not (SAMPLES / "apolice_aurora_do.pdf").exists():
        subprocess.run([sys.executable, str(ROOT / "scripts" / "gerar_amostras.py")], check=True)


@pytest.fixture
def settings(tmp_path):
    return Settings(llm_provider="offline", database_path=tmp_path / "t.db", uploads_dir=tmp_path)


@pytest.fixture
def pipe(settings):
    return Pipeline(llm=get_provider("offline", settings=settings), settings=settings)


# ----------------------------------------------------------------- utilidades
@pytest.mark.parametrize("txt,esperado", [
    ("R$ 10.000.000,00", (10_000_000.0, "BRL")),
    ("US$ 5 milhões", (5_000_000.0, "USD")),
    ("franquia de R$ 250 mil", (250_000.0, "BRL")),
    ("R$ 1.500,50 por reclamação", (1500.5, "BRL")),
    ("sem valor", (None, None)),
])
def test_parse_money(txt, esperado):
    assert parse_money(txt) == esperado


def test_normalize_date():
    assert normalize_date("01/03/2026") == "2026-03-01"
    assert normalize_date("das 24h de 01/03/2026") == "2026-03-01"
    assert normalize_date("Ilimitada") == "Ilimitada"


def test_similarity():
    assert similarity("Custos de Defesa", "Custos com a Defesa") > 0.5
    assert similarity("Lado A", "Poluição ambiental") == 0


def test_parse_json_tolerante():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('Claro! Aqui está: {"a": [1, 2]} Espero ter ajudado.') == {"a": [1, 2]}
    with pytest.raises(ValueError):
        parse_json("sem json aqui")


# ----------------------------------------------------------------- ingestão
def test_ingestao_pdf_digital(settings):
    doc = load_document("a.pdf", (SAMPLES / "apolice_aurora_do.pdf").read_bytes(), settings)
    assert doc.ocr_pages == 0
    assert "Limite Máximo de Garantia" in doc.text


def test_ingestao_pdf_digitalizado_usa_ocr(settings):
    doc = load_document("c.pdf", (SAMPLES / "apolice_cruzeiro_digitalizada.pdf").read_bytes(), settings)
    assert doc.ocr_pages == len(doc.pages) > 0
    assert "25.000.000" in doc.text


def test_ingestao_imagem(settings):
    doc = load_document("p.png", (SAMPLES / "imagem" / "apolice_cruzeiro_pagina1.png").read_bytes(), settings)
    assert "Cruzeiro" in doc.text


def test_ingestao_formato_invalido(settings):
    with pytest.raises(IngestionError):
        load_document("x.docx", b"abc", settings)
    with pytest.raises(IngestionError):
        load_document("x.pdf", b"isto nao e um pdf", settings)


# ----------------------------------------------------------------- fluxo offline
def test_fluxo_completo_offline(pipe):
    ids = []
    for f in ["apolice_aurora_do.pdf", "apolice_boreal_do.pdf", "apolice_cruzeiro_digitalizada.pdf"]:
        r = pipe.process(f, (SAMPLES / f).read_bytes())
        ids.append(r.apolice_id)
        assert r.apolice.limite_maximo_garantia.valor > 0
        assert r.triagem["eh_do"] is True
    aurora = pipe.repo.get(ids[0])
    assert aurora.identificacao.numero_apolice == "1010.0045871"
    assert len(aurora.coberturas) == 9 and len(aurora.exclusoes) == 5

    # reprocessar o mesmo arquivo reaproveita o registro
    again = pipe.process("apolice_aurora_do.pdf", (SAMPLES / "apolice_aurora_do.pdf").read_bytes())
    assert again.reaproveitado and again.apolice_id == ids[0]

    res, analise, _ = pipe.compare(ids[:2])
    lados_c = [c for c in res.coberturas if c["Categoria"] == "Lado C"]
    assert lados_c and lados_c[0]["Situação"].startswith("Ausente")  # Boreal não tem Lado C
    assert any("Segurado contra Segurado" in d for d in res.diferencas)
    assert analise["resumo_executivo"]

    out, _ = pipe.ask("franquia reclamações trabalhistas", ids)
    assert out["trechos"]

    rows = pipe.repo.query("SELECT COUNT(*) AS n FROM coberturas WHERE categoria = 'Lado A'")
    assert rows[0]["n"] == 3
    with pytest.raises(ValueError):
        pipe.repo.query("DELETE FROM apolices")


# ----------------------------------------------------------------- caminho com LLM (simulado)
class FakeLLM(LLMProvider):
    """Simula um LLM: devolve respostas predefinidas e registra as chamadas."""

    name = "fake"

    def __init__(self, respostas):
        super().__init__(model="fake-1", temperature=0, max_tokens=100, timeout_s=1, max_retries=1)
        self.respostas = list(respostas)
        self.chamadas = []

    def _complete(self, system, user, json_output):
        self.chamadas.append(user)
        return self.respostas.pop(0)


def _doc(n_pages=3, size=500):
    return DocumentText("x.pdf", "h", [PageText(i, "x" * size, "texto") for i in range(1, n_pages + 1)])


def test_chunking_por_pagina():
    assert len(chunk_pages(_doc(3, 500), 1200)) == 2
    assert len(chunk_pages(_doc(3, 500), 10_000)) == 1


def test_extracao_llm_em_blocos_e_consolidacao():
    p1 = {"identificacao": {"seguradora": "X"}, "coberturas": [{"nome": "Custos de Defesa"}]}
    p2 = {"identificacao": {"numero_apolice": "9"}, "limite_maximo_garantia": {"texto": "R$ 1.000.000,00"},
          "coberturas": [{"nome": "Custos de defesa"}, {"nome": "Lado A", "categoria": "Lado A"}]}
    llm = FakeLLM([json.dumps(p1), "```json\n" + json.dumps(p2) + "\n```"])
    ap = ExtractionAgent(llm, chunk_chars=1200).run(_doc(3, 500))
    assert len(llm.chamadas) == 2
    assert ap.identificacao.seguradora == "X" and ap.identificacao.numero_apolice == "9"
    assert [c.nome for c in ap.coberturas] == ["Custos de Defesa", "Lado A"]  # duplicata removida
    ap, _ = ValidationAgent(llm).run(ap)
    assert ap.limite_maximo_garantia.valor == 1_000_000.0  # preenchido a partir do texto


def test_extracao_corrige_json_fora_do_esquema():
    ruim = {"coberturas": [{"categoria": "Lado A"}]}  # falta 'nome' (obrigatório)
    bom = {"coberturas": [{"nome": "Lado A", "categoria": "Lado A"}]}
    llm = FakeLLM([json.dumps(ruim), json.dumps(bom)])
    ap = ExtractionAgent(llm).run(_doc(1, 100))
    assert ap.coberturas[0].nome == "Lado A"


def test_validacao_detecta_inconsistencias():
    ap = ApoliceDO(
        identificacao=Identificacao(vigencia_inicio="01/03/2027", vigencia_fim="01/03/2026"),
        limite_maximo_garantia=Valor(valor=1_000_000),
        coberturas=[Cobertura(nome="Lado A", categoria="Lado A", limite=Valor(valor=2_000_000))],
    )
    ap, alertas = ValidationAgent(FakeLLM([])).run(ap)
    msgs = " ".join(a["mensagem"] for a in alertas)
    assert "excede o LMG" in msgs and "Fim de vigência" in msgs
    assert ap.identificacao.vigencia_inicio == "2027-03-01"


def test_comparacao_usa_llm_e_faz_fallback():
    a = ApoliceDO(identificacao=Identificacao(seguradora="A"), exclusoes=[Exclusao(titulo="Poluição")])
    b = ApoliceDO(identificacao=Identificacao(seguradora="B"))
    ok = {"resumo_executivo": "ok", "diferencas_chave": [], "pontos_de_atencao": [], "recomendacao": "r"}
    _, analise = ComparisonAgent(FakeLLM([json.dumps(ok)])).run({"A": a, "B": b})
    assert analise["resumo_executivo"] == "ok"
    _, analise = ComparisonAgent(FakeLLM(["não é json", "continua não sendo"])).run({"A": a, "B": b})
    assert "Fallback" in analise["recomendacao"]


def test_provedor_sem_chave_da_erro_claro(settings):
    from do_platform.llm import LLMError
    s = settings.model_copy(update={"anthropic_api_key": None})
    with pytest.raises(LLMError, match="ANTHROPIC_API_KEY"):
        get_provider("anthropic", settings=s)


def test_triagem_heuristica_usa_o_titulo_do_documento():
    from do_platform.agents.heuristics import triage_heuristic
    apolice = "APÓLICE DE SEGURO D&O\n" + "texto " * 200 + "Além das exclusões das Condições Gerais, não cobre..."
    assert triage_heuristic(apolice)["tipo_documento"] == "apolice"
    cg = "CONDIÇÕES GERAIS DO SEGURO DE RESPONSABILIDADE CIVIL D&O\nCláusula 1 – Objeto da apólice"
    assert triage_heuristic(cg)["tipo_documento"] == "condicoes_gerais"


def test_limite_de_paginas(settings):
    pdf = (SAMPLES / "apolice_aurora_do.pdf").read_bytes()  # 2 páginas
    with pytest.raises(IngestionError, match="limite"):
        load_document("a.pdf", pdf, settings.model_copy(update={"max_pages": 1}))
    assert len(load_document("a.pdf", pdf, settings).pages) == 2
