"""
AGENTE-X Cockpit | Backend
FastAPI: API real (rotas em routes.py) + serve o build estatico do frontend
(../dist). Um so processo, uma so origem -- sem CORS.

Uso local:  uvicorn main:app --reload --port 5050
Producao:   uvicorn main:app --host 127.0.0.1 --port 5050  (via systemd)
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_ROOT / ".env")

from routes import router  # noqa: E402

DIST_DIR = Path(__file__).resolve().parent.parent / "dist"

app = FastAPI(title="Agente X Cockpit")

session_secret = os.getenv("COCKPIT_SESSION_SECRET")
if not session_secret:
    raise RuntimeError(
        "COCKPIT_SESSION_SECRET nao configurado no .env. "
        "Gere um valor aleatorio (ex: python -c \"import secrets; print(secrets.token_hex(32))\") "
        "e defina COCKPIT_SESSION_SECRET antes de subir o cockpit."
    )
app.add_middleware(SessionMiddleware, secret_key=session_secret, https_only=os.getenv("COCKPIT_HTTPS_ONLY", "true").lower() == "true")

app.include_router(router)


@app.get("/health")
def health():
    return {"ok": True}


if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        """Qualquer rota que nao seja /api/* ou /assets/* cai no index.html
        (roteamento fica por conta do React no cliente)."""
        return FileResponse(str(DIST_DIR / "index.html"))
