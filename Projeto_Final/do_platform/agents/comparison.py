"""Agente de Comparação: interpreta as diferenças calculadas e produz uma análise executiva."""
from __future__ import annotations

import json
import time

from ..comparison import ComparisonResult, compare
from ..schema import ApoliceDO
from .base import Agent
from .prompts import COMPARACAO_SYSTEM, COMPARACAO_USER


def _analise_offline(res: ComparisonResult) -> dict:
    """Análise mínima por regras, usada sem LLM ou se o LLM falhar."""
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
        "diferencas_chave": [{"tema": d.split(":")[0][:60], "descricao": d, "impacto": "medio",
                              "favorece": "neutro"} for d in res.diferencas[:15]],
        "pontos_de_atencao": [d for d in res.diferencas if "não prevista" in d or "apenas em" in d][:10],
        "recomendacao": "Análise gerada por regras (modo offline). Configure um provedor de LLM para "
                        "uma avaliação qualitativa. A decisão final exige revisão por especialista.",
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
