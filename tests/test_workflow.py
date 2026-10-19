"""Offline contract checks for the secret-bearing workflow; stdlib only."""
from pathlib import Path
import re
import unittest


class WorkflowTests(unittest.TestCase):
    def test_manual_main_only_read_only_and_bounded(self):
        workflow = Path(".github/workflows/scopus-smoke.yml").read_text()
        self.assertRegex(workflow, r"(?m)^'on':\n  workflow_dispatch:\s*\n\n")
        self.assertNotRegex(workflow, r"(?m)^  (push|pull_request|pull_request_target|schedule):")
        self.assertIn("if: github.ref == 'refs/heads/main'", workflow)
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertNotIn(": write", workflow)
        self.assertIn("environment: search", workflow)
        self.assertIn("timeout-minutes: 2", workflow)
        self.assertIn("timeout --signal=TERM --kill-after=5s 35s python3 -m scopus_cli.smoke", workflow)
        self.assertIn("persist-credentials: false", workflow)
        actions = re.findall(r"uses: (\S+)", workflow)
        self.assertEqual(len(actions), 1)
        self.assertRegex(actions[0], r"^actions/checkout@[0-9a-f]{40}$")
        self.assertEqual(workflow.count("${{ secrets.SCOPUS_API_KEY }}"), 1)
        self.assertNotIn("upload-artifact", workflow)
        self.assertNotIn("--json", workflow)


if __name__ == "__main__":
    unittest.main()
