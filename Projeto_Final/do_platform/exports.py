"""Exportação da comparação de apólices (Excel e Markdown).

Recebe o resultado já calculado, então exportar não chama o LLM de novo.
"""
from __future__ import annotations

import io

import pandas as pd

from .comparison import ComparisonResult


def comparison_xlsx(res: ComparisonResult, analise: dict) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        pd.DataFrame(res.geral).to_excel(w, sheet_name="Dados gerais", index=False)
        pd.DataFrame(res.coberturas).to_excel(w, sheet_name="Coberturas", index=False)
        pd.DataFrame(res.exclusoes).to_excel(w, sheet_name="Exclusões", index=False)
        pd.DataFrame(res.franquias).to_excel(w, sheet_name="Franquias", index=False)
        pd.DataFrame(analise.get("diferencas_chave", [])).to_excel(w, sheet_name="Análise", index=False)
    return buf.getvalue()


def comparison_markdown(res: ComparisonResult, analise: dict) -> str:
    out = ["# Comparação de apólices D&O", "", "## Resumo executivo", analise.get("resumo_executivo", ""), "",
           "## Diferenças-chave"]
    for d in analise.get("diferencas_chave", []):
        out.append(f"- **{d.get('tema')}** ({d.get('impacto')}, favorece: {d.get('favorece')}): {d.get('descricao')}")
    out += ["", "## Pontos de atenção"] + [f"- {p}" for p in analise.get("pontos_de_atencao", [])]
    out += ["", "## Recomendação", analise.get("recomendacao", ""), ""]
    for titulo, tab in [("Dados gerais", res.geral), ("Coberturas", res.coberturas),
                        ("Exclusões", res.exclusoes), ("Franquias", res.franquias)]:
        out += [f"## {titulo}", pd.DataFrame(tab).to_markdown(index=False), ""]
    return "\n".join(out)
