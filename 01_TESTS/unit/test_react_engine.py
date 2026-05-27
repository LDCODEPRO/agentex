import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "01_CORE" / "orchestrator"))
from react_engine import ReActEngine

class TestReactEngine(unittest.TestCase):
    def test_engine_init(self):
        engine = ReActEngine()
        self.assertIsNotNone(engine.router)
        self.assertIsNotNone(engine.registry)
        self.assertIsNotNone(engine.context)

if __name__ == "__main__":
    unittest.main()
