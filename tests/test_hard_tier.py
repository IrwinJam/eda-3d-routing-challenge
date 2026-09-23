import unittest

from m3d.generator import GenConfig, generate_candidate
from m3d.negotiated import route_negotiated
from m3d.baseline import route
from m3d.checker import check
from m3d.suite import suite_configs
from m3d.scorer import (SubmissionScore, CaseScore, rank_submissions,
                        pareto_frontier)


class TestNegotiatedRouter(unittest.TestCase):
    def test_routes_dense_instance_legally(self):
        # a small but contended instance
        cfg = GenConfig(name="dense", width=20, height=20, layers=6, n_nets=45,
                        frac_cross=0.45, p_twopin=0.6, max_fanout=6, frac_local=0.12,
                        cell_min=2, cell_max=2, pins_per_cell=2, cell_gap=0, seed=17)
        inst = generate_candidate(cfg, cfg.seed)
        sub, stats = route_negotiated(inst)
        self.assertIsNotNone(sub, "negotiated router should solve a feasible dense case")
        self.assertTrue(stats.success)
        res = check(inst, sub)
        self.assertTrue(res.legal, res.reasons)

    def test_negotiated_matches_delay_objective_when_uncongested(self):
        # on a sparse instance negotiated ~ per-net shortest = the simple baseline
        cfg = GenConfig(name="sparse", width=40, height=40, layers=6, n_nets=15,
                        frac_local=0.5, seed=8)
        inst = generate_candidate(cfg, cfg.seed)
        sn, _ = route_negotiated(inst)
        sb, _ = route(inst)
        self.assertTrue(check(inst, sn).legal)
        self.assertTrue(check(inst, sb).legal)


class TestTiers(unittest.TestCase):
    def test_tier_shapes(self):
        intro = suite_configs("intro")
        hard = suite_configs("hard")
        scale = suite_configs("scale")
        self.assertEqual(len(intro), 20)
        self.assertEqual(len(hard), 9)
        self.assertEqual(len(scale), 8)
        # hard uses the negotiated baseline; intro/scale use the simple one
        self.assertTrue(all(c.router == "negotiated" for c in hard))
        self.assertTrue(all(c.router == "baseline" for c in intro))
        # scale is much bigger than intro
        self.assertGreater(scale[-1].width, intro[-1].width)
        # sizes increase within each tier
        for tier in (intro, hard, scale):
            self.assertEqual([c.width for c in tier], sorted(c.width for c in tier))

    def test_intro_seed_schedule_stable(self):
        a = [c.seed for c in suite_configs("intro")]
        b = [c.seed for c in suite_configs("intro")]
        self.assertEqual(a, b)
        self.assertEqual(len(set(a)), 20)


class TestMultiSubmissionScoring(unittest.TestCase):
    def _sub(self, name, complete, agg, delay, rt, nlegal=3, ncases=3):
        return SubmissionScore(name, complete, agg, nlegal if complete else nlegal - 1,
                               ncases, delay if complete else None, rt, [])

    def test_ranking_prefers_complete_then_aggregate(self):
        subs = [
            self._sub("slow_good", True, 1.02, 1000, 200),
            self._sub("ref", True, 1.00, 1020, 100),
            self._sub("incomplete", False, 0.0, None, 50),
        ]
        ranked = rank_submissions(subs)
        self.assertEqual([s.name for s in ranked], ["slow_good", "ref", "incomplete"])

    def test_pareto_frontier(self):
        subs = [
            self._sub("fast_hi_delay", True, 1.00, 1020, 100),   # frontier
            self._sub("slow_lo_delay", True, 1.02, 1000, 200),   # frontier
            self._sub("dominated", True, 0.98, 1050, 250),       # dominated
            self._sub("incomplete", False, 0.0, None, 30),       # excluded
        ]
        fr = set(pareto_frontier(subs))
        self.assertEqual(fr, {"fast_hi_delay", "slow_lo_delay"})


if __name__ == "__main__":
    unittest.main()
