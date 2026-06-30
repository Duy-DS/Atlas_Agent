import unittest
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from agents.validator import ValidatorAgent
from core.graph import create_agent_graph
from tools.db_helper import DatabaseHelper
from tools.token_tracker import TokenTracker

class TestCommercialIntelligenceBoilerplate(unittest.TestCase):

    def setUp(self):
        self.mock_data = {
            "date": "2026-06-30",
            "properties": {
                "property_a": {
                    "occupancy": 0.85,
                    "adr": 150.0,
                    "revenue": 12750.0,
                    "bookings_today": 10,
                    "cancellations_today": 1
                },
                "property_b": {
                    "occupancy": 1.20, # Outlier: occupancy > 1.0 (120%)
                    "adr": -50.0,      # Outlier: negative ADR
                    "revenue": 5000.0,
                    "bookings_today": 5,
                    "cancellations_today": -2 # Outlier: negative cancellations
                }
            }
        }

    def test_validator_programmatic_outliers(self):
        """Tests that the validator agent programmatically catches negative values and out-of-bounds occupancy."""
        validator = ValidatorAgent()
        res = validator.validate_metrics(self.mock_data)
        
        self.assertFalse(res["is_valid"])
        # Check that outliers are correctly identified
        self.assertTrue(any("property_b.occupancy is out of range" in o for o in res["outliers"]))
        self.assertTrue(any("property_b.adr cannot be negative" in o for o in res["outliers"]))
        self.assertTrue(any("property_b.cancellations_today cannot be negative" in o for o in res["outliers"]))
        # No fields should be missing in property_a or property_b
        self.assertEqual(len(res["missing_fields"]), 0)

    def test_graph_compiles(self):
        """Tests that the LangGraph compiles successfully without structural errors."""
        try:
            graph = create_agent_graph()
            self.assertIsNotNone(graph)
        except Exception as e:
            self.fail(f"Graph compilation failed: {e}")

    def test_db_helper_caching(self):
        """Tests local SQLite DatabaseHelper caching mechanism."""
        db = DatabaseHelper(db_path=Path("data/test_ci_storage.db"))
        db.set_cache("key1", "value1")
        self.assertEqual(db.get_cache("key1"), "value1")
        
        db.clear_cache()
        if db.db_path.exists():
            db.db_path.unlink()

    def test_token_tracker(self):
        """Tests TokenTracker cost summaries calculations."""
        tracker = TokenTracker(stats_file=Path("output/test_ci_stats.json"))
        # Track Claude 3.5 Sonnet call
        tracker.track("claude-3-5-sonnet-20241022", prompt_tokens=1000, completion_tokens=500)
        summary = tracker.get_summary()
        
        self.assertEqual(summary["total_prompt_tokens"], 1000)
        self.assertEqual(summary["total_completion_tokens"], 500)
        self.assertGreater(summary["total_cost_usd"], 0.0)

if __name__ == "__main__":
    unittest.main()
