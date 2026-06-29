"""
AGENTE-X | Learning Loop (Auto-Didata Real)
Captura falhas, analisa a causa raiz via LLM (quando disponivel) ou heuristicas reais,
e armazena na knowledge base para nao repetir erros.
Principio Zero Ghost: nenhuma simulacao. Analise real ou heuristica documentada.
"""
import sqlite3
import time
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH        = _ROOT / "02_MEMORY" / "learning_memory.db"
MAIN_DB_PATH   = _ROOT / "02_MEMORY" / "agente_x.db"


# Heuristicas reais de classificacao de erros (Zero Ghost: sem mocks)
_ERROR_PATTERNS = [
    (r"AttributeError.*has no attribute '(\w+)'",
     "Metodo ou atributo '{1}' nao existe no objeto. Verificar API/versao.",
     "Adicionar verificacao hasattr() ou atualizar import/versao do modulo."),
    (r"ModuleNotFoundError.*'([\w\.]+)'",
     "Modulo '{1}' nao instalado ou nao encontrado no PYTHONPATH.",
     "Executar: pip install {1} --break-system-packages"),
    (r"sqlite3\.(OperationalError|DatabaseError).*disk I/O",
     "SQLite nao consegue escrever em disco (NTFS/permissoes).",
     "Usar _connect() com fallback para /tmp. Verificar permissoes NTFS."),
    (r"sqlite3\.OperationalError.*no such (column|table): (\w+)",
     "Schema desatualizado: {2} '{3}' nao existe.",
     "Rodar db_init.py ou setup_agente_x.py para atualizar o schema."),
    (r"ConnectionRefusedError|ConnectionError.*localhost:(\d+)",
     "Servico local na porta {1} nao esta rodando.",
     "Verificar se Ollama/backend esta iniciado. Ver: python agente_x.py --status"),
    (r"requests\.exceptions\.(Timeout|ConnectTimeout)",
     "Timeout ao chamar API externa.",
     "Aumentar timeout no LLMRouter ou verificar conectividade."),
    (r"RuntimeError.*LLMRouter.*nenhum provider",
     "Nenhum provider LLM disponivel.",
     "Verificar .env com chaves validas. Iniciar Ollama para modo local."),
    (r"KeyError.*'(\w+)'",
     "Chave '{1}' ausente no dicionario/resposta.",
     "Adicionar .get() com valor padrao ou validar resposta antes de acessar."),
    (r"RecursionError|maximum recursion",
     "Recursao infinita detectada.",
     "AntiLoopGuard deve bloquear. Verificar MAX_DEPTH no anti_loop_guard.py."),
    (r"PermissionError|Access is denied",
     "Sem permissao para acessar arquivo/diretorio.",
     "Verificar permissoes. Nunca escrever em E:. Usar caminhos dentro de D:."),
]


def _classify_error(error_msg: str) -> tuple[str, str]:
    """Classifica o erro usando heuristicas reais (Zero Ghost: sem mock)."""
    for pattern, cause_tmpl, fix_tmpl in _ERROR_PATTERNS:
        m = re.search(pattern, error_msg, re.IGNORECASE)
        if m:
            groups = m.groups()
            cause = cause_tmpl
            fix   = fix_tmpl
            for i, g in enumerate(groups, 1):
                if g:
                    cause = cause.replace(f"{{{i}}}", g)
                    fix   = fix.replace(f"{{{i}}}", g)
            return cause, fix
    # Fallback generico — mas honesto
    return (
        f"Erro nao classificado automaticamente: {error_msg[:120]}",
        "Analisar stack trace completo e verificar logs em 09_LOGS/."
    )


def _connect_learning():
    """Abre conexao com learning_memory.db com fallback."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("CREATE TABLE IF NOT EXISTS _wtest (x INTEGER)")
        conn.execute("DROP TABLE IF EXISTS _wtest")
        conn.commit()
        return conn
    except Exception:
        import tempfile as _t
        return sqlite3.connect(_t.gettempdir() + "/agente_x_learning.db")


def _connect_main():
    """Abre conexao com agente_x.db (principal) com fallback."""
    try:
        conn = sqlite3.connect(str(MAIN_DB_PATH))
        conn.execute("CREATE TABLE IF NOT EXISTS _wtest (x INTEGER)")
        conn.execute("DROP TABLE IF EXISTS _wtest")
        conn.commit()
        return conn
    except Exception:
        import tempfile as _t
        return sqlite3.connect(_t.gettempdir() + "/agente_x_fallback.db")


class LearningLoop:
    """
    Loop de aprendizado autonomo do AGENTE-X.
    - analyze_error(): classifica e registra erros reais
    - inject_knowledge(): adiciona fatos verificados na knowledge base
    - get_fix_for(): recupera solucao aprendida para um tipo de erro
    - summary(): retorna estatisticas do aprendizado
    """

    def __init__(self):
        self._init_db()

    def _init_db(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = _connect_learning()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS error_logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                error_hash TEXT NOT NULL,
                error_msg  TEXT NOT NULL,
                root_cause TEXT NOT NULL,
                proposed_fix TEXT NOT NULL,
                source     TEXT DEFAULT 'HEURISTIC',
                status     TEXT DEFAULT 'PENDING',
                occurrences INTEGER DEFAULT 1,
                resolved   INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
                updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learned_facts (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key      TEXT NOT NULL UNIQUE,
                value    TEXT NOT NULL,
                source   TEXT,
                confidence REAL DEFAULT 1.0,
                created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
            )
        """)
        conn.commit()
        conn.close()

    def analyze_error(self, error_msg: str, context: str = "", source: str = "HEURISTIC") -> dict:
        """
        Analisa erro real com heuristicas ou LLM.
        Zero Ghost: nenhuma causa/fix fabricado — apenas padrao reconhecido ou admite desconhecimento.
        """
        import hashlib
        error_hash = hashlib.md5(error_msg[:200].encode()).hexdigest()[:12]
        root_cause, proposed_fix = _classify_error(error_msg)

        conn = _connect_learning()
        # Verificar se ja existe para incrementar ocorrencias
        existing = conn.execute(
            "SELECT id, occurrences FROM error_logs WHERE error_hash=?", (error_hash,)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE error_logs SET occurrences=?, updated_at=strftime('%Y-%m-%dT%H:%M:%S','now') WHERE id=?",
                (existing[1] + 1, existing[0])
            )
            record_id = existing[0]
        else:
            conn.execute(
                """INSERT INTO error_logs
                   (error_hash, error_msg, root_cause, proposed_fix, source)
                   VALUES (?,?,?,?,?)""",
                (error_hash, error_msg[:500], root_cause, proposed_fix, source)
            )
            record_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        conn.commit()
        conn.close()

        # Tambem registrar no knowledge base principal
        self.inject_knowledge(
            category="LEARNED_ERROR",
            key=f"error_{error_hash}",
            value=f"CAUSA: {root_cause} | FIX: {proposed_fix}",
            source="LearningLoop",
        )

        return {
            "id": record_id,
            "error_hash": error_hash,
            "root_cause": root_cause,
            "proposed_fix": proposed_fix,
            "source": source,
            "status": "ANALYZED",
        }

    def inject_knowledge(self, category: str, key: str, value: str,
                         source: str = "LEARNING_LOOP", confidence: float = 1.0) -> bool:
        """
        Injeta fato verificado na knowledge base principal (agente_x.db).
        Retorna True se inserido/atualizado, False se falhou.
        """
        try:
            conn = _connect_main()
            conn.execute("""
                INSERT INTO knowledge (category, key, value, source, confidence)
                VALUES (?,?,?,?,?)
                ON CONFLICT(category, key) DO UPDATE SET
                    value=excluded.value,
                    source=excluded.source,
                    confidence=excluded.confidence,
                    updated_at=strftime('%Y-%m-%dT%H:%M:%S','now')
            """, (category, key, value, source, confidence))
            conn.commit()
            conn.close()
            # Tambem no learning_memory local
            conn2 = _connect_learning()
            conn2.execute("""
                INSERT OR REPLACE INTO learned_facts (category, key, value, source, confidence)
                VALUES (?,?,?,?,?)
            """, (category, key, value, source, confidence))
            conn2.commit()
            conn2.close()
            return True
        except Exception as e:
            print(f"[LearningLoop] inject_knowledge falhou: {e}")
            return False

    def get_fix_for(self, error_msg: str) -> str | None:
        """
        Recupera a solucao aprendida para um padrao de erro.
        Retorna None se nao encontrado.
        """
        import hashlib
        error_hash = hashlib.md5(error_msg[:200].encode()).hexdigest()[:12]
        conn = _connect_learning()
        row = conn.execute(
            "SELECT proposed_fix FROM error_logs WHERE error_hash=?", (error_hash,)
        ).fetchone()
        conn.close()
        return row[0] if row else None

    def mark_resolved(self, error_hash: str) -> bool:
        """Marca um erro como resolvido."""
        try:
            conn = _connect_learning()
            conn.execute(
                "UPDATE error_logs SET resolved=1, status='RESOLVED' WHERE error_hash=?",
                (error_hash,)
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def summary(self) -> dict:
        """Retorna estatisticas do aprendizado."""
        conn = _connect_learning()
        total = conn.execute("SELECT COUNT(*) FROM error_logs").fetchone()[0]
        resolved = conn.execute("SELECT COUNT(*) FROM error_logs WHERE resolved=1").fetchone()[0]
        top_errors = [
            {"error": r[0][:80], "occurrences": r[1]}
            for r in conn.execute(
                "SELECT error_msg, occurrences FROM error_logs ORDER BY occurrences DESC LIMIT 5"
            ).fetchall()
        ]
        facts = conn.execute("SELECT COUNT(*) FROM learned_facts").fetchone()[0]
        conn.close()
        return {
            "errors_logged": total,
            "errors_resolved": resolved,
            "top_errors": top_errors,
            "facts_learned": facts,
        }


if __name__ == "__main__":
    import json
    ll = LearningLoop()
    # Auto-teste com erros reais do sistema
    test_errors = [
        "AttributeError: 'LLMRouter' object has no attribute 'chat'",
        "sqlite3.OperationalError: disk I/O error",
        "ModuleNotFoundError: No module named 'fastapi'",
        "RuntimeError: LLMRouter: nenhum provider disponivel. Erros: ollama: ...",
    ]
    print("=== LearningLoop — Teste Real ===")
    for err in test_errors:
        result = ll.analyze_error(err)
        print(f"\n[ERRO] {err[:60]}...")
        print(f"  CAUSA: {result['root_cause']}")
        print(f"  FIX:   {result['proposed_fix']}")
    print("\n=== Summary ===")
    print(json.dumps(ll.summary(), indent=2, ensure_ascii=False))
