import unittest
import sys
import json
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "01_CORE" / "mission_engine"))
sys.path.insert(0, str(_ROOT / "02_MEMORY" / "long_term"))

from mission_brain import MissionBrain
from memory_manager import MemoryManager

class TestMissionBrain(unittest.TestCase):
    def setUp(self):
        self.brain = MissionBrain()
        self.mm = MemoryManager()
        
    def test_ingest_plan(self):
        # Usamos um json hardcoded pra simular a resposta ja decodada do LLM
        mock_plan = [
            {"code": "STEP1", "goal": "Setup inicial", "dependencies": []},
            {"code": "STEP2", "goal": "Compilar codigo", "dependencies": ["STEP1"]}
        ]
        
        res = self.brain.ingest_plan(mock_plan, "Simular Compilacao")
        self.assertTrue(res)
        
        # Validar no banco
        with self.mm._conn() as conn:
            c = conn.cursor()
            c.execute("SELECT mission_code, payload FROM fila_execucao WHERE mission_code LIKE '%_STEP2'")
            row = c.fetchone()
            
            self.assertIsNotNone(row)
            self.assertIn("MACRO_", row[1])

if __name__ == "__main__":
    unittest.main()
