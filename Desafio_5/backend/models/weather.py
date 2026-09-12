"""
Modelos de dados meteorológicos.
Representam eventos, alertas e previsões de forma normalizada.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Tipos de eventos climáticos monitorados."""
    CHUVA_INTENSA = "chuva_intensa"
    GRANIZO = "granizo"
    VENTO_FORTE = "vento_forte"
    TEMPESTADE = "tempestade"
    ONDA_CALOR = "onda_calor"
    GEADA = "geada"
    RAIOS = "raios"
    SECA = "seca"
    DESCONHECIDO = "desconhecido"


class Severity(str, Enum):
    """Níveis de severidade dos eventos."""
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class WeatherEvent(BaseModel):
    """Evento meteorológico normalizado, independente da fonte."""
    id: str
    source: str = Field(description="Fonte do dado: 'inmet' ou 'openweathermap'")
    event_type: EventType = EventType.DESCONHECIDO
    severity: Severity = Severity.BAIXA
    title: str = ""
    description: str = ""
    risks: list[str] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)
    affected_states: list[str] = Field(default_factory=list)
    affected_cities: list[str] = Field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    raw_data: Optional[dict] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class WeatherForecast(BaseModel):
    """Previsão do tempo para uma cidade (via OpenWeatherMap)."""
    city: str
    state: str = ""
    country: str = "BR"
    temperature: float = 0.0
    feels_like: float = 0.0
    humidity: int = 0
    wind_speed_kmh: float = 0.0
    rain_mm: float = 0.0
    weather_main: str = ""
    weather_description: str = ""
    forecast_time: Optional[datetime] = None

    @property
    def has_rain(self) -> bool:
        return self.rain_mm > 0 or "rain" in self.weather_main.lower()

    @property
    def has_storm(self) -> bool:
        return "thunderstorm" in self.weather_main.lower()
