"""Testes da API REST (modo offline, banco temporário). Não exigem chave de API."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OFFLINE = {"X-LLM-Provider": "offline"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    from do_platform import config
    config.get_settings.cache_clear()
    import api.main
    main = importlib.reload(api.main)
    yield TestClient(main.app)
    config.get_settings.cache_clear()


def _add_samples(client) -> list[int]:
    ids = []
    for name in ("apolice_aurora_do.pdf", "apolice_boreal_do.pdf"):
        r = client.post(f"/api/samples/{name}", headers=OFFLINE)
        assert r.status_code == 200, r.text
        ids.append(r.json()["id"])
    return ids


def test_interface_e_saude(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    r = client.get("/")
    assert r.status_code == 200 and "Abrir a plataforma" in r.text
    assert r.headers["cache-control"] == "no-cache"
    app_page = client.get("/app")
    assert app_page.status_code == 200 and 'id="view"' in app_page.text
    for asset in ("/static/css/landing.css", "/static/js/landing.js"):
        assert client.get(asset).status_code == 200
    assert client.get("/static/js/app.js").status_code == 200


def test_provedores_e_modelos_offline(client):
    p = client.get("/api/llm/providers").json()
    assert p["default"] == "offline"
    assert {x["name"] for x in p["providers"]} == {"anthropic", "openai", "gemini", "offline"}
    assert client.get("/api/llm/models", headers=OFFLINE).json()["models"][0]["id"] == "heurístico"
    assert client.get("/api/llm/models", headers={"X-LLM-Provider": "xpto"}).status_code == 400


def test_provedor_sem_chave_retorna_502_com_mensagem(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import api.main
    api.main.settings.anthropic_api_key = None
    r = client.get("/api/llm/models", headers={"X-LLM-Provider": "anthropic"})
    assert r.status_code == 502 and "ANTHROPIC_API_KEY" in r.json()["detail"]


def test_fluxo_processar_detalhar_comparar_exportar(client):
    ids = _add_samples(client)
    assert len(client.get("/api/policies").json()) == 2

    d = client.get(f"/api/policies/{ids[0]}").json()
    assert d["apolice"]["identificacao"]["seguradora"]
    assert d["tem_original"] is True
    f = client.get(f"/api/policies/{ids[0]}/file")
    assert f.status_code == 200 and f.content[:4] == b"%PDF"
    assert client.get(f"/api/policies/{ids[0]}/pages").json()[0]["numero"] == 1

    # reenvio do mesmo arquivo reaproveita o resultado
    again = client.post("/api/samples/apolice_aurora_do.pdf", headers=OFFLINE).json()
    assert again["reaproveitado"] is True and again["id"] == ids[0]

    cmp = client.post("/api/compare", json={"ids": ids}, headers=OFFLINE)
    assert cmp.status_code == 200
    body = cmp.json()
    assert len(body["resultado"]["labels"]) == 2 and body["analise"]["resumo_executivo"]
    for fmt, marker in (("xlsx", b"PK"), ("md", b"# Compara")):
        e = client.post(f"/api/compare/export/{fmt}", json={"resultado": body["resultado"], "analise": body["analise"]})
        assert e.status_code == 200 and e.content.startswith(marker)

    stats = client.get("/api/stats").json()
    assert stats["apolices"] == 2 and stats["comparacoes"] == 1


def test_upload_multipart_e_formato_invalido(client):
    pdf = (ROOT / "samples" / "apolice_boreal_do.pdf").read_bytes()
    r = client.post("/api/policies", files={"file": ("boreal.pdf", pdf, "application/pdf")},
                    data={"force": "false"}, headers=OFFLINE)
    assert r.status_code == 200 and r.json()["apolice"]["coberturas"]
    bad = client.post("/api/policies", files={"file": ("nota.txt", b"oi", "text/plain")}, headers=OFFLINE)
    assert bad.status_code == 415


def test_revisao_humana_e_exclusao(client):
    aid = _add_samples(client)[0]
    ap = client.get(f"/api/policies/{aid}").json()["apolice"]
    ap["observacoes"] = "Revisado manualmente"
    new_id = client.put(f"/api/policies/{aid}", json=ap).json()["id"]
    assert client.get(f"/api/policies/{new_id}").json()["apolice"]["observacoes"] == "Revisado manualmente"
    assert client.put(f"/api/policies/{new_id}", json={"coberturas": "x"}).status_code == 422

    assert client.delete(f"/api/policies/{new_id}").status_code == 204
    assert client.get(f"/api/policies/{new_id}").status_code == 404


def test_consulta_e_sql_somente_leitura(client):
    ids = _add_samples(client)
    a = client.post("/api/ask", json={"pergunta": "Quem cobre o Lado C?", "ids": ids}, headers=OFFLINE).json()
    assert a["resposta"] and a["trechos"]
    ok = client.post("/api/sql", json={"sql": "SELECT seguradora FROM apolices"}).json()
    assert ok["total"] == 2 and ok["columns"] == ["seguradora"]
    assert client.post("/api/sql", json={"sql": "DELETE FROM apolices"}).status_code == 400
    assert set(client.get("/api/sql/examples").json())


def test_amostra_nao_permite_sair_da_pasta(client):
    assert client.post("/api/samples/..%2Frequirements.txt", headers=OFFLINE).status_code == 404
    assert client.post("/api/samples/inexistente.pdf", headers=OFFLINE).status_code == 404


@pytest.fixture
def demo_client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "demo.db"))
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    from do_platform import config
    config.get_settings.cache_clear()
    import api.main
    main = importlib.reload(api.main)
    with TestClient(main.app) as c:  # "with" executa o lifespan (carga das amostras)
        yield c
    config.get_settings.cache_clear()


def test_modo_demo_carrega_e_protege_amostras(demo_client):
    assert demo_client.get("/api/config").json() == {"demo_mode": True, "max_upload_mb": 1}
    rows = demo_client.get("/api/policies").json()
    assert {r["arquivo"] for r in rows} >= {"apolice_aurora_do.pdf", "apolice_boreal_do.pdf"}
    aid = rows[0]["id"]
    d = demo_client.get(f"/api/policies/{aid}").json()
    assert d["protegida"] is True and d["tem_original"] is True
    assert demo_client.delete(f"/api/policies/{aid}").status_code == 403
    assert demo_client.put(f"/api/policies/{aid}", json=d["apolice"]).status_code == 403

    grande = b"%PDF" + b"0" * (1024 * 1024 + 10)
    r = demo_client.post("/api/policies", files={"file": ("grande.pdf", grande, "application/pdf")}, headers=OFFLINE)
    assert r.status_code == 413


def test_indice_da_apolice_e_caminho_da_consulta(client):
    ids = _add_samples(client)
    t = client.get(f"/api/policies/{ids[1]}/index").json()
    assert t["metodo"] == "estrutura" and any(n["titulo"] == "EXCLUSÕES" for n in t["nos"])
    a = client.post("/api/ask", json={"pergunta": "Segurado contra Segurado", "ids": ids}, headers=OFFLINE).json()
    assert a["rota"] == "lexical" and a["caminho"][0]["etapa"] == "Roteador"
    assert a["trechos"][0]["secao"] == "6. Segurado contra Segurado"
    assert client.get("/api/policies/999/index").status_code == 404
