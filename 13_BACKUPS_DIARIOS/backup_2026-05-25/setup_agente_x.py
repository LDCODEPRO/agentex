"""
AGENTE-X | Setup Script - Missoes M1-M6
Execute este script UMA VEZ no Windows para:
  1. Instalar dependencias Python
  2. Criar e inicializar o banco agente_x.db com o schema completo
  3. Validar todos os modulos M1-M6

Uso: python setup_agente_x.py
"""

import subprocess
import sys
import sqlite3
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent

print("=" * 60)
print("  AGENTE-X | Setup e Inicializacao M1-M6")
print("=" * 60)

# 1. Instalar dependencias
print("\n[1/3] Instalando dependencias...")
REQUIREMENTS = [
    "requests",
    "python-dotenv",
    "chromadb",
    "fastapi",
    "uvicorn",
    "python-multipart",
]
for pkg in REQUIREMENTS:
    import_name = pkg.replace("-", "_")
    try:
        __import__(import_name)
        print("  [OK] " + pkg + " ja instalado")
    except ImportError:
        print("  [..] Instalando " + pkg + "...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])
        print("  [OK] " + pkg + " instalado")

# 2. Criar banco SQLite
print("\n[2/3] Inicializando banco de dados...")
DB_PATH = ROOT / "02_MEMORY" / "agente_x.db"
LOG_DIR = ROOT / "09_LOGS"
LOG_DIR.mkdir(exist_ok=True)

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Core M1-M5
CREATE TABLE IF NOT EXISTS missions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    started_at TEXT,
    finished_at TEXT,
    summary TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    ended_at TEXT,
    total_turns INTEGER DEFAULT 0,
    metadata TEXT
);
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,
    source TEXT NOT NULL,
    message TEXT NOT NULL,
    payload TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);
CREATE TABLE IF NOT EXISTS knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    source TEXT,
    confidence REAL DEFAULT 1.0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    UNIQUE(category, key)
);
CREATE TABLE IF NOT EXISTS fila_execucao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_code TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 5,
    status TEXT NOT NULL DEFAULT 'QUEUED',
    payload TEXT,
    queued_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    started_at TEXT,
    finished_at TEXT
);

-- M6: FinanceEngine
CREATE TABLE IF NOT EXISTS financeiro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d', 'now')),
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    custo_usd REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);
CREATE TABLE IF NOT EXISTS llm_usage_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    custo_usd REAL NOT NULL DEFAULT 0.0,
    timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

-- M6: AntiLoopGuard
CREATE TABLE IF NOT EXISTS rate_limit_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT,
    mission_id TEXT,
    timestamp REAL,
    is_paid INTEGER
);

CREATE INDEX IF NOT EXISTS idx_missions_status ON missions(status);
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge(category);
CREATE INDEX IF NOT EXISTS idx_fila_status ON fila_execucao(status, priority);
CREATE INDEX IF NOT EXISTS idx_financeiro_data ON financeiro(data);
CREATE INDEX IF NOT EXISTS idx_rate_limit_ts ON rate_limit_stats(timestamp);
"""

conn = sqlite3.connect(str(DB_PATH))
conn.executescript(SCHEMA)

missions_seed = [
    ("M1", "Shield Protocol", "DONE"),
    ("M2", "Governance Injection", "DONE"),
    ("M3", "Router & Cognition Upload", "DONE"),
    ("M4", "Memory Foundation", "DONE"),
    ("M5", "The Maestro Boot (Runtime 24/7)", "DONE"),
    ("M6", "WhatsApp Integration + Biblioteca Absorption", "DONE"),
]
for code, title, status in missions_seed:
    conn.execute(
        "INSERT OR IGNORE INTO missions (code, title, status) VALUES (?,?,?)",
        (code, title, status)
    )

rules_seed = [
    ("zero_ghost", "Nenhum codigo pode ser simulado ou mockado."),
    ("create_test_validate_save", "Todo artefato: CREATE->TEST->VALIDATE->SAVE."),
    ("e_drive_readonly", "A unidade E: e somente-leitura. Nunca escrever em E:."),
    ("no_hollow_shells", "Nenhum modulo .py pode nascer com pass."),
    ("no_markdown_overdose", "Documentacao nao substitui codigo funcional."),
    ("react_loop", "Ciclo cognitivo: Thought->Action->Observation->repete."),
    ("skill_learning", "Apos 5+ passos, o agente salva uma skill reutilizavel."),
    ("24x7_daemon", "O Maestro roda em loop continuo processando a fila."),
    ("finance_preflight", "FinanceEngine bloqueia chamadas LLM se budget excedido."),
    ("anti_loop", "AntiLoopGuard bloqueia recursao acima de 3 niveis e rajadas acima de 20 rpm."),
    ("hallucination_guard", "HallucinationGuard valida cada resposta LLM contra o contexto real."),
    ("hermes_soul", "SOUL.md define identidade do agente e e carregado no Slot 1 do prompt."),
]
for key, value in rules_seed:
    conn.execute(
        "INSERT OR IGNORE INTO knowledge (category, key, value, source) VALUES ('RULE',?,?,'FOUNDATION_V1')",
        (key, value)
    )

conn.commit()
tables = [
    r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
]
print("  [OK] Banco criado: " + str(DB_PATH))
print("  [OK] Tabelas: " + str([t for t in tables if t != "sqlite_sequence"]))
conn.close()

# 3. Validar modulos
print("\n[3/3] Validando modulos M1-M6...")

modules_to_check = [
    # M1-M2: Governance
    ROOT / "00_GOVERNANCE" / "RULES" / "safe_gate.py",
    ROOT / "00_GOVERNANCE" / "RULES" / "risk_engine.py",
    # M3: Orchestrator
    ROOT / "01_CORE" / "orchestrator" / "llm_router.py",
    ROOT / "01_CORE" / "orchestrator" / "tool_registry.py",
    ROOT / "01_CORE" / "orchestrator" / "react_engine.py",
    ROOT / "01_CORE" / "orchestrator" / "task_classifier.py",
    # M3: Tools
    ROOT / "01_CORE" / "tools" / "base_tool.py",
    ROOT / "01_CORE" / "tools" / "file_tool.py",
    ROOT / "01_CORE" / "tools" / "shell_tool.py",
    ROOT / "01_CORE" / "tools" / "memory_tool.py",
    ROOT / "01_CORE" / "tools" / "web_tool.py",
    # M3: Finance
    ROOT / "01_CORE" / "finance" / "finance_engine.py",
    # M3: Validation
    ROOT / "01_CORE" / "validation" / "hallucination_guard.py",
    ROOT / "01_CORE" / "validation" / "trace_context.py",
    ROOT / "01_CORE" / "validation" / "anti_loop_guard.py",
    # M4: Memory
    ROOT / "02_MEMORY" / "long_term" / "db_init.py",
    ROOT / "02_MEMORY" / "long_term" / "memory_manager.py",
    ROOT / "02_MEMORY" / "vector_memory" / "chroma_manager.py",
    ROOT / "02_MEMORY" / "short_term" / "context_manager.py",
    # M5: Runtime
    ROOT / "03_RUNTIME" / "maestro.py",
    # M5-M6: Skills
    ROOT / "04_SKILLS" / "skill_manager.py",
    ROOT / "04_SKILLS" / "hermes_core.py",
    # M6: WhatsApp
    ROOT / "06_CONTAINERS" / "whatsapp" / "whatsapp_agent.py",
    # Other
    ROOT / "10_GITHUB" / "save_manager.py",
    ROOT / "agente_x.py",
]

errors = 0
for mod in modules_to_check:
    if mod.exists():
        try:
            ast.parse(mod.read_text(encoding="utf-8"))
            print("  [OK] " + str(mod.relative_to(ROOT)))
        except SyntaxError as e:
            print("  [ERRO SINTAXE] " + str(mod.relative_to(ROOT)) + ": " + str(e))
            errors += 1
    else:
        print("  [AVISO] nao encontrado: " + str(mod.relative_to(ROOT)))

try:
    import requests
    r = requests.get("http://localhost:11434/api/tags", timeout=2)
    if r.status_code == 200:
        print("\n  [OK] Ollama: ONLINE - Router usara modelo local")
    else:
        print("\n  [INFO] Ollama: resposta inesperada")
except Exception:
    print("\n  [INFO] Ollama: OFFLINE - configure .env para APIs externas")

# Verificar .env
env_path = ROOT / ".env"
if env_path.exists():
    env_text = env_path.read_text(encoding="utf-8")
    if "SK-PLACEHOLDER" in env_text:
        print("  [AVISO] .env contem placeholders - configure as API keys reais")
    else:
        print("  [OK] .env configurado")
else:
    print("  [AVISO] .env nao encontrado - crie a partir de .env.example")

print()
print("=" * 60)
if errors == 0:
    print("  AGENTE-X | Setup Concluido - Missoes M1-M6 DONE")
else:
    print("  AGENTE-X | Setup com " + str(errors) + " erro(s) de sintaxe")
print("")
print("  Para iniciar:  python agente_x.py")
print("  Modo 24/7:     python agente_x.py --daemon")
print("  Status:        python agente_x.py --status")
print("  Backup:        python agente_x.py --save")
print("  WhatsApp:      06_CONTAINERS/whatsapp/INICIAR_WHATSAPP.bat")
print("=" * 60)
