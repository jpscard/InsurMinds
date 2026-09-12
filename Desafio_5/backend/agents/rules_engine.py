"""
Agente de Regras de Negócio.

Responsável por cruzar eventos meteorológicos com a base de segurados
e determinar quais clientes devem receber notificações.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from backend.models.policyholder import InsuranceType, Policyholder
from backend.models.weather import EventType, Severity, WeatherEvent

logger = logging.getLogger(__name__)


@dataclass
class NotificationMatch:
    """Resultado do cruzamento entre evento e segurado."""
    policyholder: Policyholder
    event: WeatherEvent
    insurance_type: InsuranceType
    priority: int = 0  # Maior = mais urgente


# ─── Regras de mapeamento: Evento → Tipo de seguro afetado ─
EVENT_INSURANCE_RULES: dict[EventType, list[InsuranceType]] = {
    EventType.CHUVA_INTENSA: [
        InsuranceType.RESIDENCIAL,
        InsuranceType.AUTOMOVEL,
        InsuranceType.EMPRESARIAL,
    ],
    EventType.GRANIZO: [
        InsuranceType.AUTOMOVEL,
        InsuranceType.RESIDENCIAL,
        InsuranceType.AGRO,
    ],
    EventType.VENTO_FORTE: [
        InsuranceType.RESIDENCIAL,
        InsuranceType.EMPRESARIAL,
        InsuranceType.AGRO,
    ],
    EventType.TEMPESTADE: [
        InsuranceType.RESIDENCIAL,
        InsuranceType.AUTOMOVEL,
        InsuranceType.EMPRESARIAL,
        InsuranceType.AGRO,
        InsuranceType.VIDA,
    ],
    EventType.ONDA_CALOR: [
        InsuranceType.VIDA,
        InsuranceType.AGRO,
    ],
    EventType.GEADA: [
        InsuranceType.AGRO,
        InsuranceType.RESIDENCIAL,
    ],
    EventType.RAIOS: [
        InsuranceType.RESIDENCIAL,
        InsuranceType.EMPRESARIAL,
        InsuranceType.VIDA,
    ],
}

# ─── Prioridade por severidade ──────────────────────────────
SEVERITY_PRIORITY: dict[Severity, int] = {
    Severity.CRITICA: 100,
    Severity.ALTA: 75,
    Severity.MEDIA: 50,
    Severity.BAIXA: 25,
}

# ─── Prioridade extra por tipo de evento ────────────────────
EVENT_PRIORITY_BOOST: dict[EventType, int] = {
    EventType.TEMPESTADE: 20,
    EventType.GRANIZO: 15,
    EventType.CHUVA_INTENSA: 10,
    EventType.VENTO_FORTE: 10,
    EventType.GEADA: 5,
    EventType.ONDA_CALOR: 5,
    EventType.RAIOS: 5,
}


class RulesEngineAgent:
    """
    Agente 3: Motor de regras de negócio.

    Responsabilidades:
    - Cruzar eventos com segurados por localização e tipo de apólice
    - Aplicar regras de priorização
    - Evitar notificações duplicadas
    - Gerar lista de segurados a serem notificados
    """

    def __init__(self):
        self.name = "Agente de Regras"
        self._sent_notifications: set[str] = set()

    def match_policyholders(
        self,
        events: list[WeatherEvent],
        policyholders: list[Policyholder],
    ) -> list[NotificationMatch]:
        """
        Cruza eventos com segurados e retorna os matches para notificação.

        Regras aplicadas:
        1. O segurado deve estar em um estado afetado pelo evento
        2. O segurado deve ter uma apólice do tipo afetado pelo evento
        3. O segurado deve estar ativo
        4. Não pode haver notificação duplicada no mesmo ciclo
        """
        matches: list[NotificationMatch] = []

        for event in events:
            # Obter tipos de seguro afetados por este evento
            affected_insurance_types = EVENT_INSURANCE_RULES.get(
                event.event_type, []
            )
            if not affected_insurance_types:
                continue

            for policyholder in policyholders:
                if not policyholder.active:
                    continue

                # Verificar se o segurado está na região afetada
                if not self._is_in_affected_area(policyholder, event):
                    continue

                # Verificar cada tipo de apólice do segurado
                for policy in policyholder.policies:
                    if not policy.active:
                        continue

                    if policy.type not in affected_insurance_types:
                        continue

                    # Verificar duplicata
                    match_key = f"{policyholder.id}_{event.id}_{policy.type}"
                    if match_key in self._sent_notifications:
                        continue

                    # Calcular prioridade
                    priority = self._calculate_priority(event, policy.type)

                    match = NotificationMatch(
                        policyholder=policyholder,
                        event=event,
                        insurance_type=policy.type,
                        priority=priority,
                    )
                    matches.append(match)
                    self._sent_notifications.add(match_key)

        # Ordenar por prioridade (maior primeiro)
        matches.sort(key=lambda m: m.priority, reverse=True)

        logger.info(
            f"[{self.name}] {len(matches)} matches encontrados "
            f"({len(set(m.policyholder.id for m in matches))} segurados únicos)"
        )
        return matches

    def _is_in_affected_area(
        self, policyholder: Policyholder, event: WeatherEvent
    ) -> bool:
        """Verifica se o segurado está na área afetada pelo evento."""
        # Mapeamento de nome completo para sigla
        state_name_to_abbr = {
            "acre": "AC", "alagoas": "AL", "amapá": "AP", "amazonas": "AM",
            "bahia": "BA", "ceará": "CE", "distrito federal": "DF",
            "espírito santo": "ES", "goiás": "GO", "maranhão": "MA",
            "mato grosso": "MT", "mato grosso do sul": "MS",
            "minas gerais": "MG", "pará": "PA", "paraíba": "PB",
            "paraná": "PR", "pernambuco": "PE", "piauí": "PI",
            "rio de janeiro": "RJ", "rio grande do norte": "RN",
            "rio grande do sul": "RS", "rondônia": "RO", "roraima": "RR",
            "santa catarina": "SC", "são paulo": "SP", "sergipe": "SE",
            "tocantins": "TO",
        }

        # Verificar por estado
        if event.affected_states:
            ph_state = policyholder.state.strip().upper()
            for state in event.affected_states:
                state_clean = state.strip()
                # Comparar diretamente (sigla vs sigla)
                if ph_state == state_clean.upper():
                    return True
                # Converter nome completo para sigla e comparar
                abbr = state_name_to_abbr.get(state_clean.lower(), "")
                if abbr and ph_state == abbr:
                    return True

        # Verificar por cidade
        if event.affected_cities:
            ph_city = policyholder.city.lower().strip()
            for city in event.affected_cities:
                if ph_city == city.lower().strip():
                    return True

        return False

    def _calculate_priority(
        self, event: WeatherEvent, insurance_type: InsuranceType
    ) -> int:
        """Calcula a prioridade de uma notificação."""
        priority = SEVERITY_PRIORITY.get(event.severity, 0)
        priority += EVENT_PRIORITY_BOOST.get(event.event_type, 0)

        # Boost para tipos de seguro com maior exposição ao risco
        if event.event_type == EventType.GRANIZO and insurance_type == InsuranceType.AUTOMOVEL:
            priority += 10
        if event.event_type == EventType.CHUVA_INTENSA and insurance_type == InsuranceType.RESIDENCIAL:
            priority += 10
        if event.event_type == EventType.GEADA and insurance_type == InsuranceType.AGRO:
            priority += 10

        return priority

    def get_rules_summary(self) -> dict:
        """Retorna um resumo das regras de negócio aplicadas."""
        return {
            "event_insurance_mapping": {
                event_type.value: [it.value for it in insurance_types]
                for event_type, insurance_types in EVENT_INSURANCE_RULES.items()
            },
            "severity_levels": {s.value: p for s, p in SEVERITY_PRIORITY.items()},
            "total_notifications_sent": len(self._sent_notifications),
        }

    def reset(self):
        """Reseta o histórico de notificações enviadas."""
        self._sent_notifications.clear()
