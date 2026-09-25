"""Modelo de dados canônico de uma apólice D&O.

Este esquema é o "contrato" entre os agentes: o Agente de Extração produz
objetos `ApoliceDO`, o repositório os persiste e o Agente de Comparação os
consome. Todos os campos são opcionais porque apólices reais omitem ou
redigem informações de formas muito diferentes.
"""
from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field


class Valor(BaseModel):
    """Valor monetário. `valor` é numérico (quando identificável); `texto` guarda a redação original."""

    valor: float | None = Field(None, description="Valor numérico, sem separadores de milhar")
    moeda: str | None = Field("BRL", description="Código ISO da moeda, ex.: BRL, USD")
    texto: str | None = Field(None, description="Redação original, ex.: 'R$ 10.000.000,00 por reclamação'")


class Cobertura(BaseModel):
    nome: str = Field(..., description="Nome da cobertura, ex.: 'Custos de Defesa'")
    categoria: Literal[
        "Lado A", "Lado B", "Lado C", "Custos de Defesa", "Extensão", "Adicional", "Outra"
    ] = "Outra"
    descricao: str | None = None
    limite: Valor | None = Field(None, description="Limite ou sublimite específico da cobertura")
    franquia: Valor | None = Field(None, description="Franquia/retenção específica desta cobertura")
    trecho_fonte: str | None = Field(None, description="Trecho curto do documento que sustenta a informação")


class Exclusao(BaseModel):
    titulo: str
    categoria: Literal[
        "Conduta dolosa/fraude", "Danos corporais/materiais", "Ambiental", "Reclamações prévias",
        "Segurado vs. Segurado", "Multas e penalidades", "Trabalhista", "Contratual", "Outra",
    ] = "Outra"
    descricao: str | None = None
    trecho_fonte: str | None = None


class Franquia(BaseModel):
    aplicacao: str = Field(..., description="A que se aplica, ex.: 'Lado B', 'Reclamações trabalhistas'")
    valor: Valor | None = None


class Identificacao(BaseModel):
    seguradora: str | None = None
    numero_apolice: str | None = None
    produto: str | None = None
    processo_susep: str | None = None
    tomador: str | None = Field(None, description="Tomador/Sociedade contratante")
    cnpj_tomador: str | None = None
    corretor: str | None = None
    vigencia_inicio: str | None = Field(None, description="Data no formato AAAA-MM-DD")
    vigencia_fim: str | None = Field(None, description="Data no formato AAAA-MM-DD")


class ApoliceDO(BaseModel):
    identificacao: Identificacao = Field(default_factory=Identificacao)
    limite_maximo_garantia: Valor | None = Field(None, description="LMG / limite agregado da apólice")
    premio_total: Valor | None = None
    base_cobertura: str | None = Field(None, description="Ex.: 'à base de reclamações (claims made)'")
    data_retroatividade: str | None = Field(None, description="AAAA-MM-DD ou texto (ex.: 'ilimitada')")
    prazo_complementar: str | None = Field(None, description="Prazo complementar/suplementar para notificação")
    territorialidade: str | None = None
    segurados: list[str] = Field(default_factory=list, description="Quem é considerado segurado")
    custos_defesa: str | None = Field(None, description="Como os custos de defesa são tratados (dentro/fora do LMG, adiantamento)")
    coberturas: list[Cobertura] = Field(default_factory=list)
    exclusoes: list[Exclusao] = Field(default_factory=list)
    franquias: list[Franquia] = Field(default_factory=list)
    clausulas_relevantes: list[str] = Field(default_factory=list, description="Outras cláusulas notáveis (alocação, ordem de pagamento etc.)")
    observacoes: str | None = None

    @classmethod
    def json_schema_str(cls) -> str:
        return json.dumps(cls.model_json_schema(), ensure_ascii=False, indent=1)
