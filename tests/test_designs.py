import os
import unittest

from m3d.designs import (parse_blif, build_design_instance, generate_design_feasible,
                         DesignConfig, DESIGN_SPECS, BLIF_DIR, _rcm_order,
                         _module_adjacency, _build_modules, _live_signals)
from m3d.checker import check


def _read(path):
    with open(path) as fh:
        return fh.read()

TINY = """
# a tiny 2-gate netlist
.model t
.inputs a b c
.outputs f
.names a b g
11 1
.names g c f
11 1
.end
"""


class TestBlifParse(unittest.TestCase):
    def test_parse_tiny(self):
        nl = parse_blif(TINY)
        self.assertEqual(nl.inputs, ["a", "b", "c"])
        self.assertEqual(nl.outputs, ["f"])
        self.assertEqual(len(nl.nodes), 2)
        self.assertEqual(nl.nodes[0], ("g", ["a", "b"]))
        self.assertEqual(nl.nodes[1], ("f", ["g", "c"]))

    def test_parse_continuation(self):
        nl = parse_blif(".model m\n.inputs a b \\\n c d\n.outputs o\n.end\n")
        self.assertEqual(nl.inputs, ["a", "b", "c", "d"])

    def test_vendored_files_parse(self):
        for spec in DESIGN_SPECS:
            path = os.path.join(BLIF_DIR, spec["blif"])
            self.assertTrue(os.path.exists(path), path)
            nl = parse_blif(_read(path))
            self.assertGreater(len(nl.nodes), 0)
            self.assertGreater(len(nl.inputs), 0)


class TestInstanceMapping(unittest.TestCase):
    def test_pins_belong_to_exactly_one_net(self):
        nl = parse_blif(TINY)
        inst = build_design_instance("t", nl, DesignConfig(name="t"), channel=3)
        # model invariant: every pin is in exactly one net
        seen = {}
        for n in inst.nets:
            for pid in n.pins():
                self.assertNotIn(pid, seen, f"pin {pid} in >1 net")
                seen[pid] = n.id
        self.assertEqual(set(seen), {p.id for p in inst.pins})
        # each net has one driver and >=1 sink
        for n in inst.nets:
            self.assertGreaterEqual(len(n.sinks), 1)

    def test_cells_do_not_overlap_within_a_die(self):
        nl = parse_blif(TINY)
        inst = build_design_instance("t", nl, DesignConfig(name="t"), channel=3)
        for die in (0, 1):
            occ = set()
            for c in (c for c in inst.cells if c.die == die):
                for x in range(c.x, c.x + c.w):
                    for y in range(c.y, c.y + c.h):
                        self.assertNotIn((x, y), occ, "cell overlap on a die")
                        occ.add((x, y))

    def test_tiny_design_routes_legally(self):
        nl = parse_blif(TINY)
        res = generate_design_feasible("t", nl, DesignConfig(name="t", router="baseline"))
        self.assertTrue(check(res.instance, res.reference).legal)


class TestRCM(unittest.TestCase):
    def test_rcm_deterministic_and_complete(self):
        nl = parse_blif(_read(os.path.join(BLIF_DIR, "ctrl.blif")))
        mods = _build_modules(nl)
        live = _live_signals(mods)
        adj = _module_adjacency(mods, live)
        ids = [m.mid for m in mods]
        a = _rcm_order(ids, adj)
        b = _rcm_order(ids, adj)
        self.assertEqual(a, b)                       # deterministic
        self.assertEqual(sorted(a), sorted(ids))     # a permutation of all ids


if __name__ == "__main__":
    unittest.main()
