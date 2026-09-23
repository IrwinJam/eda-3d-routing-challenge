import importlib.util
import os
import sys
import unittest

from m3d.baseline import route
from m3d.checker import check
from m3d.generator import GenConfig, generate_feasible
from m3d.scorer import leaderboard, score_case

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_example():
    path = os.path.join(REPO, "examples", "example_submission.py")
    spec = importlib.util.spec_from_file_location("example_submission", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["example_submission"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestEndToEnd(unittest.TestCase):
    def _mini_suite(self):
        cfgs = [
            GenConfig(name="e1", width=18, height=18, layers=6, n_nets=8, seed=101),
            GenConfig(name="e2", width=22, height=22, layers=6, n_nets=14, seed=202),
            GenConfig(name="e3", width=26, height=26, layers=6, n_nets=20, seed=303),
        ]
        return [generate_feasible(c) for c in cfgs]

    def test_generate_baseline_evaluate_score(self):
        results = self._mini_suite()
        scores = []
        for r in results:
            sub, stats = route(r.instance)
            self.assertIsNotNone(sub)
            res = check(r.instance, sub)
            self.assertTrue(res.legal, res.reasons)
            scores.append(score_case(r.instance, sub, r.baseline_total))
        lb = leaderboard(scores)
        self.assertTrue(lb.complete)
        self.assertAlmostEqual(lb.aggregate_score, 1.0, places=6)

    def test_example_router_is_legal_and_complete(self):
        ex = _load_example()
        for r in self._mini_suite():
            sub = ex.route_instance(r.instance)
            res = check(r.instance, sub)
            self.assertTrue(res.legal, f"{r.instance.name}: {res.reasons}")


if __name__ == "__main__":
    unittest.main()
