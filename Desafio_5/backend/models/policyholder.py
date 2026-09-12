"""
Modelos de dados de segurados e apólices.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class InsuranceType(str, Enum):
    """Tipos de seguro oferecidos."""
    RESIDENCIAL = "residencial"
    AUTOMOVEL = "automovel"
    VIDA = "vida"
    EMPRESARIAL = "empresarial"
    AGRO = "agro"


class ContactChannel(str, Enum):
    """Canais de comunicação disponíveis."""
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    WHATSAPP = "whatsapp"


class InsurancePolicy(BaseModel):
    """Apólice de seguro de um segurado."""
    id: str
    type: InsuranceType
    description: str = ""
    coverage_value: float = 0.0
    active: bool = True


class Policyholder(BaseModel):
    """Segurado com suas informações pessoais e apólices."""
    id: str
    name: str
    document: str = Field(description="CPF ou CNPJ mascarado")
    city: str
    state: str = Field(description="Sigla do estado (ex: SP, PR)")
    neighborhood: str = ""
    phone: str = ""
    email: str = ""
    preferred_channel: ContactChannel = ContactChannel.SMS
    policies: list[InsurancePolicy] = Field(default_factory=list)
    active: bool = True

    @property
    def insurance_types(self) -> list[InsuranceType]:
        """Retorna os tipos de seguro ativos do segurado."""
        return [p.type for p in self.policies if p.active]

    @property
    def display_name(self) -> str:
        """Nome de exibição (primeiro nome)."""
        return self.name.split()[0] if self.name else "Segurado"
