import os
import time
import unittest

from ._util import RepoCase


class ReviewScopeTest(RepoCase):
    def test_no_prior_review_lists_all(self):
        self.add({"design/gdd/a.md": "# A\n", "design/gdd/game-concept.md": "# C\n"})
        code, out, _ = self.run_cli("review-scope")
        self.assertEqual(code, 0)
        self.assertIn("PRIOR_REVIEW: NONE (full review required)", out)
        self.assertIn("  design/gdd/a.md", out)
        self.assertNotIn("game-concept", out)

    def test_changed_since_review_and_deps(self):
        self.add({"design/gdd/gdd-cross-review-2026-01-01.md": "# R\n",
                  "design/gdd/old.md": "# Old\n",
                  "design/gdd/new.md": "# New\n\n## Dependencies\n\nNeeds old.md and loot.md\n"})
        past = time.time() - 1000
        os.utime(os.path.join(self.root, "design/gdd/gdd-cross-review-2026-01-01.md"), (past + 500, past + 500))
        os.utime(os.path.join(self.root, "design/gdd/old.md"), (past, past))
        code, out, _ = self.run_cli("review-scope")
        self.assertEqual(code, 0)
        self.assertIn("PRIOR_REVIEW: design/gdd/gdd-cross-review-2026-01-01.md", out)
        self.assertIn("  design/gdd/new.md", out)
        self.assertNotIn("  design/gdd/old.md", out)
        self.assertIn("new.md -> loot.md", out)
        self.assertIn("new.md -> old.md", out)
