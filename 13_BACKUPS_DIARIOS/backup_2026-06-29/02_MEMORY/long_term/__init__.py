"""
AGENTE-X | 02_MEMORY/long_term
Memória de longo prazo baseada em SQLite.
"""
from .memory_manager import MemoryManager
from .db_init import init_database, get_schema_info

__all__ = ["MemoryManager", "init_database", "get_schema_info"]
