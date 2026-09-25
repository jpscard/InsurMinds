"""Linha de comando: processa, lista e compara apólices sem a interface web.

Exemplos:
    python cli.py processar samples/*.pdf
    python cli.py listar
    python cli.py comparar 1 2 --saida comparacao.json
    python cli.py perguntar "Qual apólice tem maior prazo complementar?" 1 2
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from do_platform.llm import LLMError
from do_platform.pipeline import Pipeline
from do_platform.utils import fmt_money


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Plataforma de análise de apólices D&O")
    ap.add_argument("--provedor", help="anthropic | openai | gemini | offline (padrão: .env)")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("processar")
    p.add_argument("arquivos", nargs="+", type=Path)
    p.add_argument("--forcar", action="store_true", help="reprocessa mesmo se já estiver no banco")
    sub.add_parser("listar")
    c = sub.add_parser("comparar")
    c.add_argument("ids", nargs="+", type=int)
    c.add_argument("--saida", type=Path)
    q = sub.add_parser("perguntar")
    q.add_argument("pergunta")
    q.add_argument("ids", nargs="+", type=int)
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    try:
        from do_platform.llm import get_provider
        pipe = Pipeline(llm=get_provider(args.provedor))
    except LLMError as exc:
        print(f"Erro de configuração: {exc}", file=sys.stderr)
        return 2

    if args.cmd == "processar":
        falhas = 0
        for f in args.arquivos:
            try:
                r = pipe.process(f.name, f.read_bytes(), force=args.forcar)
            except Exception as exc:  # noqa: BLE001
                falhas += 1
                print(f"✗ {f.name}: {exc}", file=sys.stderr)
                continue
            a = r.apolice
            print(f"✓ {f.name} → #{r.apolice_id} {a.identificacao.seguradora} "
                  f"LMG={fmt_money(a.limite_maximo_garantia.valor if a.limite_maximo_garantia else None)} "
                  f"coberturas={len(a.coberturas)} exclusões={len(a.exclusoes)} alertas={len(r.alertas)}"
                  + (" (já existia)" if r.reaproveitado else ""))
        return 1 if falhas else 0

    if args.cmd == "listar":
        for r in pipe.repo.list():
            print(f"#{r['id']:<3} {r['seguradora'] or r['arquivo']:<45} {r['numero_apolice'] or '':<18} "
                  f"LMG {fmt_money(r['lmg'], r['moeda']):>18}  {r['n_coberturas']} cob. {r['n_exclusoes']} exc.")
        return 0

    if args.cmd == "comparar":
        res, analise, _ = pipe.compare(args.ids)
        print(analise.get("resumo_executivo", ""))
        print("\nDiferenças objetivas:")
        for d in res.diferencas:
            print(" -", d)
        if args.saida:
            args.saida.write_text(json.dumps({"analise": analise, "diferencas": res.diferencas,
                                              "coberturas": res.coberturas, "exclusoes": res.exclusoes,
                                              "geral": res.geral}, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\nSalvo em {args.saida}")
        return 0

    if args.cmd == "perguntar":
        out, _ = pipe.ask(args.pergunta, args.ids)
        print(out["resposta"])
        for t in out["trechos"][:3]:
            print(f"\n[{t['rotulo']} · pág. {t['pagina']}]\n{t['texto'][:400]}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
