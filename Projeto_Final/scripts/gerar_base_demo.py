"""Gera a base de demonstração pré-processada (samples/processados/).

Processa as amostras numa base temporária e salva o resultado em JSON, que o servidor em modo
demonstração importa ao iniciar (sem OCR nem chamadas à IA). Veja do_platform/demo_base.py.

Uso:
  python scripts/gerar_base_demo.py                      # regras (offline)
  python scripts/gerar_base_demo.py --provedor gemini    # com IA; a chave vem do .env (GEMINI_API_KEY)
  python scripts/gerar_base_demo.py --provedor anthropic --modelo claude-sonnet-5
"""
from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from do_platform.config import get_settings  # noqa: E402
from do_platform.demo_base import write_snapshots  # noqa: E402
from do_platform.ingestion import SUPPORTED_EXT  # noqa: E402
from do_platform.llm import get_provider  # noqa: E402
from do_platform.pipeline import Pipeline  # noqa: E402
from do_platform.storage import Repository  # noqa: E402

SAMPLES = ROOT / "samples"
DESTINO = SAMPLES / "processados"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provedor", default="offline", help="anthropic | openai | gemini | offline")
    ap.add_argument("--modelo", default=None, help="modelo do provedor (padrão: o do provedor)")
    args = ap.parse_args()

    settings = get_settings().model_copy()
    llm = get_provider(args.provedor, args.modelo, settings=settings)
    with tempfile.TemporaryDirectory() as tmp:
        settings.database_path = Path(tmp) / "demo.db"
        settings.uploads_dir = Path(tmp)
        repo = Repository(settings.database_path)
        pipe = Pipeline(llm=llm, settings=settings, repo=repo)
        ids = []
        for path in sorted(p for p in SAMPLES.glob("*") if p.suffix.lower() in SUPPORTED_EXT):
            t = time.perf_counter()
            r = pipe.process(path.name, path.read_bytes(), force=True)
            print(f"{path.name}: {len(r.apolice.coberturas)} coberturas, {len(r.apolice.exclusoes)} exclusões, "
                  f"{len(r.alertas)} alerta(s) · {time.perf_counter() - t:.1f}s")
            ids.append(r.apolice_id)
        write_snapshots(repo, ids, DESTINO, llm.describe())
    print(f"Base gerada em {DESTINO.relative_to(ROOT)} com {llm.describe()}.")


if __name__ == "__main__":
    main()
