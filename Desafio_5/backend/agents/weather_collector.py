"""
Agente Coletor de Dados Meteorológicos.

Responsável por consultar APIs externas (INMET e OpenWeatherMap)
e normalizar os dados em um formato unificado.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import httpx

from backend.config import (
    INMET_BASE_URL,
    OPENWEATHERMAP_API_KEY,
    OPENWEATHERMAP_BASE_URL,
)
from backend.models.weather import WeatherEvent, WeatherForecast

logger = logging.getLogger(__name__)


class WeatherCollectorAgent:
    """
    Agente 1: Coleta de dados meteorológicos de fontes externas.

    Fontes suportadas:
    - INMET (Instituto Nacional de Meteorologia): Alertas ativos no Brasil
    - OpenWeatherMap: Previsão do tempo por cidade (requer API key)
    """

    def __init__(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }
        self.client = httpx.AsyncClient(timeout=30.0, headers=headers, verify=False)
        self.name = "Agente Coletor"

    async def collect_all(self) -> list[WeatherEvent]:
        """Coleta dados de todas as fontes disponíveis."""
        events: list[WeatherEvent] = []

        # 1. Coletar alertas do INMET (sempre disponível, sem API key)
        try:
            inmet_events = await self.fetch_inmet_alerts()
            events.extend(inmet_events)
            logger.info(f"[{self.name}] {len(inmet_events)} alertas coletados do INMET")
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao coletar INMET: {e}")

        return events

    async def fetch_inmet_alerts(self) -> list[WeatherEvent]:
        """
        Consulta a API do INMET para obter alertas meteorológicos ativos.
        Endpoint: /avisos/ativos
        """
        url = f"{INMET_BASE_URL}/avisos/ativos"
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()

        events: list[WeatherEvent] = []

        # A resposta do INMET possui chaves "hoje", "futuro" e "amanha"
        for period_key in ["hoje", "futuro", "amanha"]:
            alerts = data.get(period_key, [])
            if not isinstance(alerts, list):
                continue

            for alert in alerts:
                event = self._parse_inmet_alert(alert, period_key)
                if event:
                    events.append(event)

        return events

    def _parse_inmet_alert(self, alert: dict, period: str) -> Optional[WeatherEvent]:
        """Converte um alerta do INMET em um WeatherEvent normalizado."""
        try:
            alert_id = str(alert.get("id", ""))
            description = alert.get("descricao", "")
            severity_text = alert.get("severidade", "")
            risks = alert.get("riscos", [])
            instructions = alert.get("instrucoes", [])
            states_str = alert.get("estados", "")
            cities_str = alert.get("municipios", "")

            # Extrair estados como lista
            affected_states = [
                s.strip() for s in states_str.split(",") if s.strip()
            ] if states_str else []

            # Extrair nomes de cidades (formato: "Cidade - UF (código)")
            affected_cities = []
            if cities_str:
                for entry in cities_str.split(",")[:50]:  # Limitar a 50 cidades
                    city_name = entry.strip().split(" - ")[0].strip()
                    if city_name:
                        affected_cities.append(city_name)

            # Parsear datas
            start_time = None
            end_time = None
            try:
                inicio = alert.get("inicio", "")
                fim = alert.get("fim", "")
                if inicio:
                    start_time = datetime.strptime(inicio, "%Y-%m-%d %H:%M")
                if fim:
                    end_time = datetime.strptime(fim, "%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                pass

            return WeatherEvent(
                id=f"inmet_{alert_id}",
                source="inmet",
                title=f"Alerta INMET: {description}",
                description=f"Severidade: {severity_text}. {'; '.join(risks) if risks else ''}",
                risks=risks if isinstance(risks, list) else [],
                instructions=instructions if isinstance(instructions, list) else [],
                affected_states=affected_states,
                affected_cities=affected_cities,
                start_time=start_time,
                end_time=end_time,
                raw_data=alert,
            )
        except Exception as e:
            logger.warning(f"[{self.name}] Erro ao parsear alerta INMET: {e}")
            return None

    async def fetch_openweathermap_forecast(
        self, city: str, country: str = "BR"
    ) -> list[WeatherForecast]:
        """
        Consulta a API do OpenWeatherMap para previsão de 5 dias.
        Requer OPENWEATHERMAP_API_KEY configurada.
        """
        if not OPENWEATHERMAP_API_KEY:
            logger.warning(f"[{self.name}] OpenWeatherMap API key não configurada")
            return []

        url = f"{OPENWEATHERMAP_BASE_URL}/forecast"
        params = {
            "q": f"{city},{country}",
            "appid": OPENWEATHERMAP_API_KEY,
            "units": "metric",
            "lang": "pt_br",
            "cnt": 8,  # Próximas 24h (intervalos de 3h)
        }

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"[{self.name}] Erro OpenWeatherMap para {city}: {e}")
            return []

        forecasts: list[WeatherForecast] = []
        for item in data.get("list", []):
            try:
                weather_info = item.get("weather", [{}])[0]
                rain_data = item.get("rain", {})
                wind_data = item.get("wind", {})
                main_data = item.get("main", {})

                forecast = WeatherForecast(
                    city=city,
                    country=country,
                    temperature=main_data.get("temp", 0),
                    feels_like=main_data.get("feels_like", 0),
                    humidity=main_data.get("humidity", 0),
                    wind_speed_kmh=wind_data.get("speed", 0) * 3.6,
                    rain_mm=rain_data.get("3h", 0),
                    weather_main=weather_info.get("main", ""),
                    weather_description=weather_info.get("description", ""),
                    forecast_time=datetime.fromtimestamp(item.get("dt", 0)),
                )
                forecasts.append(forecast)
            except Exception as e:
                logger.warning(f"[{self.name}] Erro ao parsear forecast: {e}")

        return forecasts

    def generate_demo_events(self) -> list[WeatherEvent]:
        """
        Gera eventos de demonstração para quando não há alertas ativos.
        Simula cenários realistas para fins de apresentação do MVP.
        """
        now = datetime.now()
        logger.info(f"[{self.name}] Gerando eventos de demonstração")

        return [
            WeatherEvent(
                id="demo_001",
                source="inmet",
                title="Alerta INMET: Tempestade",
                description="Severidade: Perigo Potencial. Chuva entre 20 e 30 mm/h ou até 50 mm/dia, ventos intensos (40-60 km/h), e queda de granizo.",
                risks=[
                    "Chuva entre 20 e 30 mm/h ou até 50 mm/dia, ventos intensos (40-60 km/h), e queda de granizo.",
                    "Baixo risco de corte de energia elétrica, estragos em plantações, queda de galhos de árvores e de alagamentos.",
                ],
                instructions=[
                    "Em caso de rajadas de vento: não se abrigue debaixo de árvores.",
                    "Evite usar aparelhos eletrônicos ligados à tomada.",
                    "Obtenha mais informações junto à Defesa Civil (telefone 199).",
                ],
                affected_states=["Paraná", "Santa Catarina", "Rio Grande do Sul", "São Paulo"],
                affected_cities=[
                    "Curitiba", "Londrina", "Maringá", "Cascavel", "Ponta Grossa",
                    "Guarapuava", "Foz do Iguaçu", "Florianópolis", "Joinville",
                    "Blumenau", "Chapecó", "Criciúma", "Porto Alegre", "Caxias do Sul",
                    "São Paulo", "Guarulhos", "Campinas", "Santos", "Sorocaba",
                ],
                start_time=now,
                end_time=None,
                raw_data={"severidade": "Perigo Potencial", "descricao": "Tempestade"},
            ),
            WeatherEvent(
                id="demo_002",
                source="inmet",
                title="Alerta INMET: Chuva Intensa",
                description="Severidade: Perigo. Chuva entre 30 e 60 mm/h ou 50 e 100 mm/dia. Risco de alagamentos, deslizamentos e transbordamento de rios.",
                risks=[
                    "Chuva entre 30 e 60 mm/h ou 50 e 100 mm/dia.",
                    "Risco de alagamentos, deslizamentos de encostas e transbordamento de rios.",
                    "Risco de corte de energia elétrica e queda de árvores.",
                ],
                instructions=[
                    "Evite áreas de alagamento e não dirija em ruas inundadas.",
                    "Se possível, desligue aparelhos elétricos e o quadro geral de energia.",
                    "Ligue para Defesa Civil (199) ou Bombeiros (193) em caso de emergência.",
                ],
                affected_states=["Minas Gerais", "São Paulo"],
                affected_cities=[
                    "Belo Horizonte", "São Paulo", "Guarulhos", "Campinas", "Sorocaba",
                ],
                start_time=now,
                end_time=None,
                raw_data={"severidade": "Perigo", "descricao": "Chuva Intensa"},
            ),
            WeatherEvent(
                id="demo_003",
                source="inmet",
                title="Alerta INMET: Geada",
                description="Severidade: Perigo Potencial. Temperatura mínima prevista de -2°C a 3°C. Risco de danos a plantações sensíveis ao frio.",
                risks=[
                    "Temperatura mínima prevista de -2°C a 3°C.",
                    "Formação de geada em áreas agrícolas.",
                    "Risco de danos a plantações sensíveis ao frio.",
                ],
                instructions=[
                    "Proteja plantações sensíveis com cobertura adequada.",
                    "Mantenha animais em abrigos.",
                    "Evite exposição prolongada ao frio.",
                ],
                affected_states=["Paraná", "Santa Catarina", "Rio Grande do Sul"],
                affected_cities=[
                    "Guarapuava", "Ponta Grossa", "Curitiba",
                    "Caxias do Sul", "Chapecó",
                ],
                start_time=now,
                end_time=None,
                raw_data={"severidade": "Perigo Potencial", "descricao": "Geada"},
            ),
        ]

    async def close(self):
        """Fecha o cliente HTTP."""
        await self.client.aclose()
