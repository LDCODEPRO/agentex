import sys
import unittest
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "02_MEMORY" / "long_term"))
from memory_manager import MemoryManager

class TestMemoryManager(unittest.TestCase):
    def setUp(self):
        self.mm = MemoryManager()
        
    def test_mission_queue(self):
        mission_code = f"TEST_Q_{int(time.time())}"
        self.mm.enqueue_mission(mission_code, priority=1, payload={"test": True})
        
        item = self.mm.dequeue_next()
        self.assertIsNotNone(item)
        self.mm.finish_queue_item(item["id"], status="DONE")

if __name__ == "__main__":
    unittest.main()
