"""
Agente Gerador de Mensagens Personalizadas.

Utiliza IA Generativa (Google Gemini) para criar mensagens
personalizadas para cada segurado com base no evento climático.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from backend.config import GEMINI_API_KEY, GEMINI_MODEL
from backend.models.notification import Notification, NotificationStatus
from backend.models.policyholder import ContactChannel, InsuranceType
from backend.models.weather import EventType, Severity
from backend.agents.rules_engine import NotificationMatch

logger = logging.getLogger(__name__)


# ─── Templates de fallback (quando IA não está disponível) ──
FALLBACK_TEMPLATES: dict[EventType, dict[str, str]] = {
    EventType.CHUVA_INTENSA: {
        "subject": "Alerta: Chuva Intensa na sua região",
        "message": (
            "Prezado(a) {name},\n\n"
            "O Instituto Nacional de Meteorologia (INMET) emitiu um alerta de "
            "chuva intensa para a região de {city}/{state}.\n\n"
            "Como titular de um seguro {insurance_type}, recomendamos:\n"
            "• Evite estacionar veículos em áreas de alagamento\n"
            "• Verifique calhas e ralos da sua residência\n"
            "• Mantenha documentos e objetos de valor em locais elevados\n"
            "• Em caso de emergência, ligue para a Defesa Civil (199)\n\n"
            "Estamos aqui para ajudar. Sua segurança é nossa prioridade.\n\n"
            "Atenciosamente,\nSua Seguradora"
        ),
        "short": "Alerta: Chuva intensa prevista em {city}. Proteja seu {insurance_type}. Evite áreas de alagamento. Defesa Civil: 199",
    },
    EventType.GRANIZO: {
        "subject": "Alerta: Granizo — Proteja seu patrimônio",
        "message": (
            "Prezado(a) {name},\n\n"
            "Há previsão de granizo para a região de {city}/{state}.\n\n"
            "Para proteger seu {insurance_type}:\n"
            "• Estacione seu veículo em local coberto\n"
            "• Recolha objetos soltos em áreas externas\n"
            "• Evite sair de casa durante a precipitação\n"
            "• Afaste-se de janelas de vidro\n\n"
            "Sua segurança é nossa prioridade.\n\n"
            "Atenciosamente,\nSua Seguradora"
        ),
        "short": "Alerta: Granizo previsto em {city}. Proteja seu veículo em local coberto. Evite áreas externas.",
    },
    EventType.VENTO_FORTE: {
        "subject": "Alerta: Ventos Fortes na sua região",
        "message": (
            "Prezado(a) {name},\n\n"
            "Ventos fortes são esperados para a região de {city}/{state}.\n\n"
            "Recomendações para seu {insurance_type}:\n"
            "• Feche janelas e portas com segurança\n"
            "• Não se abrigue debaixo de árvores\n"
            "• Recolha objetos que possam ser arrastados\n"
            "• Evite uso de aparelhos eletrônicos ligados à tomada\n\n"
            "Atenciosamente,\nSua Seguradora"
        ),
        "short": "Alerta: Ventos fortes em {city}. Feche janelas, recolha objetos externos. Defesa Civil: 199",
    },
    EventType.TEMPESTADE: {
        "subject": "Alerta: Tempestade — Ação preventiva recomendada",
        "message": (
            "Prezado(a) {name},\n\n"
            "Uma tempestade está prevista para {city}/{state}.\n\n"
            "Medidas preventivas para seu {insurance_type}:\n"
            "• Busque abrigo seguro imediatamente\n"
            "• Estacione veículos em locais cobertos\n"
            "• Desligue aparelhos eletrônicos da tomada\n"
            "• Evite contato com objetos metálicos\n"
            "• Em caso de emergência: Bombeiros (193), Defesa Civil (199)\n\n"
            "Atenciosamente,\nSua Seguradora"
        ),
        "short": "Alerta: Tempestade em {city}. Busque abrigo seguro. Bombeiros: 193, Defesa Civil: 199",
    },
    EventType.ONDA_CALOR: {
        "subject": "Alerta: Onda de Calor — Cuide da sua saúde",
        "message": (
            "Prezado(a) {name},\n\n"
            "Uma onda de calor está afetando a região de {city}/{state}.\n\n"
            "Recomendações:\n"
            "• Mantenha-se hidratado(a)\n"
            "• Evite exposição ao sol entre 10h e 16h\n"
            "• Use protetor solar\n"
            "• Fique atento(a) a sinais de insolação\n\n"
            "Sua saúde é nossa prioridade.\n\n"
            "Atenciosamente,\nSua Seguradora"
        ),
        "short": "Alerta: Calor extremo em {city}. Hidrate-se e evite sol entre 10h-16h.",
    },
    EventType.GEADA: {
        "subject": "Alerta: Geada — Proteja suas plantações",
        "message": (
            "Prezado(a) {name},\n\n"
            "Há risco de geada na região de {city}/{state}.\n\n"
            "Recomendações para seu {insurance_type}:\n"
            "• Proteja plantações sensíveis ao frio\n"
            "• Verifique sistemas de aquecimento\n"
            "• Proteja tubulações expostas contra congelamento\n"
            "• Mantenha animais em abrigos adequados\n\n"
            "Atenciosamente,\nSua Seguradora"
        ),
        "short": "Alerta: Geada prevista em {city}. Proteja plantações e tubulações. Verifique aquecimento.",
    },
}

# Fallback genérico
DEFAULT_TEMPLATE = {
    "subject": "Alerta Meteorológico para sua região",
    "message": (
        "Prezado(a) {name},\n\n"
        "Um alerta meteorológico foi emitido para a região de {city}/{state}.\n\n"
        "Recomendamos atenção e medidas preventivas.\n"
        "Em caso de emergência, ligue para a Defesa Civil (199).\n\n"
        "Atenciosamente,\nSua Seguradora"
    ),
    "short": "Alerta meteorológico em {city}. Tome medidas preventivas. Defesa Civil: 199",
}


# ─── Nomes amigáveis para tipos de seguro ───────────────────
INSURANCE_TYPE_NAMES: dict[InsuranceType, str] = {
    InsuranceType.RESIDENCIAL: "seguro residencial",
    InsuranceType.AUTOMOVEL: "seguro automóvel",
    InsuranceType.VIDA: "seguro de vida",
    InsuranceType.EMPRESARIAL: "seguro empresarial",
    InsuranceType.AGRO: "seguro agrícola",
}


class MessageGeneratorAgent:
    """
    Agente 4: Geração de mensagens personalizadas.

    Utiliza Google Gemini para gerar mensagens contextualizadas,
    com fallback para templates pré-definidos quando a IA não está disponível.
    """

    def __init__(self):
        self.name = "Agente Comunicador"
        self._gemini_model = None
        self._init_gemini()

    def _init_gemini(self):
        """Inicializa o modelo Gemini se a API key estiver disponível."""
        if not GEMINI_API_KEY:
            logger.warning(
                f"[{self.name}] Gemini API key não configurada. "
                "Usando templates de fallback."
            )
            return

        try:
            import google.generativeai as genai

            genai.configure(api_key=GEMINI_API_KEY)
            self._gemini_model = genai.GenerativeModel(GEMINI_MODEL)
            logger.info(f"[{self.name}] Gemini inicializado com modelo {GEMINI_MODEL}")
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao inicializar Gemini: {e}")
            self._gemini_model = None

    async def generate_notifications(
        self, matches: list[NotificationMatch]
    ) -> list[Notification]:
        """Gera notificações personalizadas para cada match."""
        notifications: list[Notification] = []

        for match in matches:
            try:
                notification = await self._generate_single(match)
                notifications.append(notification)
            except Exception as e:
                logger.error(
                    f"[{self.name}] Erro ao gerar notificação para "
                    f"{match.policyholder.name}: {e}"
                )

        logger.info(
            f"[{self.name}] {len(notifications)} notificações geradas"
        )
        return notifications

    async def _generate_single(self, match: NotificationMatch) -> Notification:
        """Gera uma única notificação para um match."""
        ph = match.policyholder
        event = match.event
        ins_type = match.insurance_type
        ins_name = INSURANCE_TYPE_NAMES.get(ins_type, ins_type.value)

        # Tentar geração com IA primeiro
        if self._gemini_model:
            try:
                subject, message, short_msg, recommendations = await self._generate_with_ai(
                    match, ins_name
                )
            except Exception as e:
                logger.warning(
                    f"[{self.name}] Fallback para template após erro Gemini: {e}"
                )
                subject, message, short_msg, recommendations = self._generate_with_template(
                    match, ins_name
                )
        else:
            subject, message, short_msg, recommendations = self._generate_with_template(
                match, ins_name
            )

        # Simular envio
        now = datetime.now()

        return Notification(
            id=f"NTF-{uuid.uuid4().hex[:8].upper()}",
            policyholder_id=ph.id,
            policyholder_name=ph.name,
            event_id=event.id,
            event_type=event.event_type,
            severity=event.severity,
            insurance_type=ins_type,
            channel=ph.preferred_channel,
            subject=subject,
            message=message,
            short_message=short_msg,
            recommendations=recommendations,
            status=NotificationStatus.ENVIADA,
            created_at=now,
            sent_at=now,
            city=ph.city,
            state=ph.state,
        )

    async def _generate_with_ai(
        self, match: NotificationMatch, ins_name: str
    ) -> tuple[str, str, str, list[str]]:
        """Gera mensagem usando Google Gemini."""
        ph = match.policyholder
        event = match.event

        prompt = f"""Você é um assistente de comunicação de uma seguradora brasileira.
Gere uma mensagem de alerta preventivo personalizada para um segurado.

CONTEXTO DO EVENTO:
- Tipo: {event.event_type.value.replace('_', ' ').title()}
- Título: {event.title}
- Descrição: {event.description}
- Severidade: {event.severity.value.upper()}
- Riscos: {'; '.join(event.risks) if event.risks else 'Não especificados'}
- Instruções oficiais: {'; '.join(event.instructions) if event.instructions else 'Não disponíveis'}

CONTEXTO DO SEGURADO:
- Nome: {ph.display_name}
- Cidade: {ph.city}/{ph.state}
- Tipo de seguro: {ins_name}
- Canal de comunicação: {ph.preferred_channel.value}

INSTRUÇÕES:
1. Gere um assunto/título curto e impactante (max 60 caracteres)
2. Gere uma mensagem completa e empática em português brasileiro
3. Gere uma versão curta da mensagem (max 160 caracteres, formato SMS)
4. Liste 3-5 recomendações práticas específicas para o tipo de seguro
5. NÃO utilize emojis em nenhuma parte do texto (mantenha padrão corporativo formal)

FORMATO DE RESPOSTA (use exatamente estas tags):
<ASSUNTO>título aqui</ASSUNTO>
<MENSAGEM>mensagem completa aqui</MENSAGEM>
<SMS>mensagem curta aqui</SMS>
<RECOMENDACOES>
- recomendação 1
- recomendação 2
- recomendação 3
</RECOMENDACOES>"""

        response = self._gemini_model.generate_content(prompt)
        text = response.text

        # Parsear resposta
        subject = self._extract_tag(text, "ASSUNTO") or f"Alerta para {ph.city}"
        message = self._extract_tag(text, "MENSAGEM") or ""
        short_msg = self._extract_tag(text, "SMS") or ""
        recs_text = self._extract_tag(text, "RECOMENDACOES") or ""

        recommendations = [
            line.strip().lstrip("- •").strip()
            for line in recs_text.split("\n")
            if line.strip() and line.strip() != "-"
        ]

        return subject, message, short_msg, recommendations

    def _generate_with_template(
        self, match: NotificationMatch, ins_name: str
    ) -> tuple[str, str, str, list[str]]:
        """Gera mensagem usando templates de fallback."""
        ph = match.policyholder
        event = match.event

        template = FALLBACK_TEMPLATES.get(event.event_type, DEFAULT_TEMPLATE)

        format_vars = {
            "name": ph.display_name,
            "city": ph.city,
            "state": ph.state,
            "insurance_type": ins_name,
        }

        subject = template["subject"]
        message = template["message"].format(**format_vars)
        short_msg = template["short"].format(**format_vars)

        # Extrair recomendações do template (linhas com •)
        recommendations = [
            line.strip().lstrip("• ").strip()
            for line in message.split("\n")
            if line.strip().startswith("•")
        ]

        return subject, message, short_msg, recommendations

    @staticmethod
    def _extract_tag(text: str, tag: str) -> Optional[str]:
        """Extrai conteúdo entre tags XML da resposta do Gemini."""
        import re

        pattern = f"<{tag}>(.*?)</{tag}>"
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else None
