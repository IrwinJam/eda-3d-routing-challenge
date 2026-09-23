import json
import unittest

from m3d.generator import GenConfig, generate_candidate, generate_feasible
from m3d.checker import check
from m3d.suite import suite_configs


class TestGenerator(unittest.TestCase):
    def test_deterministic(self):
        cfg = GenConfig(name="d", width=22, height=22, layers=6, n_nets=15, seed=7)
        a = generate_feasible(cfg).instance.to_dict()
        b = generate_feasible(cfg).instance.to_dict()
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))

    def test_every_pin_in_exactly_one_net(self):
        cfg = GenConfig(name="p", width=24, height=24, layers=6, n_nets=20, seed=3)
        inst = generate_feasible(cfg).instance
        seen = {}
        for net in inst.nets:
            for pid in net.pins():
                self.assertNotIn(pid, seen, f"pin {pid} in >1 net")
                seen[pid] = net.id
        self.assertEqual(set(seen), {p.id for p in inst.pins})
        # each net has exactly one driver + >=1 sink
        for net in inst.nets:
            self.assertGreaterEqual(len(net.sinks), 1)

    def test_reference_is_legal(self):
        cfg = GenConfig(name="f", width=26, height=26, layers=6, n_nets=25, seed=11)
        r = generate_feasible(cfg)
        res = check(r.instance, r.reference)
        self.assertTrue(res.legal, res.reasons)
        self.assertEqual(res.total_delay, r.baseline_total)

    def test_cross_die_present(self):
        cfg = GenConfig(name="x", width=26, height=26, layers=6, n_nets=30,
                        frac_cross=0.5, seed=5)
        inst = generate_feasible(cfg).instance
        pin = inst.pin_by_id()
        cross = sum(1 for n in inst.nets
                    if len({pin[p].die for p in n.pins()}) > 1)
        self.assertGreater(cross, 0)

    def test_suite_sizes_increase(self):
        cfgs = suite_configs()
        self.assertEqual(len(cfgs), 20)
        widths = [c.width for c in cfgs]
        nets = [c.n_nets for c in cfgs]
        self.assertEqual(widths, sorted(widths))
        self.assertEqual(nets, sorted(nets))
        self.assertLess(widths[0], widths[-1])
        self.assertLess(nets[0], nets[-1])
        # per-case seeds are distinct
        self.assertEqual(len({c.seed for c in cfgs}), 20)


if __name__ == "__main__":
    unittest.main()
