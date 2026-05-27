import json
import unittest
from pathlib import Path


class HarnessBootstrapTest(unittest.TestCase):
    def test_feature_inventory_exists(self):
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root / "docs" / "features.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["features"]), 3)

    def test_required_project_entrypoints_exist(self):
        root = Path(__file__).resolve().parents[1]
        for relative in [
            "AGENTS.md",
            "PROGRESS.md",
            "DECISIONS.md",
            "docs/QUALITY.md",
            "docs/SPRINT_CONTRACT.md",
            "docs/architecture.md",
            "docs/security.md",
            "docs/evaluation.md",
            "docs/code_review.md",
            "harness/validate.py",
            "scripts/check.py",
            "src/repopilot/__init__.py",
            "src/repopilot/main.py",
            "src/repopilot/approvals/__init__.py",
            "src/repopilot/runs/__init__.py",
            "src/repopilot/workspace/__init__.py",
            "src/repopilot/artifacts/__init__.py",
        ]:
            with self.subTest(relative=relative):
                self.assertTrue((root / relative).exists(), relative)

    def test_feature_inventory_has_single_active_item(self):
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root / "docs" / "features.json").read_text(encoding="utf-8"))
        active = [item for item in data["features"] if item["state"] == "active"]
        self.assertLessEqual(len(active), 1)


if __name__ == "__main__":
    unittest.main()
