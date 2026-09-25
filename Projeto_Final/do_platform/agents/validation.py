"""Agente de Validação: normaliza e confere a consistência da extração.

É deliberadamente determinístico (sem LLM): funciona como um "revisor" que
pega erros comuns de modelos generativos — valores numéricos não preenchidos,
datas fora do padrão, sublimites maiores que o LMG — e gera alertas para o
usuário em vez de corrigir silenciosamente.
"""
from __future__ import annotations

import time
from datetime import date

from ..schema import ApoliceDO, Valor
from ..utils import fmt_money, normalize_date, parse_money
from .base import Agent


def _fill_valor(v: Valor | None) -> Valor | None:
    if v and v.valor is None and v.texto:
        num, moeda = parse_money(v.texto)
        v.valor = num
        v.moeda = moeda or v.moeda
    return v


class ValidationAgent(Agent):
    nome = "Validação"

    def run(self, ap: ApoliceDO) -> tuple[ApoliceDO, list[dict]]:
        t0 = time.perf_counter()
        alertas: list[dict] = []

        def alerta(nivel: str, msg: str):
            alertas.append({"nivel": nivel, "mensagem": msg})

        idt = ap.identificacao
        idt.vigencia_inicio = normalize_date(idt.vigencia_inicio)
        idt.vigencia_fim = normalize_date(idt.vigencia_fim)
        ap.data_retroatividade = normalize_date(ap.data_retroatividade)
        ap.limite_maximo_garantia = _fill_valor(ap.limite_maximo_garantia)
        ap.premio_total = _fill_valor(ap.premio_total)
        for c in ap.coberturas:
            c.limite = _fill_valor(c.limite)
            c.franquia = _fill_valor(c.franquia)
        for f in ap.franquias:
            f.valor = _fill_valor(f.valor)

        for campo, valor in [("Seguradora", idt.seguradora), ("Número da apólice", idt.numero_apolice),
                             ("Tomador", idt.tomador), ("Início de vigência", idt.vigencia_inicio),
                             ("Fim de vigência", idt.vigencia_fim)]:
            if not valor:
                alerta("aviso", f"{campo} não identificado(a) no documento.")

        lmg = ap.limite_maximo_garantia.valor if ap.limite_maximo_garantia else None
        if lmg is None:
            alerta("aviso", "Limite Máximo de Garantia (LMG) não identificado.")

        try:
            if idt.vigencia_inicio and idt.vigencia_fim:
                ini = date.fromisoformat(idt.vigencia_inicio)
                fim = date.fromisoformat(idt.vigencia_fim)
                if fim <= ini:
                    alerta("erro", "Fim de vigência anterior ou igual ao início.")
                elif (fim - ini).days > 800:
                    alerta("info", f"Vigência longa ({(fim - ini).days} dias); confira.")
                if ap.data_retroatividade and len(ap.data_retroatividade) == 10:
                    if date.fromisoformat(ap.data_retroatividade) > ini:
                        alerta("aviso", "Data de retroatividade posterior ao início da vigência.")
        except ValueError:
            alerta("info", "Datas em formato não padronizado; comparação de vigência limitada.")

        for c in ap.coberturas:
            if lmg and c.limite and c.limite.valor and c.limite.valor > lmg * 1.0001:
                alerta("erro", f"Limite da cobertura '{c.nome}' ({fmt_money(c.limite.valor, c.limite.moeda)}) "
                               f"excede o LMG ({fmt_money(lmg)}).")
        if not ap.coberturas:
            alerta("aviso", "Nenhuma cobertura extraída.")
        if not ap.exclusoes:
            alerta("aviso", "Nenhuma exclusão extraída — pode estar nas Condições Gerais (documento separado).")
        if not any(c.categoria == "Lado A" for c in ap.coberturas):
            alerta("info", "Cobertura 'Lado A' não identificada explicitamente.")

        self.trace.add(self.nome, "Normalização e checagens", t0, f"{len(alertas)} alerta(s)")
        return ap, alertas
