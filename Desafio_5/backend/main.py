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
from pydantic import BaseModel

from backend.agents.event_analyzer import EventAnalyzerAgent
from backend.agents.message_generator import MessageGeneratorAgent
from backend.agents.rules_engine import RulesEngineAgent
from backend.agents.weather_collector import WeatherCollectorAgent
from backend.models.notification import PipelineResult
from backend.models.policyholder import Policyholder

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
    version="1.0.0",
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

# ─── Agentes ────────────────────────────────────────────────
collector_agent = WeatherCollectorAgent()
analyzer_agent = EventAnalyzerAgent()
rules_agent = RulesEngineAgent()
message_agent = MessageGeneratorAgent()


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


# ─── Startup ────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    global _policyholders
    _policyholders = _load_policyholders()
    logger.info(f"✅ {len(_policyholders)} segurados carregados")
    logger.info(f"✅ Frontend servido de: {FRONTEND_DIR}")


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


@app.get("/api/policyholders")
async def get_policyholders():
    """Lista todos os segurados cadastrados."""
    return {
        "success": True,
        "count": len(_policyholders),
        "policyholders": [p.model_dump() for p in _policyholders],
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
        logger.info(f"[Etapa 1] ✅ {detail_msg}")
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
        logger.warning(f"[Etapa 1] ⚠️ {error_msg}")

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
        logger.info(f"[Etapa 2] ✅ {len(analyzed_events)} eventos relevantes")
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
        logger.error(f"[Etapa 2] ❌ {error_msg}")
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
        logger.info(
            f"[Etapa 3] ✅ {len(matches)} matches, "
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
        logger.error(f"[Etapa 3] ❌ {error_msg}")
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
        logger.info(f"[Etapa 4] ✅ {len(notifications)} notificações geradas")
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
        logger.error(f"[Etapa 4] ❌ {error_msg}")
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
