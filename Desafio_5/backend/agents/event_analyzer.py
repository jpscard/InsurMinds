"""
Agente Analisador de Eventos Climáticos.

Responsável por classificar eventos meteorológicos por tipo e severidade,
determinando quais são relevantes para notificação de segurados.
"""

from __future__ import annotations

import logging
import re

from backend.config import (
    FROST_THRESHOLD_C,
    HEAT_THRESHOLD_C,
    RAIN_THRESHOLD_MM,
    WIND_THRESHOLD_KMH,
)
from backend.models.weather import EventType, Severity, WeatherEvent, WeatherForecast

logger = logging.getLogger(__name__)


# ─── Mapeamento de palavras-chave para tipos de evento ──────
EVENT_KEYWORDS: dict[EventType, list[str]] = {
    EventType.CHUVA_INTENSA: [
        "chuva", "precipitação", "alagamento", "inundação", "enchente",
    ],
    EventType.GRANIZO: [
        "granizo", "gelo", "saraiva",
    ],
    EventType.VENTO_FORTE: [
        "vento", "ventania", "rajada", "ciclone",
    ],
    EventType.TEMPESTADE: [
        "tempestade", "temporal", "tormenta",
    ],
    EventType.ONDA_CALOR: [
        "calor", "temperatura elevada", "onda de calor",
    ],
    EventType.GEADA: [
        "geada", "frio", "temperatura baixa", "neve", "congelamento",
    ],
    EventType.RAIOS: [
        "raio", "descarga elétrica", "relâmpago", "trovoada",
    ],
}

# ─── Mapeamento de severidade INMET para nosso sistema ──────
INMET_SEVERITY_MAP: dict[str, Severity] = {
    "Perigo Potencial": Severity.MEDIA,
    "Perigo": Severity.ALTA,
    "Grande Perigo": Severity.CRITICA,
}


class EventAnalyzerAgent:
    """
    Agente 2: Análise e classificação de eventos climáticos.

    Responsabilidades:
    - Classificar eventos por tipo (chuva, granizo, vento, etc.)
    - Atribuir nível de severidade
    - Filtrar apenas eventos relevantes para notificação
    """

    def __init__(self):
        self.name = "Agente Analisador"

    def analyze_events(self, events: list[WeatherEvent]) -> list[WeatherEvent]:
        """
        Analisa e enriquece uma lista de eventos meteorológicos.
        Retorna apenas os eventos considerados relevantes.
        """
        analyzed: list[WeatherEvent] = []

        for event in events:
            enriched = self._classify_event(event)
            if enriched and self._is_relevant(enriched):
                analyzed.append(enriched)

        logger.info(
            f"[{self.name}] {len(analyzed)}/{len(events)} eventos classificados como relevantes"
        )
        return analyzed

    def analyze_forecasts(
        self, forecasts: list[WeatherForecast]
    ) -> list[WeatherEvent]:
        """
        Converte previsões do OpenWeatherMap em eventos quando relevantes.
        """
        events: list[WeatherEvent] = []

        for forecast in forecasts:
            event = self._forecast_to_event(forecast)
            if event and self._is_relevant(event):
                events.append(event)

        return events

    def _classify_event(self, event: WeatherEvent) -> WeatherEvent:
        """Classifica o tipo e a severidade de um evento."""
        # Classificar tipo de evento
        event.event_type = self._detect_event_type(event)

        # Classificar severidade
        event.severity = self._detect_severity(event)

        return event

    def _detect_event_type(self, event: WeatherEvent) -> EventType:
        """Detecta o tipo de evento com base em palavras-chave."""
        text = f"{event.title} {event.description}".lower()
        risks_text = " ".join(event.risks).lower() if event.risks else ""
        full_text = f"{text} {risks_text}"

        # Verificar cada tipo de evento por palavras-chave
        scores: dict[EventType, int] = {}
        for event_type, keywords in EVENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in full_text)
            if score > 0:
                scores[event_type] = score

        if not scores:
            return EventType.DESCONHECIDO

        # Priorizar tempestade se múltiplos tipos detectados
        if EventType.TEMPESTADE in scores and len(scores) > 1:
            return EventType.TEMPESTADE

        # Retornar o tipo com maior pontuação
        return max(scores, key=scores.get)

    def _detect_severity(self, event: WeatherEvent) -> Severity:
        """Detecta a severidade do evento."""
        # Para eventos INMET, usar o mapeamento direto
        if event.source == "inmet" and event.raw_data:
            inmet_severity = event.raw_data.get("severidade", "")
            if inmet_severity in INMET_SEVERITY_MAP:
                return INMET_SEVERITY_MAP[inmet_severity]

        # Análise por texto para outras fontes
        text = f"{event.title} {event.description}".lower()

        if any(word in text for word in ["grande perigo", "extremo", "crítico"]):
            return Severity.CRITICA
        if any(word in text for word in ["perigo", "severo", "intenso"]):
            return Severity.ALTA
        if any(word in text for word in ["potencial", "moderado", "atenção"]):
            return Severity.MEDIA

        return Severity.BAIXA

    def _forecast_to_event(self, forecast: WeatherForecast) -> WeatherEvent | None:
        """Converte uma previsão em um evento se for relevante."""
        event_type = EventType.DESCONHECIDO
        severity = Severity.BAIXA
        risks: list[str] = []

        # Verificar condições de alerta
        if forecast.rain_mm >= RAIN_THRESHOLD_MM:
            event_type = EventType.CHUVA_INTENSA
            severity = Severity.MEDIA if forecast.rain_mm < 50 else Severity.ALTA
            risks.append(f"Chuva prevista de {forecast.rain_mm:.1f}mm em 3h")

        if forecast.has_storm:
            event_type = EventType.TEMPESTADE
            severity = Severity.ALTA
            risks.append("Tempestade com possibilidade de raios e granizo")

        if forecast.wind_speed_kmh >= WIND_THRESHOLD_KMH:
            if event_type == EventType.DESCONHECIDO:
                event_type = EventType.VENTO_FORTE
            severity = max(severity, Severity.MEDIA)
            risks.append(f"Ventos de {forecast.wind_speed_kmh:.0f} km/h")

        if forecast.temperature >= HEAT_THRESHOLD_C:
            event_type = EventType.ONDA_CALOR
            severity = Severity.MEDIA
            risks.append(f"Temperatura de {forecast.temperature:.1f}°C")

        if forecast.temperature <= FROST_THRESHOLD_C:
            event_type = EventType.GEADA
            severity = Severity.MEDIA
            risks.append(f"Temperatura de {forecast.temperature:.1f}°C — risco de geada")

        if event_type == EventType.DESCONHECIDO:
            return None

        ft = forecast.forecast_time
        return WeatherEvent(
            id=f"owm_{forecast.city}_{ft.strftime('%Y%m%d%H%M') if ft else 'now'}",
            source="openweathermap",
            event_type=event_type,
            severity=severity,
            title=f"Previsão: {event_type.value.replace('_', ' ').title()} em {forecast.city}",
            description=f"{forecast.weather_description.capitalize()}. {'; '.join(risks)}",
            risks=risks,
            affected_cities=[forecast.city],
            affected_states=[forecast.state] if forecast.state else [],
            start_time=forecast.forecast_time,
        )

    def _is_relevant(self, event: WeatherEvent) -> bool:
        """Determina se um evento é relevante para notificação."""
        # Eventos desconhecidos não são relevantes
        if event.event_type == EventType.DESCONHECIDO:
            return False

        # Todos os eventos com severidade média ou superior são relevantes
        if event.severity in (Severity.MEDIA, Severity.ALTA, Severity.CRITICA):
            return True

        # Eventos específicos de alta relevância mesmo com severidade baixa
        if event.event_type in (EventType.GRANIZO, EventType.TEMPESTADE):
            return True

        return False
