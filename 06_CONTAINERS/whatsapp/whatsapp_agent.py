"""
AGENTE-X | WhatsApp Agent (M6)
Porta 3001 — ponte entre WhatsApp (servidor.js) e AGENTE-X (ReAct Engine).

Fluxo:
  WhatsApp -> servidor.js (porta 3000) -> aqui (porta 3001) -> ReAct Engine -> resposta -> WhatsApp

Como usar:
  1. cd "D:\\Agente X\\06_CONTAINERS\\whatsapp"
  2. node servidor.js          (deixar rodando — escaneia QR code uma vez)
  3. python whatsapp_agent.py  (em outro terminal)
"""
import sys, os, json, logging
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
for p in [
    ROOT / "01_CORE/orchestrator",
    ROOT / "01_CORE/tools",
    ROOT / "01_CORE/validation",
    ROOT / "01_CORE/finance",
    ROOT / "02_MEMORY/long_term",
    ROOT / "02_MEMORY/short_term",
    ROOT / "04_SKILLS",
    ROOT / "00_GOVERNANCE/RULES",
    ROOT / "12_CONFIG",
]:
    sys.path.insert(0, str(p))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    filename=str(ROOT / "09_LOGS" / "whatsapp_agent.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("WhatsAppAgent")

HISTORICO_DIR = ROOT / "06_CONTAINERS" / "whatsapp" / "historicos"
HISTORICO_DIR.mkdir(parents=True, exist_ok=True)

WHATSAPP_URL   = "http://localhost:3000"
MAX_HISTORICO  = 10
IGNORAR_GRUPOS = True
PREFIXO_GRUPO  = "!"

app = FastAPI(title="AGENTE-X WhatsApp Bridge")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_historicos: dict = {}


# ── UTILITARIOS ───────────────────────────────────────────────────────────

def _enviar_whatsapp(numero: str, mensagem: str) -> bool:
    import urllib.request
    try:
        payload = json.dumps({"numero": numero, "mensagem": mensagem}).encode("utf-8")
        req = urllib.request.Request(
            f"{WHATSAPP_URL}/enviar", data=payload,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            res = json.loads(r.read())
            return res.get("ok", False)
    except Exception as e:
        logger.error("Erro ao enviar para %s: %s", numero, e)
        return False


def _carregar_historico(numero: str) -> list:
    if numero in _historicos:
        return _historicos[numero]
    arquivo = HISTORICO_DIR / f"{numero}.json"
    if arquivo.exists():
        try:
            _historicos[numero] = json.loads(arquivo.read_text(encoding="utf-8"))
        except Exception:
            _historicos[numero] = []
    else:
        _historicos[numero] = []
    return _historicos[numero]


def _salvar_historico(numero: str, historico: list):
    _historicos[numero] = historico[-MAX_HISTORICO:]
    arquivo = HISTORICO_DIR / f"{numero}.json"
    try:
        arquivo.write_text(
            json.dumps(_historicos[numero], ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        logger.warning("Nao foi possivel salvar historico de %s: %s", numero, e)


def _processar_com_agente(mensagem: str, numero: str, nome: str) -> str:
    """Passa mensagem para o AGENTE-X via ReAct Engine e retorna resposta."""
    try:
        from react_engine import ReActEngine
        session_id = f"whatsapp_{numero}"
        engine = ReActEngine(session_id=session_id)
        goal = f"[WhatsApp] De: {nome} ({numero}) | Mensagem: {mensagem}"
        resposta = engine.run(goal, verbose=False)
        return resposta or "Recebi sua mensagem. Processando..."
    except Exception as e:
        logger.error("Erro no ReAct Engine para %s: %s", numero, e)
        return f"[AGENTE-X] Erro interno: {str(e)[:100]}"


# ── ENDPOINTS ─────────────────────────────────────────────────────────────

@app.post("/mensagem")
async def receber_mensagem(request: Request):
    """Recebe mensagem do servidor.js, processa com AGENTE-X, envia resposta."""
    try:
        dados = await request.json()
    except Exception:
        return {"ok": False, "erro": "Payload invalido"}

    numero   = str(dados.get("numero", "")).strip()
    nome     = str(dados.get("nome", "Contato")).strip()
    mensagem = str(dados.get("mensagem", "")).strip()
    e_grupo  = bool(dados.get("grupo", False))

    if not numero or not mensagem:
        return {"ok": False, "erro": "numero e mensagem obrigatorios"}

    if e_grupo and IGNORAR_GRUPOS:
        return {"ok": True, "ignorado": True, "motivo": "grupo ignorado"}

    if e_grupo and not mensagem.startswith(PREFIXO_GRUPO):
        return {"ok": True, "ignorado": True, "motivo": "sem prefixo de ativacao"}

    if mensagem.startswith(PREFIXO_GRUPO):
        mensagem = mensagem[len(PREFIXO_GRUPO):].strip()

    logger.info("[RECEBIDO] %s (%s): %s", nome, numero, mensagem[:80])

    # Aprender contato via hermes_core
    try:
        from hermes_core import aprender_fato
        aprender_fato("agente_x",
                      f"WhatsApp: {nome} ({numero[:10]}): {mensagem[:80]}",
                      "whatsapp")
    except Exception:
        pass

    resposta = _processar_com_agente(mensagem, numero, nome)
    enviado  = _enviar_whatsapp(numero, resposta)

    logger.info("[ENVIADO] -> %s (%s chars) | ok=%s", numero, len(resposta), enviado)

    historico = _carregar_historico(numero)
    historico.append({
        "usuario":    f"[{nome}] {mensagem}",
        "assistente": resposta,
        "ts":         datetime.now().strftime("%d/%m/%Y %H:%M"),
    })
    _salvar_historico(numero, historico)

    return {"ok": enviado, "para": numero, "resposta_chars": len(resposta)}


@app.post("/enviar_direto")
async def enviar_direto(request: Request):
    """Envia mensagem diretamente para um numero. Payload: {numero, mensagem}"""
    try:
        dados = await request.json()
    except Exception:
        return {"ok": False, "erro": "Payload invalido"}
    numero   = str(dados.get("numero", "")).strip()
    mensagem = str(dados.get("mensagem", "")).strip()
    if not numero or not mensagem:
        return {"ok": False, "erro": "numero e mensagem obrigatorios"}
    ok = _enviar_whatsapp(numero, mensagem)
    logger.info("[DIRETO] -> %s | ok=%s", numero, ok)
    return {"ok": ok, "para": numero}


@app.get("/status")
def status():
    return {
        "agente":    "AGENTE-X WhatsApp Bridge",
        "porta":     3001,
        "whatsapp":  WHATSAPP_URL,
        "historicos": len(_historicos),
        "ts":        datetime.now().isoformat(),
    }


@app.get("/historico/{numero}")
def ver_historico(numero: str):
    h = _carregar_historico(numero)
    return {"numero": numero, "turnos": len(h), "historico": h}


@app.delete("/historico/{numero}")
def limpar_historico(numero: str):
    _historicos[numero] = []
    arquivo = HISTORICO_DIR / f"{numero}.json"
    if arquivo.exists():
        arquivo.unlink()
    return {"ok": True}


@app.on_event("startup")
async def startup():
    logger.info("AGENTE-X WhatsApp Bridge iniciado na porta 3001")
    print("=" * 55)
    print("  AGENTE-X | WhatsApp Bridge")
    print("  Porta 3001 | Conectando a servidor.js (3000)")
    print("  Mensagens recebidas -> ReAct Engine -> WhatsApp")
    print("=" * 55)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001, log_level="warning")
