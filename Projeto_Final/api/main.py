"""API REST da Plataforma D&O e servidor da interface web.

Execute:  uvicorn api.main:app --reload     (ou: python -m api)

O provedor, o modelo e a chave de LLM chegam em cada requisição pelos cabeçalhos
X-LLM-Provider, X-LLM-Model e X-LLM-Key. O servidor não guarda a chave: sem o
cabeçalho, vale a configuração do .env.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from do_platform.comparison import ComparisonResult
from do_platform.config import ROOT_DIR, Settings, get_settings
from do_platform.exports import comparison_markdown, comparison_xlsx
from do_platform.ingestion import SUPPORTED_EXT, IngestionError
from do_platform.llm import PROVIDERS, LLMError, get_provider
from do_platform.pipeline import Pipeline
from do_platform.schema import ApoliceDO
from do_platform.storage import Repository

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("api")

WEB_DIR = ROOT_DIR / "web"
SAMPLES_DIR = ROOT_DIR / "samples"

settings = get_settings()
repo = Repository(settings.database_path)


def _sample_names() -> set[str]:
    return {p.name for p in SAMPLES_DIR.glob("*") if p.suffix.lower() in SUPPORTED_EXT}


def _seed_samples() -> None:
    """Modo demonstração: a carteira nunca começa vazia (o disco do deploy gratuito é efêmero)."""
    if repo.list():
        return
    pipe = Pipeline(llm=get_provider("offline", settings=settings), settings=settings, repo=repo)
    for name in sorted(_sample_names()):
        try:
            data = (SAMPLES_DIR / name).read_bytes()
            r = pipe.process(name, data)
            _upload_path(repo.get_row(r.apolice_id)["sha256"], name).write_bytes(data)
            log.info("Amostra carregada: %s -> #%s", name, r.apolice_id)
        except Exception:  # noqa: BLE001 - uma amostra com problema não impede o servidor de subir
            log.exception("Falha ao carregar a amostra %s", name)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.demo_mode:
        _seed_samples()
    yield


app = FastAPI(title="D&O Insight API", version="1.0.0", lifespan=lifespan,
              description="Ingestão, extração, comparação e consulta de apólices D&O.")


def _protected(row: dict) -> bool:
    return settings.demo_mode and row["arquivo"] in _sample_names()


def _guard(row: dict) -> None:
    if _protected(row):
        raise HTTPException(403, "Apólice de demonstração: não pode ser alterada nem excluída. "
                                 "Envie seus próprios documentos para testar essas funções.")


# --------------------------------------------------------------------------- erros
@app.exception_handler(LLMError)
async def _llm_error(_: Request, exc: LLMError):
    return JSONResponse({"detail": str(exc)}, status_code=502)


@app.exception_handler(IngestionError)
async def _ingestion_error(_: Request, exc: IngestionError):
    return JSONResponse({"detail": str(exc)}, status_code=422)


@app.exception_handler(KeyError)
async def _not_found(_: Request, exc: KeyError):
    return JSONResponse({"detail": str(exc.args[0]) if exc.args else "Não encontrado"}, status_code=404)


# --------------------------------------------------------------------------- LLM por requisição
class LLMContext:
    def __init__(self, provider: str, model: str | None, settings: Settings):
        self.provider, self.model, self.settings = provider, model, settings

    def pipeline(self) -> Pipeline:
        llm = get_provider(self.provider, self.model, settings=self.settings)
        return Pipeline(llm=llm, settings=self.settings, repo=repo)


def llm_context(
    x_llm_provider: Annotated[str | None, Header()] = None,
    x_llm_model: Annotated[str | None, Header()] = None,
    x_llm_key: Annotated[str | None, Header()] = None,
) -> LLMContext:
    prov = (x_llm_provider or settings.llm_provider).lower().strip()
    if prov not in PROVIDERS:
        raise HTTPException(400, f"Provedor desconhecido: {prov}")
    s = settings.model_copy()
    if x_llm_key and prov != "offline":
        setattr(s, f"{prov}_api_key", x_llm_key)
    return LLMContext(prov, (x_llm_model or "").strip() or None, s)


LLM = Annotated[LLMContext, Depends(llm_context)]

_models_cache: dict[tuple[str, str], tuple[float, list]] = {}
MODELS_TTL_S = 3600


@app.get("/api/llm/providers")
def providers():
    return {
        "default": settings.llm_provider,
        "providers": [
            {"name": name, "default_model": settings.llm_model or cls.default_model,
             "has_env_key": name == "offline" or bool(getattr(settings, f"{name}_api_key", None))}
            for name, cls in PROVIDERS.items()
        ],
    }


@app.get("/api/llm/models")
def models(ctx: LLM):
    """Modelos disponíveis para a chave informada (ou a do .env), com cache de 1 h."""
    if ctx.provider == "offline":
        return {"models": [{"id": "heurístico", "name": "Regras (sem IA)"}]}
    key = getattr(ctx.settings, f"{ctx.provider}_api_key") or ""
    cache_key = (ctx.provider, hashlib.sha256(key.encode()).hexdigest())
    hit = _models_cache.get(cache_key)
    if hit and time.time() - hit[0] < MODELS_TTL_S:
        items = hit[1]
    else:
        items = get_provider(ctx.provider, settings=ctx.settings).list_models()
        _models_cache[cache_key] = (time.time(), items)
    return {"models": [{"id": i, "name": n} for i, n in items]}


# --------------------------------------------------------------------------- apólices
def _upload_path(sha256: str, filename: str) -> Path:
    return settings.uploads_dir / f"{sha256}{Path(filename).suffix.lower()}"


def _trace(trace) -> list[dict]:
    return [dataclasses.asdict(s) for s in trace.steps]


def _process(ctx: LLMContext, filename: str, data: bytes, force: bool) -> dict:
    if Path(filename).suffix.lower() not in SUPPORTED_EXT:
        raise HTTPException(415, f"Formato não suportado: {filename}")
    r = ctx.pipeline().process(filename, data, force=force)
    row = repo.get_row(r.apolice_id)
    path = _upload_path(row["sha256"], filename)
    if not path.exists():
        path.write_bytes(data)  # guarda o original para visualização
    return {
        "id": r.apolice_id, "arquivo": r.arquivo, "reaproveitado": r.reaproveitado,
        "avisos": r.avisos, "alertas": r.alertas, "triagem": r.triagem, "trace": _trace(r.trace),
        "apolice": r.apolice.model_dump(),
    }


@app.get("/api/policies")
def list_policies():
    return repo.list()


@app.post("/api/policies")
def upload_policy(ctx: LLM, file: UploadFile = File(...), force: bool = Form(False)):
    limit = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"Arquivo maior que {settings.max_upload_mb} MB.")
    name = file.filename or "documento"
    if settings.demo_mode and name in _sample_names():
        force = False  # não deixa reprocessar por cima das amostras protegidas
    return _process(ctx, name, data, force)


@app.get("/api/policies/{aid}")
def get_policy(aid: int):
    row = repo.get_row(aid)
    meta = {k: v for k, v in row.items() if k not in {"dados_json", "triagem_json", "alertas_json"}}
    return {
        "meta": meta,
        "apolice": json.loads(row["dados_json"]),
        "triagem": json.loads(row["triagem_json"] or "{}"),
        "alertas": json.loads(row["alertas_json"] or "[]"),
        "tem_original": _upload_path(row["sha256"], row["arquivo"]).exists(),
        "protegida": _protected(row),
    }


@app.put("/api/policies/{aid}")
def update_policy(aid: int, ap: ApoliceDO):
    row = repo.get_row(aid)
    _guard(row)
    sha = row["sha256"]
    repo.update_data(aid, ap)
    # a regravação gera um novo id; devolve o atual para a interface seguir
    return {"id": repo.find_by_hash(sha)}


@app.delete("/api/policies/{aid}", status_code=204)
def delete_policy(aid: int):
    row = repo.get_row(aid)
    _guard(row)
    repo.delete(aid)
    if not repo.find_by_hash(row["sha256"]):
        _upload_path(row["sha256"], row["arquivo"]).unlink(missing_ok=True)
    return Response(status_code=204)


@app.get("/api/policies/{aid}/pages")
def policy_pages(aid: int):
    repo.get_row(aid)
    return repo.pages(aid)


@app.get("/api/policies/{aid}/file")
def policy_file(aid: int):
    row = repo.get_row(aid)
    path = _upload_path(row["sha256"], row["arquivo"])
    if not path.exists():
        raise HTTPException(404, "O arquivo original não foi guardado (processado antes desta versão).")
    return FileResponse(path, filename=row["arquivo"], content_disposition_type="inline")


@app.get("/api/samples")
def samples():
    return [{"name": p.name, "size": p.stat().st_size}
            for p in sorted(SAMPLES_DIR.rglob("*")) if p.suffix.lower() in SUPPORTED_EXT and p.parent == SAMPLES_DIR]


@app.post("/api/samples/{name}")
def process_sample(name: str, ctx: LLM, force: bool = False):
    path = SAMPLES_DIR / name
    if path.parent != SAMPLES_DIR or not path.is_file():
        raise HTTPException(404, "Amostra não encontrada")
    return _process(ctx, path.name, path.read_bytes(), force and not settings.demo_mode)


# --------------------------------------------------------------------------- comparação
class CompareIn(BaseModel):
    ids: list[int] = Field(..., min_length=2)


@app.post("/api/compare")
def compare(body: CompareIn, ctx: LLM):
    for aid in body.ids:
        repo.get_row(aid)
    res, analise, trace = ctx.pipeline().compare(body.ids)
    return {"resultado": dataclasses.asdict(res), "analise": analise, "trace": _trace(trace),
            "ids": body.ids}


class ExportIn(BaseModel):
    resultado: dict
    analise: dict


@app.post("/api/compare/export/{fmt}")
def export(fmt: str, body: ExportIn):
    res = ComparisonResult(**body.resultado)
    if fmt == "xlsx":
        return Response(comparison_xlsx(res, body.analise),
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": 'attachment; filename="comparacao_do.xlsx"'})
    if fmt == "md":
        return Response(comparison_markdown(res, body.analise), media_type="text/markdown; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="comparacao_do.md"'})
    raise HTTPException(400, "Formato deve ser xlsx ou md")


# --------------------------------------------------------------------------- consulta
class AskIn(BaseModel):
    pergunta: str = Field(..., min_length=3)
    ids: list[int] = Field(..., min_length=1)


@app.post("/api/ask")
def ask(body: AskIn, ctx: LLM):
    out, trace = ctx.pipeline().ask(body.pergunta, body.ids)
    return {**out, "trace": _trace(trace)}


SQL_EXAMPLES = {
    "Apólices por LMG": "SELECT id, seguradora, numero_apolice, lmg, premio, ROUND(premio*100.0/lmg, 3) AS taxa_pct\n"
                        "FROM apolices ORDER BY lmg DESC",
    "Quem cobre Lado C?": "SELECT a.seguradora, c.nome, c.limite, c.franquia\nFROM coberturas c\n"
                          "JOIN apolices a ON a.id = c.apolice_id\nWHERE c.categoria = 'Lado C'",
    "Exclusões por categoria": "SELECT e.categoria, COUNT(*) AS qtd, GROUP_CONCAT(DISTINCT a.seguradora) AS seguradoras\n"
                               "FROM exclusoes e JOIN apolices a ON a.id = e.apolice_id\n"
                               "GROUP BY e.categoria ORDER BY qtd DESC",
    "Maiores franquias de cobertura": "SELECT a.seguradora, c.nome, c.franquia\nFROM coberturas c\n"
                                      "JOIN apolices a ON a.id = c.apolice_id\n"
                                      "WHERE c.franquia IS NOT NULL ORDER BY c.franquia DESC LIMIT 10",
}


class SqlIn(BaseModel):
    sql: str


@app.get("/api/sql/examples")
def sql_examples():
    return SQL_EXAMPLES


@app.post("/api/sql")
def sql(body: SqlIn):
    try:
        rows = repo.query(body.sql)
    except Exception as exc:  # noqa: BLE001 - erro de SQL volta para o usuário
        raise HTTPException(400, str(exc)) from exc
    return {"columns": list(rows[0]) if rows else [], "rows": rows[:1000], "total": len(rows)}


# --------------------------------------------------------------------------- painel e docs
@app.get("/api/stats")
def stats():
    rows = repo.query(
        "SELECT COUNT(*) AS apolices, COUNT(DISTINCT seguradora) AS seguradoras, "
        "SUM(lmg) AS lmg_total, AVG(CASE WHEN lmg > 0 THEN premio * 100.0 / lmg END) AS taxa_media "
        "FROM apolices")[0]
    rows["coberturas"] = repo.query("SELECT COUNT(*) AS n FROM coberturas")[0]["n"]
    rows["comparacoes"] = repo.query("SELECT COUNT(*) AS n FROM comparacoes")[0]["n"]
    return rows


@app.get("/api/about")
def about():
    doc = ROOT_DIR / "docs" / "ARQUITETURA.md"
    return {"markdown": doc.read_text(encoding="utf-8") if doc.exists() else ""}


@app.get("/api/config")
def app_config():
    return {"demo_mode": settings.demo_mode, "max_upload_mb": settings.max_upload_mb}


@app.get("/api/health")
def health():
    return {"status": "ok"}


# --------------------------------------------------------------------------- interface web
@app.middleware("http")
async def _revalidate_static(request: Request, call_next):
    """A interface é servida sem build: o navegador revalida (ETag) para pegar sempre a versão atual."""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(WEB_DIR / "index.html")
