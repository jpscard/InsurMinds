"""
Orquestrador do Pipeline Multi-Agente em Python Puro.

Executa a esteira sequencial dos 4 agentes autônomos de forma desacoplada,
sem dependência de frameworks externos pesados (como LangChain ou CrewAI),
utilizando exclusivamente Programação Orientada a Objetos e tipagem com Pydantic.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Callable

from backend.agents.event_analyzer import EventAnalyzerAgent
from backend.agents.message_generator import MessageGeneratorAgent
from backend.agents.rules_engine import RulesEngineAgent
from backend.agents.weather_collector import WeatherCollectorAgent
from backend.models.notification import PipelineResult, Notification
from backend.models.policyholder import Policyholder
from backend.models.weather import WeatherEvent

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orquestrador determinístico em Python puro para o pipeline multi-agente.
    
    Etapas coordenadas:
    1. Agente Coletor (WeatherCollectorAgent): Coleta meteorológica externa (INMET + contingência).
    2. Agente Analisador (EventAnalyzerAgent): Análise semântica, classificação e criticidade.
    3. Agente de Regras (RulesEngineAgent): Cruzamento geográfico, coberturas e scoring atuarial.
    4. Agente Comunicador (MessageGeneratorAgent): Síntese de mensagens com Gemini / fallback corporativo.
    """

    def __init__(
        self,
        collector: WeatherCollectorAgent | None = None,
        analyzer: EventAnalyzerAgent | None = None,
        rules_engine: RulesEngineAgent | None = None,
        message_generator: MessageGeneratorAgent | None = None,
    ):
        self.collector = collector or WeatherCollectorAgent()
        self.analyzer = analyzer or EventAnalyzerAgent()
        self.rules_engine = rules_engine or RulesEngineAgent()
        self.message_generator = message_generator or MessageGeneratorAgent()

    async def run(
        self,
        policyholders: list[Policyholder],
        audit_callback: Callable[[str, str, str, dict], None] | None = None,
    ) -> PipelineResult:
        """
        Executa o pipeline completo de ponta a ponta em Python puro.
        """
        run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
        started_at = datetime.now()
        steps: list[dict] = []
        errors: list[str] = []

        logger.info(f"═══ [PipelineOrchestrator] {run_id} iniciado ═══")
        self.rules_engine.reset()

        def log_audit(topic: str, source: str, event_type: str, details: dict):
            if audit_callback:
                audit_callback(topic, source, event_type, details)

        # ── Etapa 1: Coleta Meteorológica (Agente 1) ─────────────────
        step1_start = datetime.now()
        demo_mode = False
        try:
            raw_events = await self.collector.collect_all()
            if not raw_events:
                raw_events = self.collector.generate_demo_events()
                demo_mode = True
                detail = f"{len(raw_events)} eventos de demonstração gerados (INMET sem alertas ativos)"
            else:
                detail = f"{len(raw_events)} eventos brutos coletados do INMET"

            duration_ms = (datetime.now() - step1_start).total_seconds() * 1000
            steps.append({
                "step": 1,
                "name": "Coleta de Dados",
                "agent": "Agente Coletor",
                "status": "success",
                "detail": detail,
                "demo_mode": demo_mode,
                "duration_ms": round(duration_ms, 2),
            })
            log_audit("meteorology.inmet", "WeatherCollectorAgent", "ALERTS_FETCHED", {
                "events_count": len(raw_events),
                "demo_mode": demo_mode,
            })
        except Exception as e:
            raw_events = self.collector.generate_demo_events()
            demo_mode = True
            duration_ms = (datetime.now() - step1_start).total_seconds() * 1000
            steps.append({
                "step": 1,
                "name": "Coleta de Dados",
                "agent": "Agente Coletor",
                "status": "success",
                "detail": f"{len(raw_events)} eventos de demonstração gerados (fallback após erro: {e})",
                "demo_mode": True,
                "duration_ms": round(duration_ms, 2),
            })
            log_audit("meteorology.inmet", "WeatherCollectorAgent", "FALLBACK_DEMO_GENERATED", {
                "reason": str(e),
            })

        # ── Etapa 2: Análise Semântica (Agente 2) ─────────────────────
        step2_start = datetime.now()
        try:
            analyzed_events = self.analyzer.analyze_events(raw_events)
            duration_ms = (datetime.now() - step2_start).total_seconds() * 1000
            steps.append({
                "step": 2,
                "name": "Análise de Eventos",
                "agent": "Agente Analisador",
                "status": "success",
                "detail": f"{len(analyzed_events)} eventos relevantes identificados",
                "duration_ms": round(duration_ms, 2),
            })
            log_audit("risk.analyzer", "EventAnalyzerAgent", "RELEVANT_EVENTS_FILTERED", {
                "relevant_count": len(analyzed_events),
                "total_raw": len(raw_events),
            })
        except Exception as e:
            analyzed_events = raw_events
            err = f"Erro na análise: {e}"
            errors.append(err)
            duration_ms = (datetime.now() - step2_start).total_seconds() * 1000
            steps.append({
                "step": 2,
                "name": "Análise de Eventos",
                "agent": "Agente Analisador",
                "status": "warning",
                "detail": err,
                "duration_ms": round(duration_ms, 2),
            })

        # ── Etapa 3: Motor de Regras e Cruzamento Atuarial (Agente 3) ─
        step3_start = datetime.now()
        try:
            matches = self.rules_engine.match_policyholders(analyzed_events, policyholders)
            duration_ms = (datetime.now() - step3_start).total_seconds() * 1000
            steps.append({
                "step": 3,
                "name": "Regras de Negócio",
                "agent": "Agente de Regras",
                "status": "success",
                "detail": f"{len(matches)} correspondências segurado x evento geradas",
                "duration_ms": round(duration_ms, 2),
            })
            log_audit("rules.engine", "RulesEngineAgent", "MATCHES_GENERATED", {
                "matches_count": len(matches),
                "active_policyholders": len(policyholders),
            })
        except Exception as e:
            matches = []
            err = f"Erro no motor de regras: {e}"
            errors.append(err)
            duration_ms = (datetime.now() - step3_start).total_seconds() * 1000
            steps.append({
                "step": 3,
                "name": "Regras de Negócio",
                "agent": "Agente de Regras",
                "status": "error",
                "detail": err,
                "duration_ms": round(duration_ms, 2),
            })

        # ── Etapa 4: Geração de Mensagens com IA (Agente 4) ────────────
        step4_start = datetime.now()
        notifications: list[Notification] = []
        try:
            notifications = await self.message_generator.generate_notifications(matches)
            duration_ms = (datetime.now() - step4_start).total_seconds() * 1000
            steps.append({
                "step": 4,
                "name": "Geração de Mensagens",
                "agent": "Agente Comunicador",
                "status": "success",
                "detail": f"{len(notifications)} mensagens personalizadas geradas",
                "duration_ms": round(duration_ms, 2),
            })
            log_audit("notifications.dispatcher", "MessageGeneratorAgent", "NOTIFICATIONS_DISPATCHED", {
                "notifications_count": len(notifications),
                "ai_enabled": bool(self.message_generator._gemini_model),
            })
        except Exception as e:
            err = f"Erro na geração de mensagens: {e}"
            errors.append(err)
            duration_ms = (datetime.now() - step4_start).total_seconds() * 1000
            steps.append({
                "step": 4,
                "name": "Geração de Mensagens",
                "agent": "Agente Comunicador",
                "status": "error",
                "detail": err,
                "duration_ms": round(duration_ms, 2),
            })

        completed_at = datetime.now()
        result = PipelineResult(
            run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            events_collected=len(raw_events),
            events_relevant=len(analyzed_events),
            policyholders_matched=len(matches),
            notifications_generated=len(notifications),
            notifications=notifications,
            events=[e.model_dump() for e in analyzed_events],
            steps=steps,
            errors=errors,
        )

        logger.info(
            f"═══ [PipelineOrchestrator] Concluído em "
            f"{(completed_at - started_at).total_seconds():.2f}s "
            f"— {len(notifications)} notificações emitidas ═══"
        )
        return result


if __name__ == "__main__":
    import json
    from pathlib import Path

    print("--- Testando PipelineOrchestrator em Python Puro (CLI) ---")
    data_path = Path(__file__).resolve().parent.parent / "data" / "policyholders.json"
    with open(data_path, "r", encoding="utf-8") as f:
        ph_raw = json.load(f)
    sample_phs = [Policyholder.model_validate(p) for p in ph_raw]
    print(f"Segurados carregados: {len(sample_phs)}")

    orchestrator = PipelineOrchestrator()
    res = asyncio.run(orchestrator.run(sample_phs))
    print(f"\nResultado da Orquestração:")
    print(f"- Run ID: {res.run_id}")
    print(f"- Eventos coletados: {res.events_collected}")
    print(f"- Eventos relevantes: {res.events_relevant}")
    print(f"- Matches: {res.policyholders_matched}")
    print(f"- Notificações geradas: {res.notifications_generated}")
    for s in res.steps:
        print(f"  [{s['step']}] {s['name']} ({s['agent']}): {s['status']} - {s['detail']}")
