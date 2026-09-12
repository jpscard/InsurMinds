"""
Modelos de dados de notificações.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .policyholder import ContactChannel, InsuranceType
from .weather import EventType, Severity


class NotificationStatus(str, Enum):
    """Status de envio da notificação."""
    PENDENTE = "pendente"
    ENVIADA = "enviada"
    FALHA = "falha"


class Notification(BaseModel):
    """Notificação gerada para um segurado."""
    id: str
    policyholder_id: str
    policyholder_name: str
    event_id: str
    event_type: EventType
    severity: Severity
    insurance_type: InsuranceType
    channel: ContactChannel
    subject: str = ""
    message: str = ""
    short_message: str = ""
    recommendations: list[str] = Field(default_factory=list)
    status: NotificationStatus = NotificationStatus.PENDENTE
    created_at: datetime = Field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    city: str = ""
    state: str = ""

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class PipelineResult(BaseModel):
    """Resultado completo de uma execução do pipeline."""
    run_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    events_collected: int = 0
    events_relevant: int = 0
    policyholders_matched: int = 0
    notifications_generated: int = 0
    notifications: list[Notification] = Field(default_factory=list)
    events: list[dict] = Field(default_factory=list)
    steps: list[dict] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}
