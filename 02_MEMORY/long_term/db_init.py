"""
AGENTE-X | Memory Foundation — Database Initializer
Cria e inicializa o banco SQLite real (agente_x.db) com o schema completo.
Princípio Zero Ghost: banco físico, sem mocks, sem dumps JSON falsos.
"""

import sqlite3
import logging
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = _ROOT / "02_MEMORY" / "agente_x.db"
LOG_PATH = _ROOT / "09_LOGS" / "memory.log"

logging.basicConfig(
    filename=str(LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("DBInit")

SCHEMA = """
-- ============================================================
-- AGENTE-X | Schema v1.0
-- ============================================================

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Missões executadas ou em execução
CREATE TABLE IF NOT EXISTS missions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    mission_parent  TEXT,
    status          TEXT NOT NULL DEFAULT 'MISSION_CREATED',
    started_at      TEXT,
    ended_at        TEXT,
    retry_count     INTEGER DEFAULT 0,
    dependencies    TEXT,
    result          TEXT,
    evidence_path   TEXT,
    summary         TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

-- Sessões de interação com LLMs
CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL UNIQUE,
    provider    TEXT NOT NULL,
    model       TEXT NOT NULL,
    started_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    ended_at    TEXT,
    total_turns INTEGER DEFAULT 0,
    metadata    TEXT    -- JSON livre
);

-- Log de eventos do sistema
CREATE TABLE IF NOT EXISTS logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    level       TEXT NOT NULL,    -- INFO | WARNING | ERROR | CRITICAL
    source      TEXT NOT NULL,    -- nome do módulo
    message     TEXT NOT NULL,
    payload     TEXT,             -- JSON opcional
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

-- Memória de longo prazo: fatos e conhecimento persistido
CREATE TABLE IF NOT EXISTS knowledge (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category    TEXT NOT NULL,    -- ex: RULE, FACT, DECISION, CONTEXT
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    source      TEXT,             -- de onde veio este conhecimento
    confidence  REAL DEFAULT 1.0, -- 0.0 a 1.0
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    UNIQUE(category, key)
);

-- Fila de execução (usada pelo Maestro Boot — M5)
CREATE TABLE IF NOT EXISTS fila_execucao (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_code TEXT NOT NULL,
    priority    INTEGER NOT NULL DEFAULT 5,  -- 1 (máx) a 10 (mín)
    status      TEXT NOT NULL DEFAULT 'QUEUED',  -- QUEUED | RUNNING | DONE | FAILED
    payload     TEXT,   -- JSON com parâmetros da missão
    queued_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    started_at  TEXT,
    finished_at TEXT
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_missions_status   ON missions(status);
CREATE INDEX IF NOT EXISTS idx_logs_level        ON logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_source       ON logs(source);
CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge(category);
CREATE INDEX IF NOT EXISTS idx_fila_status       ON fila_execucao(status, priority);
"""


def init_database(db_path: Path = DB_PATH) -> bool:
    """
    Cria o banco de dados e aplica o schema completo.
    Idempotente: seguro para rodar múltiplas vezes.
    Retorna True se bem-sucedido, False se falhar.
    """
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.executescript(SCHEMA)
        conn.commit()

        # Verificar que as tabelas foram criadas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        expected = {"missions", "sessions", "logs", "knowledge", "fila_execucao"}
        missing = expected - set(tables)
        if missing:
            raise RuntimeError(f"Tabelas ausentes após init: {missing}")

        logger.info("Banco inicializado com sucesso: %s | Tabelas: %s", db_path, tables)
        return True

    except Exception as e:
        logger.error("Falha ao inicializar banco: %s", e)
        raise


def get_schema_info(db_path: Path = DB_PATH) -> dict:
    """Retorna metadados do banco para auditoria."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]
    info = {}
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        info[table] = cursor.fetchone()[0]
    conn.close()
    return {"db_path": str(db_path), "tables": info}


if __name__ == "__main__":
    print("Inicializando agente_x.db...")
    init_database()
    info = get_schema_info()
    print(f"Banco: {info['db_path']}")
    print("Tabelas criadas:")
    for table, count in info["tables"].items():
        print(f"  {table}: {count} registros")
    print("OK — Memory Foundation ativa.")
