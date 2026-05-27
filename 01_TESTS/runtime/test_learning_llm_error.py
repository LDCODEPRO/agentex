"""
AGENTE-X | Mock LLM Error Test (Auto Didata)
Testa a detecção de erro de LLM e o registro no Learning Loop.
"""
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "01_CORE" / "orchestrator"))

from learning_loop import LearningLoop

class TestLearningLLMError(unittest.TestCase):
    def test_provider_timeout_simulation(self):
        # Simular timeout do Ollama
        loop = LearningLoop()
        error_msg = "TimeoutError: Provider ollama offline or took too long."
        
        # O agente capta isso e joga pro LearningLoop
        result = loop.analyze_error(error_msg, "Chamando router.route()")
        
        self.assertIn("id", result)
        self.assertEqual(result["status"], "PENDING_APPROVAL")
        self.assertIn("Erro originado", result["root_cause"])

if __name__ == "__main__":
    unittest.main()
