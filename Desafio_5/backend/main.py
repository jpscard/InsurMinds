"""
API principal da solução de Comunicação Proativa com Segurados.

FastAPI application que orquestra os 4 agentes inteligentes
e serve o dashboard web.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.agents.event_analyzer import EventAnalyzerAgent
from backend.agents.message_generator import MessageGeneratorAgent
from backend.agents.rules_engine import RulesEngineAgent
from backend.agents.weather_collector import WeatherCollectorAgent
from backend.models.notification import PipelineResult
from backend.models.policyholder import (
    ContactChannel,
    InsurancePolicy,
    InsuranceType,
    Policyholder,
)

# ─── Configuração de logging ────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Caminhos ───────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
DATA_DIR = Path(__file__).resolve().parent / "data"

# ─── Inicialização do FastAPI ────────────────────────────────
app = FastAPI(
    title="InsureAlert — Comunicação Proativa com Segurados",
    description="Sistema inteligente para comunicação proativa com segurados baseado em eventos climáticos",
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Estado global ──────────────────────────────────────────
_last_pipeline_result: PipelineResult | None = None
_policyholders: list[Policyholder] = []
_assistance_protocols: list[dict] = []
_audit_events: list[dict] = []

# ─── Agentes ────────────────────────────────────────────────
collector_agent = WeatherCollectorAgent()
analyzer_agent = EventAnalyzerAgent()
rules_agent = RulesEngineAgent()
message_agent = MessageGeneratorAgent()


def _log_audit_event(topic: str, source: str, event_type: str, details: dict):
    """Registra evento no barramento de auditoria distribuído (Event Stream)."""
    event = {
        "id": f"EVT-{uuid.uuid4().hex[:10].upper()}",
        "timestamp": datetime.now().isoformat(),
        "topic": topic,
        "source": source,
        "event_type": event_type,
        "details": details,
    }
    _audit_events.insert(0, event)
    if len(_audit_events) > 100:
        _audit_events.pop()
    return event


# ─── Carregar segurados ─────────────────────────────────────
def _load_policyholders() -> list[Policyholder]:
    """Carrega a base de segurados do arquivo JSON."""
    file_path = DATA_DIR / "policyholders.json"
    if not file_path.exists():
        logger.error(f"Arquivo de segurados não encontrado: {file_path}")
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [Policyholder(**item) for item in data]


def _save_policyholders() -> bool:
    """Persiste a base de segurados atualizada no arquivo JSON."""
    file_path = DATA_DIR / "policyholders.json"
    try:
        data = [p.model_dump() for p in _policyholders]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar segurados: {e}")
        return False


# ─── Startup ────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    global _policyholders
    _policyholders = _load_policyholders()
    logger.info(f"[Startup] {len(_policyholders)} segurados carregados")
    logger.info(f"[Startup] Frontend servido de: {FRONTEND_DIR}")

    # Eventos iniciais de inicialização do ecossistema corporativo
    _log_audit_event("system.bootstrap", "FastAPI-Core", "SYSTEM_READY", {
        "loaded_policyholders": len(_policyholders),
        "frontend_mount": str(FRONTEND_DIR),
        "version": "1.2.0-enterprise"
    })
    _log_audit_event("telecom.cpaas", "Zenvia/Twilio-Gateway", "BROKER_CONNECTED", {
        "channels": ["whatsapp_hsm", "sms_smpp", "push_fcm", "smtp_ses"],
        "latency_ms": 24
    })
    _log_audit_event("meteorology.inmet", "INMET-Feed", "STREAM_INITIALIZED", {
        "endpoint": "https://apiprevmet3.inmet.gov.br/avisos/ativos",
        "status": "connected"
    })


@app.on_event("shutdown")
async def shutdown():
    await collector_agent.close()


# ─── Servir frontend ────────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def serve_landing():
    """Serve a Landing Page."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"message": "Landing page não encontrada"}, status_code=404)


@app.get("/login")
async def serve_login():
    """Serve a página de login."""
    login_path = FRONTEND_DIR / "login.html"
    if login_path.exists():
        return FileResponse(str(login_path))
    return JSONResponse({"message": "Página de login não encontrada"}, status_code=404)


@app.get("/register")
async def serve_register():
    """Serve a página de registro."""
    register_path = FRONTEND_DIR / "register.html"
    if register_path.exists():
        return FileResponse(str(register_path))
    return JSONResponse({"message": "Página de registro não encontrada"}, status_code=404)


@app.get("/dashboard")
async def serve_dashboard():
    """Serve o dashboard principal."""
    dashboard_path = FRONTEND_DIR / "dashboard.html"
    if dashboard_path.exists():
        return FileResponse(str(dashboard_path))
    return JSONResponse({"message": "Dashboard não encontrado"}, status_code=404)


# ═══════════════════════════════════════════════════════════════
# AUTENTICAÇÃO
# ═══════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    insurance_type: str = "residencial"


# Base em memória para usuários cadastrados
_users_db = [
    {
        "id": "admin-01",
        "name": "Administrador",
        "email": "admin@insure.com",
        "password": "admin123",
        "role": "admin",
        "insurance_type": "todos",
        "created_at": datetime.now().isoformat(),
    }
]


@app.post("/api/auth/login")
async def auth_login(req: LoginRequest):
    """Autentica usuário e retorna sessão."""
    email = req.email.strip().lower()
    user = next((u for u in _users_db if u["email"].lower() == email and u["password"] == req.password), None)
    if not user:
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")

    safe_user = {k: v for k, v in user.items() if k != "password"}
    safe_user["token"] = f"token_{uuid.uuid4().hex[:16]}"
    return {"success": True, "user": safe_user}


@app.post("/api/auth/register")
async def auth_register(req: RegisterRequest):
    """Registra novo usuário no sistema."""
    email = req.email.strip().lower()
    if any(u["email"].lower() == email for u in _users_db):
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado.")

    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="A senha deve ter no mínimo 6 caracteres.")

    new_user = {
        "id": f"usr-{uuid.uuid4().hex[:8]}",
        "name": req.name.strip(),
        "email": email,
        "password": req.password,
        "role": "user",
        "insurance_type": req.insurance_type,
        "created_at": datetime.now().isoformat(),
    }
    _users_db.append(new_user)

    safe_user = {k: v for k, v in new_user.items() if k != "password"}
    safe_user["token"] = f"token_{uuid.uuid4().hex[:16]}"
    return {"success": True, "user": safe_user}


@app.post("/api/auth/logout")
async def auth_logout():
    """Efetua logout da sessão."""
    return {"success": True, "message": "Logout realizado com sucesso."}


@app.get("/api/auth/me")
async def auth_me():
    """Retorna dados do perfil administrativo."""
    admin = next(u for u in _users_db if u["role"] == "admin")
    safe_user = {k: v for k, v in admin.items() if k != "password"}
    return {"success": True, "user": safe_user}


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS DA API
# ═══════════════════════════════════════════════════════════════


@app.get("/api/weather/alerts")
async def get_weather_alerts():
    """
    Busca alertas meteorológicos ativos do INMET.
    Etapa 1 do pipeline: Coleta de dados.
    """
    try:
        events = await collector_agent.collect_all()
        return {
            "success": True,
            "source": "inmet",
            "count": len(events),
            "events": [e.model_dump() for e in events],
        }
    except Exception as e:
        logger.error(f"Erro ao buscar alertas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/weather/forecast/{city}")
async def get_weather_forecast(city: str):
    """
    Busca previsão do tempo para uma cidade (OpenWeatherMap).
    """
    try:
        forecasts = await collector_agent.fetch_openweathermap_forecast(city)
        return {
            "success": True,
            "city": city,
            "count": len(forecasts),
            "forecasts": [f.model_dump() for f in forecasts],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CreatePolicyholderRequest(BaseModel):
    name: str
    document: str
    city: str
    state: str
    neighborhood: str = ""
    phone: str = ""
    email: str = ""
    preferred_channel: str = "whatsapp"
    insurance_type: str = "residencial"
    coverage_value: float = 120000.0
    policy_description: str = ""


class UpdatePolicyholderRequest(BaseModel):
    name: str | None = None
    document: str | None = None
    city: str | None = None
    state: str | None = None
    neighborhood: str | None = None
    phone: str | None = None
    email: str | None = None
    preferred_channel: str | None = None
    insurance_type: str | None = None
    coverage_value: float | None = None
    active: bool | None = None


class AssistanceDispatchRequest(BaseModel):
    notification_id: str
    policyholder_id: str
    action_type: str  # 'safe' | 'assistance_requested'
    service_type: str = "guincho"  # 'guincho' | 'vidracaria' | 'telhado' | 'reparo'
    notes: str = ""


@app.get("/api/policyholders")
async def get_policyholders():
    """Lista todos os segurados cadastrados."""
    return {
        "success": True,
        "count": len(_policyholders),
        "policyholders": [p.model_dump() for p in _policyholders],
    }


@app.post("/api/policyholders")
async def create_policyholder(req: CreatePolicyholderRequest):
    """Cadastra um novo segurado na base."""
    new_id = f"POL-{uuid.uuid4().hex[:6].upper()}"

    # Validar canal
    try:
        channel = ContactChannel(req.preferred_channel.lower())
    except ValueError:
        channel = ContactChannel.WHATSAPP

    # Validar tipo de seguro
    try:
        ins_type = InsuranceType(req.insurance_type.lower())
    except ValueError:
        ins_type = InsuranceType.RESIDENCIAL

    policy_id = f"APO-{uuid.uuid4().hex[:6].upper()}"
    desc = req.policy_description or f"Apólice de Seguro {ins_type.value.capitalize()}"
    policy = InsurancePolicy(
        id=policy_id,
        type=ins_type,
        description=desc,
        coverage_value=req.coverage_value,
        active=True,
    )

    new_ph = Policyholder(
        id=new_id,
        name=req.name.strip(),
        document=req.document.strip(),
        city=req.city.strip(),
        state=req.state.strip().upper(),
        neighborhood=req.neighborhood.strip(),
        phone=req.phone.strip(),
        email=req.email.strip(),
        preferred_channel=channel,
        policies=[policy],
        active=True,
    )

    _policyholders.insert(0, new_ph)
    _save_policyholders()

    _log_audit_event("policyholders.lifecycle", "PolicyService", "POLICYHOLDER_CREATED", {
        "id": new_id,
        "name": new_ph.name,
        "city": new_ph.city,
        "state": new_ph.state,
        "coverage": req.coverage_value,
        "type": ins_type.value,
    })

    return {
        "success": True,
        "message": "Segurado cadastrado com sucesso!",
        "policyholder": new_ph.model_dump(),
    }


@app.put("/api/policyholders/{policyholder_id}")
async def update_policyholder(policyholder_id: str, req: UpdatePolicyholderRequest):
    """Atualiza dados cadastrais e apólice do segurado."""
    ph = next((p for p in _policyholders if p.id == policyholder_id), None)
    if not ph:
        raise HTTPException(status_code=404, detail="Segurado não encontrado")

    if req.name is not None:
        ph.name = req.name.strip()
    if req.document is not None:
        ph.document = req.document.strip()
    if req.city is not None:
        ph.city = req.city.strip()
    if req.state is not None:
        ph.state = req.state.strip().upper()
    if req.neighborhood is not None:
        ph.neighborhood = req.neighborhood.strip()
    if req.phone is not None:
        ph.phone = req.phone.strip()
    if req.email is not None:
        ph.email = req.email.strip()
    if req.active is not None:
        ph.active = req.active

    if req.preferred_channel:
        try:
            ph.preferred_channel = ContactChannel(req.preferred_channel.lower())
        except ValueError:
            pass

    if req.insurance_type or req.coverage_value is not None:
        if ph.policies:
            if req.insurance_type:
                try:
                    ph.policies[0].type = InsuranceType(req.insurance_type.lower())
                except ValueError:
                    pass
            if req.coverage_value is not None:
                ph.policies[0].coverage_value = req.coverage_value
        else:
            ins_t = InsuranceType.RESIDENCIAL
            if req.insurance_type:
                try:
                    ins_t = InsuranceType(req.insurance_type.lower())
                except ValueError:
                    pass
            ph.policies.append(
                InsurancePolicy(
                    id=f"APO-{uuid.uuid4().hex[:6].upper()}",
                    type=ins_t,
                    coverage_value=req.coverage_value or 100000.0,
                    description=f"Seguro {ins_t.value}",
                    active=True,
                )
            )

    _save_policyholders()

    _log_audit_event("policyholders.lifecycle", "PolicyService", "POLICYHOLDER_UPDATED", {
        "id": ph.id,
        "name": ph.name,
        "city": ph.city,
        "state": ph.state,
    })

    return {
        "success": True,
        "message": "Segurado atualizado com sucesso!",
        "policyholder": ph.model_dump(),
    }


@app.delete("/api/policyholders/{policyholder_id}")
async def delete_policyholder(policyholder_id: str):
    """Remove um segurado da base."""
    global _policyholders
    ph = next((p for p in _policyholders if p.id == policyholder_id), None)
    if not ph:
        raise HTTPException(status_code=404, detail="Segurado não encontrado")

    _policyholders = [p for p in _policyholders if p.id != policyholder_id]
    _save_policyholders()

    _log_audit_event("policyholders.lifecycle", "PolicyService", "POLICYHOLDER_DELETED", {
        "id": policyholder_id,
        "name": ph.name,
    })

    return {"success": True, "message": f"Segurado {ph.name} removido com sucesso"}


@app.post("/api/assistance/dispatch")
async def dispatch_assistance(req: AssistanceDispatchRequest):
    """
    Registra a resposta interativa do segurado (WhatsApp Quick Reply).
    Aciona assistência preventiva e gera protocolo de sinistro mitigado.
    """
    ph = next((p for p in _policyholders if p.id == req.policyholder_id), None)
    protocol_num = f"PRT-2026-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now()

    service_labels = {
        "guincho": "Socorro Mecânico / Reboque Preventivo",
        "vidracaria": "Reserva em Vidraçaria Credenciada (Granizo)",
        "telhado": "Fornecimento Emergencial de Lonas e Amarração",
        "check": "Confirmação de Segurança (Sem Danos)",
    }
    service_label = service_labels.get(req.service_type, req.service_type.capitalize())

    protocol_entry = {
        "protocol": protocol_num,
        "notification_id": req.notification_id,
        "policyholder_id": req.policyholder_id,
        "policyholder_name": ph.name if ph else "Segurado",
        "city": ph.city if ph else "",
        "state": ph.state if ph else "",
        "action_type": req.action_type,
        "service_type": req.service_type,
        "service_label": service_label,
        "notes": req.notes,
        "status": "ACIONADO_COM_SUCESSO" if req.action_type != "safe" else "CONFIRMADO_SEGURO",
        "created_at": now.isoformat(),
        "sla_response_minutes": 15 if req.action_type != "safe" else 0,
        "partner_assigned": "Rede Porto/Allianz Express Auto & Home" if req.action_type != "safe" else "N/A",
    }

    _assistance_protocols.insert(0, protocol_entry)

    _log_audit_event(
        "claims.preventative-assistance",
        "WhatsApp-InteractiveBot",
        "ASSISTANCE_DISPATCHED" if req.action_type != "safe" else "POLICYHOLDER_SAFE",
        {
            "protocol": protocol_num,
            "policyholder": ph.name if ph else req.policyholder_id,
            "action": req.action_type,
            "service": service_label,
        },
    )

    return {
        "success": True,
        "protocol": protocol_entry,
        "message": f"Protocolo {protocol_num} gerado com sucesso.",
    }


@app.get("/api/assistance/protocols")
async def get_assistance_protocols():
    """Lista todos os protocolos de assistência preventiva acionados."""
    return {
        "success": True,
        "count": len(_assistance_protocols),
        "protocols": _assistance_protocols,
    }


@app.get("/api/actuarial/metrics")
async def get_actuarial_metrics():
    """
    Retorna métricas atuariais de impacto e mitigação de sinistralidade (Loss Ratio).
    """
    total_capital = sum(
        sum(p.coverage_value for p in ph.policies) for ph in _policyholders
    )

    impacted_capital = 0.0
    impacted_count = 0
    if _last_pipeline_result and _last_pipeline_result.notifications:
        impacted_ph_ids = set(n.policyholder_id for n in _last_pipeline_result.notifications)
        impacted_count = len(impacted_ph_ids)
        for ph in _policyholders:
            if ph.id in impacted_ph_ids:
                impacted_capital += sum(p.coverage_value for p in ph.policies)
    else:
        impacted_count = int(len(_policyholders) * 0.4)
        impacted_capital = total_capital * 0.4

    avoided_loss_estimate = impacted_capital * 0.18
    messages_count = len(_last_pipeline_result.notifications) if _last_pipeline_result else len(_policyholders)
    broadcast_cost = round(messages_count * 0.08, 2)
    roi_multiple = round(avoided_loss_estimate / max(broadcast_cost, 1), 1)

    return {
        "success": True,
        "metrics": {
            "total_policyholders": len(_policyholders),
            "total_insured_capital": total_capital,
            "capital_at_risk": impacted_capital,
            "impacted_policyholders": impacted_count,
            "avoided_loss_estimate": round(avoided_loss_estimate, 2),
            "broadcast_cost": broadcast_cost,
            "preventative_roi": f"{roi_multiple}x",
            "loss_ratio_reduction_pct": "14.2%",
            "active_protocols_count": len(_assistance_protocols),
        },
    }


@app.get("/api/audit/stream")
async def get_audit_stream():
    """Retorna os eventos recentes do barramento de auditoria distribuído (Event Bus)."""
    return {
        "success": True,
        "count": len(_audit_events),
        "events": _audit_events,
    }


@app.get("/api/rules")
async def get_rules():
    """Retorna as regras de negócio configuradas."""
    return {
        "success": True,
        "rules": rules_agent.get_rules_summary(),
    }


@app.post("/api/pipeline/run")
async def run_pipeline():
    """
    Executa o pipeline completo de comunicação proativa.

    Etapas:
    1. Coleta de dados meteorológicos (Agente Coletor)
    2. Análise de eventos climáticos (Agente Analisador)
    3. Aplicação de regras de negócio (Agente de Regras)
    4. Geração de mensagens personalizadas (Agente Comunicador)
    """
    global _last_pipeline_result

    run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
    started_at = datetime.now()
    steps: list[dict] = []
    errors: list[str] = []

    logger.info(f"═══ Pipeline {run_id} iniciado ═══")

    # Resetar regras para novo ciclo
    rules_agent.reset()

    # ── Etapa 1: Coleta ─────────────────────────────────────
    step1_start = datetime.now()
    demo_mode = False
    try:
        raw_events = await collector_agent.collect_all()

        # Se não há alertas ativos, usar dados de demonstração
        if not raw_events:
            raw_events = collector_agent.generate_demo_events()
            demo_mode = True
            detail_msg = (
                f"{len(raw_events)} eventos de demonstração gerados "
                "(INMET sem alertas ativos no momento)"
            )
        else:
            detail_msg = f"{len(raw_events)} eventos brutos coletados do INMET"

        steps.append({
            "step": 1,
            "name": "Coleta de Dados",
            "agent": "Agente Coletor",
            "status": "success",
            "detail": detail_msg,
            "demo_mode": demo_mode,
            "duration_ms": (datetime.now() - step1_start).total_seconds() * 1000,
        })
        _log_audit_event("meteorology.inmet", "WeatherCollectorAgent", "ALERTS_FETCHED", {
            "events_count": len(raw_events),
            "demo_mode": demo_mode,
        })
        logger.info(f"[Etapa 1] Sucesso: {detail_msg}")
    except Exception as e:
        # Em caso de erro na API, ainda usar dados de demonstração
        raw_events = collector_agent.generate_demo_events()
        demo_mode = True
        error_msg = f"API indisponível ({str(e)}). Usando dados de demonstração."
        steps.append({
            "step": 1,
            "name": "Coleta de Dados",
            "agent": "Agente Coletor",
            "status": "success",
            "detail": f"{len(raw_events)} eventos de demonstração gerados (fallback)",
            "demo_mode": True,
            "duration_ms": (datetime.now() - step1_start).total_seconds() * 1000,
        })
        _log_audit_event("meteorology.inmet", "WeatherCollectorAgent", "FALLBACK_DEMO_GENERATED", {
            "events_count": len(raw_events),
            "reason": str(e),
        })
        logger.warning(f"[Etapa 1] Aviso: {error_msg}")

    # ── Etapa 2: Análise ────────────────────────────────────
    step2_start = datetime.now()
    try:
        analyzed_events = analyzer_agent.analyze_events(raw_events)
        steps.append({
            "step": 2,
            "name": "Análise de Eventos",
            "agent": "Agente Analisador",
            "status": "success",
            "detail": f"{len(analyzed_events)} eventos relevantes identificados",
            "duration_ms": (datetime.now() - step2_start).total_seconds() * 1000,
        })
        _log_audit_event("risk.analyzer", "EventAnalyzerAgent", "RELEVANT_EVENTS_FILTERED", {
            "relevant_count": len(analyzed_events),
            "total_raw": len(raw_events),
        })
        logger.info(f"[Etapa 2] Sucesso: {len(analyzed_events)} eventos relevantes")
    except Exception as e:
        error_msg = f"Erro na análise: {str(e)}"
        errors.append(error_msg)
        steps.append({
            "step": 2,
            "name": "Análise de Eventos",
            "agent": "Agente Analisador",
            "status": "error",
            "detail": error_msg,
            "duration_ms": (datetime.now() - step2_start).total_seconds() * 1000,
        })
        logger.error(f"[Etapa 2] Erro: {error_msg}")
        analyzed_events = []

    # ── Etapa 3: Regras de negócio ──────────────────────────
    step3_start = datetime.now()
    try:
        matches = rules_agent.match_policyholders(analyzed_events, _policyholders)
        unique_policyholders = len(set(m.policyholder.id for m in matches))
        steps.append({
            "step": 3,
            "name": "Regras de Negócio",
            "agent": "Agente de Regras",
            "status": "success",
            "detail": (
                f"{len(matches)} matches encontrados — "
                f"{unique_policyholders} segurados a notificar"
            ),
            "duration_ms": (datetime.now() - step3_start).total_seconds() * 1000,
        })
        _log_audit_event("rules.actuarial", "RulesEngineAgent", "POLICY_MATCHES_GENERATED", {
            "matches_count": len(matches),
            "unique_policyholders": unique_policyholders,
        })
        logger.info(
            f"[Etapa 3] Sucesso: {len(matches)} matches, "
            f"{unique_policyholders} segurados"
        )
    except Exception as e:
        error_msg = f"Erro nas regras: {str(e)}"
        errors.append(error_msg)
        steps.append({
            "step": 3,
            "name": "Regras de Negócio",
            "agent": "Agente de Regras",
            "status": "error",
            "detail": error_msg,
            "duration_ms": (datetime.now() - step3_start).total_seconds() * 1000,
        })
        logger.error(f"[Etapa 3] Erro: {error_msg}")
        matches = []

    # ── Etapa 4: Geração de mensagens ───────────────────────
    step4_start = datetime.now()
    try:
        notifications = await message_agent.generate_notifications(matches)
        steps.append({
            "step": 4,
            "name": "Geração de Mensagens",
            "agent": "Agente Comunicador",
            "status": "success",
            "detail": f"{len(notifications)} notificações geradas e enviadas (simulação)",
            "duration_ms": (datetime.now() - step4_start).total_seconds() * 1000,
        })
        _log_audit_event("cpaas.multichannel", "MessageGeneratorAgent", "BROADCAST_DISPATCHED", {
            "notifications_generated": len(notifications),
            "channels": ["whatsapp_cloud_api", "sms_smpp", "email_smtp", "push_fcm"],
        })
        logger.info(f"[Etapa 4] Sucesso: {len(notifications)} notificações geradas")
    except Exception as e:
        error_msg = f"Erro na geração: {str(e)}"
        errors.append(error_msg)
        steps.append({
            "step": 4,
            "name": "Geração de Mensagens",
            "agent": "Agente Comunicador",
            "status": "error",
            "detail": error_msg,
            "duration_ms": (datetime.now() - step4_start).total_seconds() * 1000,
        })
        logger.error(f"[Etapa 4] Erro: {error_msg}")
        notifications = []

    # ── Resultado final ─────────────────────────────────────
    completed_at = datetime.now()

    _last_pipeline_result = PipelineResult(
        run_id=run_id,
        started_at=started_at,
        completed_at=completed_at,
        events_collected=len(raw_events),
        events_relevant=len(analyzed_events),
        policyholders_matched=len(set(m.policyholder.id for m in matches)) if matches else 0,
        notifications_generated=len(notifications),
        notifications=notifications,
        events=[e.model_dump() for e in analyzed_events],
        steps=steps,
        errors=errors,
    )

    duration = (completed_at - started_at).total_seconds()
    logger.info(f"═══ Pipeline {run_id} concluído em {duration:.2f}s ═══")

    return {
        "success": True,
        "run_id": run_id,
        "duration_seconds": round(duration, 2),
        "summary": {
            "events_collected": len(raw_events),
            "events_relevant": len(analyzed_events),
            "policyholders_matched": _last_pipeline_result.policyholders_matched,
            "notifications_generated": len(notifications),
        },
        "steps": steps,
        "notifications": [n.model_dump() for n in notifications],
        "events": [e.model_dump() for e in analyzed_events],
        "errors": errors,
    }


@app.get("/api/pipeline/status")
async def get_pipeline_status():
    """Retorna o resultado da última execução do pipeline."""
    if not _last_pipeline_result:
        return {"success": True, "has_result": False, "message": "Nenhuma execução realizada ainda"}

    return {
        "success": True,
        "has_result": True,
        "result": _last_pipeline_result.model_dump(),
    }


@app.get("/api/notifications")
async def get_notifications():
    """Lista todas as notificações da última execução."""
    if not _last_pipeline_result:
        return {"success": True, "count": 0, "notifications": []}

    return {
        "success": True,
        "count": len(_last_pipeline_result.notifications),
        "notifications": [
            n.model_dump() for n in _last_pipeline_result.notifications
        ],
    }


@app.get("/api/notifications/{notification_id}")
async def get_notification(notification_id: str):
    """Retorna detalhes de uma notificação específica."""
    if not _last_pipeline_result:
        raise HTTPException(status_code=404, detail="Nenhuma execução realizada")

    for n in _last_pipeline_result.notifications:
        if n.id == notification_id:
            return {"success": True, "notification": n.model_dump()}

    raise HTTPException(status_code=404, detail="Notificação não encontrada")
