"""
Configurações centrais do sistema.
Carrega variáveis de ambiente e define constantes.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── API Keys ───────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "")

# ─── URLs das APIs externas ─────────────────────────────────
INMET_BASE_URL = "https://apiprevmet3.inmet.gov.br"
OPENWEATHERMAP_BASE_URL = "https://api.openweathermap.org/data/2.5"

# ─── Limiares de severidade ─────────────────────────────────
# Chuva em mm/h para considerar intensa
RAIN_THRESHOLD_MM = 20.0
# Velocidade do vento em km/h para considerar forte
WIND_THRESHOLD_KMH = 50.0
# Temperatura mínima em °C para alerta de geada
FROST_THRESHOLD_C = 3.0
# Temperatura máxima em °C para alerta de onda de calor
HEAT_THRESHOLD_C = 38.0

# ─── Configurações do sistema ───────────────────────────────
# Tempo mínimo entre notificações para o mesmo segurado/evento (em segundos)
NOTIFICATION_COOLDOWN_SECONDS = 6 * 60 * 60  # 6 horas

# ─── Modelo Gemini ──────────────────────────────────────────
GEMINI_MODEL = "gemini-2.0-flash"

# ─── Mapeamento de estados brasileiros ──────────────────────
ESTADOS_BR = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal",
    "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
    "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco",
    "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima",
    "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe",
    "TO": "Tocantins",
}
