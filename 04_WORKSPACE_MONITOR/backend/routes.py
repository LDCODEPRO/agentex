"""
AGENTE-X Cockpit | Rotas da API
Uma rota por necessidade de tela do frontend. Tudo protegido por sessao,
exceto /health e /api/login.
"""
import sys
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

import db
from auth import check_password, require_auth

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "03_RUNTIME"))
sys.path.insert(0, str(_ROOT / "01_CORE" / "orchestrator"))
sys.path.insert(0, str(_ROOT / "02_MEMORY" / "long_term"))
sys.path.insert(0, str(_ROOT / "10_GITHUB"))
sys.path.insert(0, str(_ROOT / "05_HEALTH"))

from maestro import Maestro  # noqa: E402

router = APIRouter()
_maestro = Maestro()


# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------

class LoginIn(BaseModel):
    password: str


@router.post("/api/login")
def login(body: LoginIn, request: Request):
    if not check_password(body.password):
        raise HTTPException(status_code=401, detail="Senha incorreta")
    request.session["authenticated"] = True
    return {"ok": True}


@router.post("/api/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/api/me")
def me(request: Request):
    return {"authenticated": bool(request.session.get("authenticated"))}


# ------------------------------------------------------------------
# Visao Geral
# ------------------------------------------------------------------

@router.get("/api/overview", dependencies=[Depends(require_auth)])
def api_overview():
    return db.overview()


@router.get("/api/activity", dependencies=[Depends(require_auth)])
def api_activity():
    return db.recent_activity()


@router.get("/api/health/system", dependencies=[Depends(require_auth)])
def api_system_health():
    return db.system_health()


# ------------------------------------------------------------------
# Chat
# ------------------------------------------------------------------

class ChatIn(BaseModel):
    message: str


@router.post("/api/chat", dependencies=[Depends(require_auth)])
def api_chat(body: ChatIn):
    if not body.message or not body.message.strip():
        raise HTTPException(status_code=400, detail="Mensagem vazia")
    t0 = time.time()
    result = _maestro.run_task(body.message, verbose=False, interactive=True, return_trace=True)
    elapsed = time.time() - t0
    if isinstance(result, str):
        # Excecao inesperada em run_task -- ainda assim devolve algo exibivel
        return {"final_answer": result, "thought": None, "action": None,
                "observation": None, "provider": None, "elapsed_s": round(elapsed, 1)}
    result["elapsed_s"] = round(elapsed, 1)
    return result


# ------------------------------------------------------------------
# Missoes
# ------------------------------------------------------------------

@router.get("/api/missions", dependencies=[Depends(require_auth)])
def api_missions(status: str = "all"):
    return db.list_missions(status=status)


# ------------------------------------------------------------------
# Fila
# ------------------------------------------------------------------

@router.get("/api/queue", dependencies=[Depends(require_auth)])
def api_queue():
    return db.queue_by_status()


# ------------------------------------------------------------------
# Cerebro / LLMs
# ------------------------------------------------------------------

@router.get("/api/brains", dependencies=[Depends(require_auth)])
def api_brains():
    return db.brain_usage()


# ------------------------------------------------------------------
# Memoria
# ------------------------------------------------------------------

@router.get("/api/memory/tabs", dependencies=[Depends(require_auth)])
def api_memory_tabs():
    return db.memory_tabs()


@router.get("/api/memory", dependencies=[Depends(require_auth)])
def api_memory(tab: str):
    return db.memory_items(tab)


# ------------------------------------------------------------------
# Logs
# ------------------------------------------------------------------

@router.get("/api/logs", dependencies=[Depends(require_auth)])
def api_logs(level: str = "ALL"):
    return db.logs(level=level)


# ------------------------------------------------------------------
# Seguranca
# ------------------------------------------------------------------

@router.get("/api/security/blocked", dependencies=[Depends(require_auth)])
def api_security_blocked():
    return db.blocked_actions()


# ------------------------------------------------------------------
# Financeiro
# ------------------------------------------------------------------

@router.get("/api/finance", dependencies=[Depends(require_auth)])
def api_finance():
    return db.finance_overview()


# ------------------------------------------------------------------
# Configuracoes
# ------------------------------------------------------------------

@router.get("/api/settings", dependencies=[Depends(require_auth)])
def api_settings():
    return db.settings()
