"""Comparação determinística entre apólices estruturadas.

Calcula as diferenças objetivas (valores, presença/ausência de coberturas e
exclusões) sem LLM. Isso garante que números e fatos na comparação sejam
exatos e reprodutíveis; o LLM entra depois apenas para interpretar.

Coberturas e exclusões têm nomes diferentes em cada seguradora
("Custos de Defesa" vs. "Despesas com Defesa"), então são alinhadas por
similaridade de palavras + categoria.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..schema import ApoliceDO, Valor
from ..utils import fmt_money, norm_key, similarity

MATCH_THRESHOLD = 0.34


def _v(v: Valor | None) -> str:
    if not v:
        return "—"
    if v.valor is not None:
        return fmt_money(v.valor, v.moeda)
    return v.texto or "—"


def policy_label(ap: ApoliceDO, fallback: str) -> str:
    """Rótulo curto para colunas de tabela, ex.: 'Aurora · 1010.0045871'."""
    seg = ap.identificacao.seguradora or fallback
    genericas = {"seguros", "seguradora", "companhia", "cia", "de", "do", "sa", "s a", "ficticia", "brasil"}
    palavras = [w for w in re.split(r"[\s()/.,]+", seg) if len(norm_key(w)) > 2 and norm_key(w) not in genericas]
    curto = " ".join(palavras[:2]) or seg[:20]
    num = ap.identificacao.numero_apolice
    return f"{curto} · {num}" if num else curto


@dataclass
class Group:
    nome: str
    categoria: str
    membros: dict[str, object] = field(default_factory=dict)


def align(items_by_label: dict[str, list], name_of, cat_of) -> list[Group]:
    groups: list[Group] = []
    for label, items in items_by_label.items():
        used: set[int] = set()
        for it in items:
            best, best_score = None, 0.0
            for gi, g in enumerate(groups):
                if gi in used or label in g.membros:
                    continue
                score = similarity(name_of(it), g.nome)
                if cat_of(it) == g.categoria and cat_of(it) != "Outra":
                    score += 0.15
                if score > best_score:
                    best, best_score = gi, score
            if best is not None and best_score >= MATCH_THRESHOLD:
                groups[best].membros[label] = it
                used.add(best)
            else:
                groups.append(Group(name_of(it), cat_of(it), {label: it}))
                used.add(len(groups) - 1)
    return groups


@dataclass
class ComparisonResult:
    labels: list[str]
    geral: list[dict]
    coberturas: list[dict]
    exclusoes: list[dict]
    franquias: list[dict]
    diferencas: list[str]
    metricas: dict[str, dict]


def compare(apolices: dict[str, ApoliceDO]) -> ComparisonResult:
    """`apolices`: rótulo -> ApoliceDO (mínimo 2)."""
    if len(apolices) < 2:
        raise ValueError("Selecione ao menos duas apólices para comparar")
    labels = list(apolices)
    diffs: list[str] = []

    # --- Dados gerais -------------------------------------------------------
    campos = [
        ("Seguradora", lambda a: a.identificacao.seguradora),
        ("Nº da apólice", lambda a: a.identificacao.numero_apolice),
        ("Tomador", lambda a: a.identificacao.tomador),
        ("Vigência", lambda a: f"{a.identificacao.vigencia_inicio or '?'} a {a.identificacao.vigencia_fim or '?'}"),
        ("Limite Máximo de Garantia", lambda a: _v(a.limite_maximo_garantia)),
        ("Prêmio total", lambda a: _v(a.premio_total)),
        ("Base de cobertura", lambda a: a.base_cobertura),
        ("Data de retroatividade", lambda a: a.data_retroatividade),
        ("Prazo complementar", lambda a: a.prazo_complementar),
        ("Territorialidade", lambda a: a.territorialidade),
        ("Custos de defesa", lambda a: a.custos_defesa),
        ("Nº de coberturas", lambda a: str(len(a.coberturas))),
        ("Nº de exclusões", lambda a: str(len(a.exclusoes))),
    ]
    geral = []
    for nome, fn in campos:
        row = {"Campo": nome}
        vals = []
        for lb in labels:
            val = fn(apolices[lb]) or "—"
            row[lb] = val
            vals.append(str(val).strip().lower())
        row["Diferente"] = len(set(vals)) > 1
        geral.append(row)
        if row["Diferente"] and nome not in {"Seguradora", "Nº da apólice", "Tomador", "Vigência"}:
            diffs.append(f"{nome}: " + "; ".join(f"{lb} = {row[lb]}" for lb in labels))

    # --- Métricas -----------------------------------------------------------
    metricas = {}
    for lb in labels:
        a = apolices[lb]
        lmg = a.limite_maximo_garantia.valor if a.limite_maximo_garantia else None
        pr = a.premio_total.valor if a.premio_total else None
        metricas[lb] = {
            "lmg": lmg, "premio": pr,
            "taxa_pct": round(pr / lmg * 100, 3) if lmg and pr else None,
            "coberturas": len(a.coberturas), "exclusoes": len(a.exclusoes),
        }
    taxas = {lb: m["taxa_pct"] for lb, m in metricas.items() if m["taxa_pct"] is not None}
    if len(taxas) >= 2:
        diffs.append("Custo relativo (prêmio/LMG): " + "; ".join(f"{lb} = {t:.3f}%" for lb, t in taxas.items()))

    # --- Coberturas ---------------------------------------------------------
    groups = align({lb: apolices[lb].coberturas for lb in labels}, lambda c: c.nome, lambda c: c.categoria)
    coberturas = []
    for g in groups:
        row = {"Cobertura": g.nome, "Categoria": g.categoria}
        limites = []
        for lb in labels:
            c = g.membros.get(lb)
            if c is None:
                row[lb] = "✗ não prevista"
            else:
                lim = _v(c.limite)
                fr = f" · franquia {_v(c.franquia)}" if c.franquia else ""
                row[lb] = f"✓ {lim}{fr}"
                limites.append(lim)
        ausentes = [lb for lb in labels if lb not in g.membros]
        if ausentes:
            row["Situação"] = "Ausente em " + ", ".join(ausentes)
            diffs.append(f"Cobertura '{g.nome}' ({g.categoria}) não prevista em: {', '.join(ausentes)}")
        elif len(set(limites)) > 1:
            row["Situação"] = "Limites diferentes"
            diffs.append(f"Cobertura '{g.nome}' com limites diferentes: "
                         + "; ".join(f"{lb} = {row[lb]}" for lb in labels))
        else:
            row["Situação"] = "Equivalente"
        coberturas.append(row)

    # --- Exclusões ----------------------------------------------------------
    groups = align({lb: apolices[lb].exclusoes for lb in labels}, lambda e: e.titulo, lambda e: e.categoria)
    exclusoes = []
    for g in groups:
        row = {"Exclusão": g.nome, "Categoria": g.categoria}
        for lb in labels:
            row[lb] = "✓ exclui" if lb in g.membros else "—"
        presentes = [lb for lb in labels if lb in g.membros]
        if len(presentes) < len(labels):
            row["Situação"] = "Só em " + ", ".join(presentes)
            diffs.append(f"Exclusão '{g.nome}' presente apenas em: {', '.join(presentes)} "
                         f"(mais restritiva nesse ponto)")
        else:
            row["Situação"] = "Em todas"
        exclusoes.append(row)

    # --- Franquias ----------------------------------------------------------
    groups = align({lb: apolices[lb].franquias for lb in labels}, lambda f: f.aplicacao, lambda f: "Outra")
    franquias = []
    for g in groups:
        row = {"Aplicação": g.nome}
        for lb in labels:
            f = g.membros.get(lb)
            row[lb] = _v(f.valor) if f else "—"
        franquias.append(row)
        vals = {row[lb] for lb in labels}
        if len(vals) > 1:
            diffs.append(f"Franquia '{g.nome}': " + "; ".join(f"{lb} = {row[lb]}" for lb in labels))

    return ComparisonResult(labels, geral, coberturas, exclusoes, franquias, diffs, metricas)
