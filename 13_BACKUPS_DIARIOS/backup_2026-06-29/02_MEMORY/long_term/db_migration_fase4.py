import sqlite3
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = _ROOT / "02_MEMORY" / "agente_x.db"

def migrate():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    # Dropando e recriando a tabela missions para adequar ao novo schema
    cursor.execute("DROP TABLE IF EXISTS missions;")
    cursor.execute("""
    CREATE TABLE missions (
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
    """)
    cursor.execute("CREATE INDEX idx_missions_status ON missions(status);")
    conn.commit()
    conn.close()
    print("Migração concluída: Tabela 'missions' atualizada para FASE 4.")

if __name__ == "__main__":
    migrate()
