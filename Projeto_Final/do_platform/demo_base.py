"""Base de demonstração pré-processada.

O deploy gratuito tem pouca CPU e disco temporário: processar as amostras a cada reinício
(OCR incluído) faz o visitante esperar minutos. Em vez disso, as amostras são processadas
uma vez, fora do servidor (scripts/gerar_base_demo.py, com ou sem IA), e o resultado é
guardado em samples/processados/. O servidor só importa esses JSON ao iniciar.

Cada arquivo guarda o hash do documento de origem: se a amostra mudar, o JSON antigo é
ignorado e a amostra é processada de novo, para nunca exibir dados desatualizados.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

from .schema import ApoliceDO
from .storage import Repository

log = logging.getLogger(__name__)
VERSAO = 1


def export_policy(repo: Repository, aid: int) -> dict:
    row = repo.get_row(aid)
    return {
        "versao": VERSAO,
        "arquivo": row["arquivo"],
        "sha256": row["sha256"],
        "provedor_llm": row["provedor_llm"],
        "processado_em": row["criado_em"],
        "triagem": json.loads(row["triagem_json"] or "{}"),
        "alertas": json.loads(row["alertas_json"] or "[]"),
        "dados": json.loads(row["dados_json"]),
        "paginas": [{"numero": p["numero"], "metodo": p["metodo"], "texto": p["texto"]} for p in repo.pages(aid)],
        "indice": repo.get_index(aid),
    }


def import_policy(repo: Repository, snap: dict) -> int:
    ap = ApoliceDO.model_validate(snap["dados"])
    pages = [(p["numero"], p["metodo"], p["texto"]) for p in snap["paginas"]]
    aid = repo.save(snap["arquivo"], snap["sha256"], ap, pages, snap["triagem"], snap["alertas"], snap["provedor_llm"])
    if snap.get("indice"):
        repo.save_index(aid, snap["indice"])
    return aid


def snapshot_path(base_dir: Path, arquivo: str) -> Path:
    return base_dir / f"{arquivo}.json"


def load_snapshot(base_dir: Path, sample: Path) -> dict | None:
    """JSON pré-processado da amostra, se existir e corresponder ao arquivo atual."""
    path = snapshot_path(base_dir, sample.name)
    if not path.exists():
        return None
    try:
        snap = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        log.warning("Base de demonstração inválida: %s", path.name)
        return None
    if snap.get("versao") != VERSAO or snap.get("sha256") != hashlib.sha256(sample.read_bytes()).hexdigest():
        log.info("Base de demonstração desatualizada para %s; será reprocessada", sample.name)
        return None
    return snap


def write_snapshots(repo: Repository, ids: list[int], base_dir: Path, provedor: str) -> None:
    base_dir.mkdir(parents=True, exist_ok=True)
    for aid in ids:
        snap = export_policy(repo, aid)
        snapshot_path(base_dir, snap["arquivo"]).write_text(
            json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    (base_dir / "manifesto.json").write_text(json.dumps({
        "provedor": provedor, "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "documentos": sorted(export_policy(repo, aid)["arquivo"] for aid in ids),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
