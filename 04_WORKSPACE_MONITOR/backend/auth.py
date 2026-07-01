"""
AGENTE-X Cockpit | Autenticacao
Usuario unico (o Diretor). Senha nunca fica em texto puro -- so o hash bcrypt
vive no .env (COCKPIT_PASSWORD_HASH). Sessao via cookie assinado (Starlette
SessionMiddleware, chave em COCKPIT_SESSION_SECRET).
"""
import os

import bcrypt
from fastapi import HTTPException, Request


def check_password(plain: str) -> bool:
    hashed = os.getenv("COCKPIT_PASSWORD_HASH", "")
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def require_auth(request: Request) -> None:
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Sessao expirada ou nao autenticada")
