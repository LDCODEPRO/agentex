import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "01_CORE" / "validation_engine"))

from validation_engine import ValidationEngine

class TestValidationEngine(unittest.TestCase):
    def setUp(self):
        self.ve = ValidationEngine()

    def test_file_validation(self):
        result = self.ve.validate_action({"file_exists": __file__})
        self.assertTrue(result)

    def test_invalid_file(self):
        result = self.ve.validate_action({"file_exists": "ghost_file_xyz.txt"})
        self.assertFalse(result)

if __name__ == "__main__":
    unittest.main()
