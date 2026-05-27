"""
AGENTE-X | Mock Disk Error Test (Auto Didata)
Testa a detecção de erro de disco (ex: SQLite Locked) e registro no loop.
"""
import sys
import sqlite3
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "01_CORE" / "orchestrator"))

from learning_loop import LearningLoop

class TestLearningDiskError(unittest.TestCase):
    def test_sqlite_locked_simulation(self):
        loop = LearningLoop()
        
        # Simular uma exceção real de sqlite3
        try:
            raise sqlite3.OperationalError("database is locked")
        except sqlite3.OperationalError as e:
            result = loop.analyze_error(str(e), "Acesso concorrente em mission_state_manager")
            
        self.assertIn("id", result)
        self.assertEqual(result["status"], "PENDING_APPROVAL")

if __name__ == "__main__":
    unittest.main()
