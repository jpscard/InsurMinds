"""Agente de Comparação: interpreta as diferenças calculadas e produz uma análise executiva."""
from __future__ import annotations

import json
import time

from ..comparison import ComparisonResult, compare
from ..schema import ApoliceDO
from .base import Agent
from .prompts import COMPARACAO_SYSTEM, COMPARACAO_USER


_CATEGORIAS_CENTRAIS = {"Lado A", "Lado B", "Lado C", "Custos de Defesa"}
_ORDEM_IMPACTO = {"alto": 0, "medio": 1, "baixo": 2}


def _diferencas_por_regras(res: ComparisonResult) -> list[dict]:
    """Diferenças-chave classificadas por impacto a partir das tabelas já calculadas (sem LLM)."""
    labels, m = res.labels, res.metricas
    out: list[dict] = []

    def melhor(chave, maior=True):
        vals = {lb: m[lb][chave] for lb in labels if m[lb][chave] is not None}
        if len(set(vals.values())) < 2:
            return "neutro"
        return (max if maior else min)(vals, key=vals.get)

    geral = {r["Campo"]: r for r in res.geral if r.get("Diferente")}
    for campo, impacto, fav in (("Limite Máximo de Garantia", "alto", melhor("lmg")),
                                ("Prêmio total", "medio", melhor("premio", maior=False)),
                                ("Data de retroatividade", "medio", "neutro"),
                                ("Prazo complementar", "medio", "neutro"),
                                ("Territorialidade", "medio", "neutro"),
                                ("Custos de defesa", "medio", "neutro"),
                                ("Base de cobertura", "baixo", "neutro")):
        if campo in geral:
            out.append({"tema": campo, "impacto": impacto, "favorece": fav,
                        "descricao": "; ".join(f"{lb}: {geral[campo][lb]}" for lb in labels)})
    taxas = {lb: m[lb]["taxa_pct"] for lb in labels if m[lb]["taxa_pct"] is not None}
    if len(set(taxas.values())) > 1:
        out.append({"tema": "Custo relativo (prêmio/LMG)", "impacto": "medio", "favorece": melhor("taxa_pct", maior=False),
                    "descricao": "; ".join(f"{lb}: {t:.3f}%" for lb, t in taxas.items())})

    for r in res.coberturas:
        sit = r.get("Situação", "")
        if sit.startswith("Ausente"):
            tem = [lb for lb in labels if not str(r[lb]).startswith("✗")]
            out.append({"tema": f"Cobertura: {r['Cobertura']}",
                        "impacto": "alto" if r["Categoria"] in _CATEGORIAS_CENTRAIS else "medio",
                        "favorece": ", ".join(tem), "descricao": f"Prevista em {', '.join(tem)}; {sit[:1].lower() + sit[1:]}."})
        elif sit.startswith("Limites"):
            out.append({"tema": f"Cobertura: {r['Cobertura']}", "impacto": "baixo", "favorece": "neutro",
                        "descricao": "Limites diferentes: " + "; ".join(f"{lb}: {r[lb].lstrip('✓ ')}" for lb in labels)})
    for r in res.exclusoes:
        sit = r.get("Situação", "")
        if sit.startswith("Só em"):
            com = [lb for lb in labels if r[lb] != "—"]
            sem = [lb for lb in labels if r[lb] == "—"]
            out.append({"tema": f"Exclusão: {r['Exclusão']}", "impacto": "alto" if len(com) == 1 else "medio",
                        "favorece": ", ".join(sem),
                        "descricao": f"Só {', '.join(com)} exclui; {', '.join(sem)} não tem essa restrição."})
    return sorted(out, key=lambda d: _ORDEM_IMPACTO[d["impacto"]])


def _analise_offline(res: ComparisonResult) -> dict:
    """Análise por regras, usada sem LLM ou se o LLM falhar."""
    m = res.metricas
    maior_lmg = max(m, key=lambda lb: m[lb]["lmg"] or 0)
    mais_cob = max(m, key=lambda lb: m[lb]["coberturas"])
    menos_exc = min(m, key=lambda lb: m[lb]["exclusoes"])
    taxas = {lb: v["taxa_pct"] for lb, v in m.items() if v["taxa_pct"] is not None}
    resumo = (f"Foram identificadas {len(res.diferencas)} diferenças objetivas. "
              f"Maior LMG: {maior_lmg}. Mais coberturas: {mais_cob}. "
              f"Menos exclusões: {menos_exc}.")
    if taxas:
        resumo += f" Menor custo relativo (prêmio/LMG): {min(taxas, key=taxas.get)}."
    return {
        "resumo_executivo": resumo,
        "diferencas_chave": _diferencas_por_regras(res),
        "pontos_de_atencao": [d for d in res.diferencas if "não prevista" in d or "apenas em" in d][:10],
        "recomendacao": "Análise gerada por regras (modo offline). Configure um provedor de LLM para "
                        "uma avaliação qualitativa. A decisão final exige revisão por especialista.",
        "modo": "regras",
    }


class ComparisonAgent(Agent):
    nome = "Comparação"

    def run(self, apolices: dict[str, ApoliceDO]) -> tuple[ComparisonResult, dict]:
        t0 = time.perf_counter()
        res = compare(apolices)
        self.trace.add(self.nome, "Diferenças determinísticas", t0, f"{len(res.diferencas)} diferença(s)")

        t1 = time.perf_counter()
        if self.llm.is_offline:
            analise = _analise_offline(res)
        else:
            payload = {lb: ap.model_dump(exclude_none=True) for lb, ap in apolices.items()}
            # trechos-fonte ocupam muito contexto e não são necessários aqui
            for ap in payload.values():
                for lst in ("coberturas", "exclusoes"):
                    for it in ap.get(lst, []):
                        it.pop("trecho_fonte", None)
            user = COMPARACAO_USER.format(
                apolices=json.dumps(payload, ensure_ascii=False, indent=1),
                diferencas="\n".join(f"- {d}" for d in res.diferencas) or "(nenhuma)",
            )
            try:
                analise = self.llm.complete_json(COMPARACAO_SYSTEM, user)
            except Exception as exc:  # noqa: BLE001
                self.log.warning("Análise via LLM falhou (%s); usando regras", exc)
                analise = _analise_offline(res)
                analise["recomendacao"] = f"[Fallback: o LLM falhou: {exc}] " + analise["recomendacao"]
        self.trace.add(self.nome, "Análise qualitativa", t1, self.llm.describe())
        return res, analise
