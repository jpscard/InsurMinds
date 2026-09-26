"""Mede a qualidade da extração contra o gabarito das amostras.

As amostras são geradas pelos scripts deste projeto, então sabemos exatamente o que cada uma
contém (gerar_amostras.APOLICES e amostras_longas.LONGAS). Este script processa cada apólice
com o provedor escolhido e compara campo a campo com esse gabarito.

Uso:
  python scripts/avaliar_extracao.py                          # regras (offline)
  python scripts/avaliar_extracao.py --provedor gemini        # chave do .env
  python scripts/avaliar_extracao.py --provedor gemini --saida docs/relatorio/avaliacao_gemini.json
  python scripts/avaliar_extracao.py --provedor gemini --modelo gemini-3-flash-preview --sem-resumos --base

--base também grava o resultado como base de demonstração (samples/processados/), numa única rodada.
--sem-resumos usa resumos por regras no índice: 2 chamadas por documento em vez de 3 (útil em cotas gratuitas).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from amostras_longas import LONGAS, RISCOS_EXCLUIDOS  # noqa: E402
from gerar_amostras import APOLICES  # noqa: E402

from do_platform.config import get_settings  # noqa: E402
from do_platform.demo_base import write_snapshots  # noqa: E402
from do_platform.ingestion import SUPPORTED_EXT  # noqa: E402
from do_platform.llm import get_provider  # noqa: E402
from do_platform.pipeline import Pipeline  # noqa: E402
from do_platform.utils import normalize_date, parse_money  # noqa: E402


def norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def parecido(a, b) -> bool:
    """Nomes equivalentes: um contém o outro ou compartilham a maioria das palavras relevantes."""
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return False
    if na in nb or nb in na:
        return True
    pa, pb = {w for w in na.split() if len(w) > 3}, {w for w in nb.split() if len(w) > 3}
    return bool(pa and pb) and len(pa & pb) / min(len(pa), len(pb)) >= 0.6


def gabarito(d: dict) -> dict:
    exclusoes = d.get("exclusoes") or (
        [(t, x) for t, x in d["exclusoes_particulares"]]
        + [(t, x) for t, x, _ in RISCOS_EXCLUIDOS if t not in d["gerais"].get("sem_exclusoes", [])]
        + [(t, x) for t, x, _ in d["gerais"].get("exclusoes_extra", [])])
    return {
        "seguradora": d["seguradora"], "numero": d["numero"],
        "inicio": normalize_date(d["vig"][0]), "fim": normalize_date(d["vig"][1]),
        "lmg": parse_money(d["lmg"])[0], "premio": parse_money(d["premio"])[0],
        "retro": normalize_date(d["retro"]) if re.match(r"\d", d["retro"]) else d["retro"],
        "coberturas": [(n, parse_money(lim)[0]) for n, lim, _ in d["coberturas"]],
        "exclusoes": [t for t, _ in exclusoes],
        "franquias": len(d["franquias"]),
    }


def avaliar(ap, g: dict) -> dict:
    idt = ap.identificacao
    campos = {
        "seguradora": parecido(idt.seguradora, g["seguradora"]),
        "numero_apolice": norm(idt.numero_apolice) == norm(g["numero"]),
        "vigencia_inicio": idt.vigencia_inicio == g["inicio"],
        "vigencia_fim": idt.vigencia_fim == g["fim"],
        "lmg": bool(ap.limite_maximo_garantia) and ap.limite_maximo_garantia.valor == g["lmg"],
        "premio": bool(ap.premio_total) and ap.premio_total.valor == g["premio"],
        "retroatividade": norm(ap.data_retroatividade) == norm(g["retro"]),
    }
    # coberturas: encontradas (nome) e com o limite certo
    achadas = limite_ok = 0
    for nome, lim in g["coberturas"]:
        c = next((c for c in ap.coberturas if parecido(c.nome, nome)), None)
        if c:
            achadas += 1
            limite_ok += bool(c.limite) and c.limite.valor == lim
    exc_achadas = sum(any(parecido(e.titulo, t) for e in ap.exclusoes) for t in g["exclusoes"])
    return {
        "campos": campos,
        "coberturas": {"esperadas": len(g["coberturas"]), "encontradas": achadas, "limite_correto": limite_ok,
                       "extraidas": len(ap.coberturas)},
        "exclusoes": {"esperadas": len(g["exclusoes"]), "encontradas": exc_achadas, "extraidas": len(ap.exclusoes)},
        "franquias": {"esperadas": g["franquias"], "extraidas": len(ap.franquias)},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provedor", default="offline")
    ap.add_argument("--modelo", default=None)
    ap.add_argument("--saida", default=None, help="salva o resultado em JSON")
    ap.add_argument("--base", action="store_true", help="grava também a base de demonstração (samples/processados)")
    ap.add_argument("--sem-resumos", action="store_true", help="resumos do índice por regras (menos chamadas)")
    args = ap.parse_args()

    settings = get_settings().model_copy()
    settings.index_llm_summaries = not args.sem_resumos
    llm = get_provider(args.provedor, args.modelo, settings=settings)
    gabaritos = {d["arquivo"]: d for d in list(APOLICES.values()) + list(LONGAS.values())}
    docs = [(p.name, gabaritos.get(p.name)) for p in sorted((ROOT / "samples").glob("*"))
            if p.suffix.lower() in SUPPORTED_EXT]
    resultado = {"provedor": llm.describe(), "documentos": {}}
    tot_campos = ok_campos = tot_cob = ok_cob = ok_lim = tot_exc = ok_exc = 0
    with tempfile.TemporaryDirectory() as tmp:
        settings.database_path, settings.uploads_dir = Path(tmp) / "a.db", Path(tmp)
        pipe = Pipeline(llm=llm, settings=settings)
        ids = []
        for arquivo, d in docs:
            t = time.perf_counter()
            r = pipe.process(arquivo, (ROOT / "samples" / arquivo).read_bytes(), force=True)
            ids.append(r.apolice_id)
            for aviso in r.avisos:
                print(f"  aviso ({arquivo}): {aviso}")
            if d is None:  # sem gabarito (ex.: condições gerais): só entra na base
                print(f"{arquivo:36} triagem: {r.triagem.get('tipo_documento')} · {time.perf_counter() - t:.1f}s")
                continue
            av = avaliar(r.apolice, gabarito(d))
            av["segundos"] = round(time.perf_counter() - t, 1)
            av["erros_de_campo"] = [k for k, v in av["campos"].items() if not v]
            resultado["documentos"][arquivo] = av
            c = av["campos"]
            tot_campos += len(c); ok_campos += sum(c.values())
            tot_cob += av["coberturas"]["esperadas"]; ok_cob += av["coberturas"]["encontradas"]
            ok_lim += av["coberturas"]["limite_correto"]
            tot_exc += av["exclusoes"]["esperadas"]; ok_exc += av["exclusoes"]["encontradas"]
            print(f"{arquivo:36} campos {sum(c.values())}/{len(c)} · coberturas {av['coberturas']['encontradas']}/"
                  f"{av['coberturas']['esperadas']} (limite certo {av['coberturas']['limite_correto']}) · exclusões "
                  f"{av['exclusoes']['encontradas']}/{av['exclusoes']['esperadas']} · {av['segundos']}s"
                  + (f" · erros: {', '.join(av['erros_de_campo'])}" if av["erros_de_campo"] else ""))
        if args.base:
            write_snapshots(pipe.repo, ids, ROOT / "samples" / "processados", llm.describe())
            print(f"Base de demonstração gravada em samples/processados ({llm.describe()}).")
    resultado["total"] = {
        "campos_gerais": f"{ok_campos}/{tot_campos}", "campos_gerais_pct": round(100 * ok_campos / tot_campos, 1),
        "coberturas_pct": round(100 * ok_cob / tot_cob, 1), "limites_pct": round(100 * ok_lim / tot_cob, 1),
        "exclusoes_pct": round(100 * ok_exc / tot_exc, 1),
    }
    print(f"\nTOTAL ({llm.describe()}): campos gerais {resultado['total']['campos_gerais_pct']}% · coberturas "
          f"{resultado['total']['coberturas_pct']}% · limites {resultado['total']['limites_pct']}% · exclusões "
          f"{resultado['total']['exclusoes_pct']}%")
    if args.saida:
        Path(args.saida).write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
