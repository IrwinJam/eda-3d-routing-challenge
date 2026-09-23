import unittest

from m3d.baseline import route
from m3d.checker import check
from m3d.generator import GenConfig, generate_feasible
from m3d.scorer import CaseScore, leaderboard, score_case


class TestBaseline(unittest.TestCase):
    def test_baseline_routes_legally(self):
        cfg = GenConfig(name="b", width=24, height=24, layers=6, n_nets=18, seed=2)
        inst = generate_feasible(cfg).instance
        sub, stats = route(inst)
        self.assertIsNotNone(sub)
        self.assertTrue(stats.success)
        res = check(inst, sub)
        self.assertTrue(res.legal, res.reasons)

    def test_multipin_nets_are_trees(self):
        cfg = GenConfig(name="m", width=28, height=28, layers=6, n_nets=25,
                        p_twopin=0.0, max_fanout=6, seed=9)  # force multi-pin
        inst = generate_feasible(cfg).instance
        self.assertTrue(any(len(n.sinks) >= 2 for n in inst.nets))
        sub, _ = route(inst)
        res = check(inst, sub)
        self.assertTrue(res.legal, res.reasons)


class TestScorer(unittest.TestCase):
    def test_self_score_is_one(self):
        cfg = GenConfig(name="s", width=22, height=22, layers=6, n_nets=15, seed=4)
        r = generate_feasible(cfg)
        cs = score_case(r.instance, r.reference, r.baseline_total)
        self.assertTrue(cs.legal)
        self.assertAlmostEqual(cs.ratio, 1.0, places=6)

    def test_leaderboard_geomean_and_completeness(self):
        good = [CaseScore("c1", True, 100, 200, 2.0),
                CaseScore("c2", True, 50, 100, 2.0)]
        lb = leaderboard(good)
        self.assertTrue(lb.complete)
        self.assertAlmostEqual(lb.aggregate_score, 2.0, places=6)  # geomean(2,2)=2

        mixed = [CaseScore("c1", True, 100, 200, 2.0),
                 CaseScore("c2", False, None, 100, None, reasons=["short"])]
        lb2 = leaderboard(mixed)
        self.assertFalse(lb2.complete)
        self.assertEqual(lb2.aggregate_score, 0.0)

    def test_better_route_scores_higher(self):
        worse = leaderboard([CaseScore("c", True, 200, 100, 0.5)]).aggregate_score
        better = leaderboard([CaseScore("c", True, 50, 100, 2.0)]).aggregate_score
        self.assertLess(worse, 1.0)
        self.assertGreater(better, 1.0)


if __name__ == "__main__":
    unittest.main()
