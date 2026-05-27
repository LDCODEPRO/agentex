"""
AGENTE-X | Learning Loop (Auto Didata Controlado)
Captura falhas, analisa a causa raiz e propõe correções armazenando-as
na learning_memory.db para não repetir o mesmo erro.
"""
import sqlite3
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = _ROOT / "02_MEMORY" / "learning_memory.db"

class LearningLoop:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_message TEXT,
                root_cause TEXT,
                proposed_fix TEXT,
                status TEXT DEFAULT 'PENDING_APPROVAL',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def analyze_error(self, error_msg: str, context: str = "") -> dict:
        """
        Em um sistema FASE 5 usaria LLM. Aqui na FASE 4, gravamos o erro de forma
        estruturada para que o Safe Gate autorize e o orquestrador aprenda.
        """
        # Exemplo: Simular analise de causa raiz
        root_cause = f"Erro originado possivelmente por contexto inválido: {context[:50]}"
        proposed_fix = "Validar tipagem antes de execução."
        
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO error_logs (error_message, root_cause, proposed_fix) VALUES (?, ?, ?)",
            (error_msg, root_cause, proposed_fix)
        )
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "id": record_id,
            "root_cause": root_cause,
            "proposed_fix": proposed_fix,
            "status": "PENDING_APPROVAL"
        }
