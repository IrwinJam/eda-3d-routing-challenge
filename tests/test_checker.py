import copy
import unittest

from m3d.model import Cell, Instance, Net, Pin, Submission, NetRoute
from m3d.checker import check


def two_net_instance():
    """3x3x1 grid, two 2-pin nets on layer 0, routable without conflict.

      net0: (0,0,0) -> (2,0,0)   along y=0
      net1: (0,2,0) -> (2,2,0)   along y=2
    """
    inst = Instance(
        name="t2", width=3, height=3, layers=1,
        layer_delay=[1], via_delay=5,
        cells=[Cell(0, 0, 0, 0, 3, 3)],
        pins=[Pin(0, 0, 0, 0, 0, 0), Pin(1, 0, 0, 2, 0, 0),
              Pin(2, 0, 0, 0, 2, 0), Pin(3, 0, 0, 2, 2, 0)],
        nets=[Net(0, 0, [1]), Net(1, 2, [3])],
    )
    good = Submission("t2", [
        NetRoute(0, [((0, 0, 0), (1, 0, 0)), ((1, 0, 0), (2, 0, 0))]),
        NetRoute(1, [((0, 2, 0), (1, 2, 0)), ((1, 2, 0), (2, 2, 0))]),
    ])
    return inst, good


class TestCheckerAcceptsLegal(unittest.TestCase):
    def test_legal(self):
        inst, good = two_net_instance()
        res = check(inst, good)
        self.assertTrue(res.legal, res.reasons)
        self.assertEqual(res.total_delay, 2 + 2)


class TestCheckerRejects(unittest.TestCase):
    def setUp(self):
        self.inst, self.good = two_net_instance()

    def _sub(self, routes):
        return Submission("t2", routes)

    def test_missing_net(self):
        bad = self._sub([self.good.routes[0]])  # drop net1
        res = check(self.inst, bad)
        self.assertFalse(res.legal)
        self.assertTrue(any("missing net" in r for r in res.reasons))

    def test_duplicate_net(self):
        bad = self._sub([self.good.routes[0], self.good.routes[0], self.good.routes[1]])
        res = check(self.inst, bad)
        self.assertFalse(res.legal)
        self.assertTrue(any("more than once" in r for r in res.reasons))

    def test_disconnected_pin(self):
        bad = self._sub([NetRoute(0, [((0, 0, 0), (1, 0, 0))]),  # sink (2,0,0) unreached
                         self.good.routes[1]])
        res = check(self.inst, bad)
        self.assertFalse(res.legal)
        self.assertTrue(any("not connected" in " ".join(n.reasons)
                            for n in res.nets if n.net == 0))

    def test_cycle(self):
        # add a redundant edge to make a cycle in net0 (needs a 2D loop)
        bad = self._sub([
            NetRoute(0, [((0, 0, 0), (1, 0, 0)), ((1, 0, 0), (2, 0, 0)),
                         ((2, 0, 0), (2, 1, 0)), ((2, 1, 0), (1, 1, 0)),
                         ((1, 1, 0), (1, 0, 0))]),   # loop back
            self.good.routes[1]])
        res = check(self.inst, bad)
        self.assertFalse(res.legal)
        self.assertTrue(any("not a tree" in " ".join(n.reasons)
                            for n in res.nets if n.net == 0))

    def test_short_shared_vertex(self):
        # net1 keeps its own path (0,2)->(1,2)->(2,2) and adds a branch down to
        # (1,0,0), a *non-pin* vertex that net0 also uses -> shared-vertex short.
        # Both nets stay individually legal, so the conflict is a genuine short.
        bad = self._sub([
            self.good.routes[0],
            NetRoute(1, [((0, 2, 0), (1, 2, 0)), ((1, 2, 0), (2, 2, 0)),
                         ((1, 2, 0), (1, 1, 0)), ((1, 1, 0), (1, 0, 0))])])
        res = check(self.inst, bad)
        self.assertFalse(res.legal)
        self.assertTrue(any("short" in r for r in res.reasons), res.reasons)
        self.assertIn((1, 0, 0), res.conflict_vertices)

    def test_illegal_diagonal_move(self):
        bad = self._sub([NetRoute(0, [((0, 0, 0), (1, 1, 0)), ((1, 1, 0), (2, 0, 0))]),
                         self.good.routes[1]])
        res = check(self.inst, bad)
        self.assertFalse(res.legal)
        self.assertTrue(any("illegal move" in " ".join(n.reasons)
                            for n in res.nets if n.net == 0))

    def test_out_of_bounds(self):
        bad = self._sub([NetRoute(0, [((0, 0, 0), (-1, 0, 0))]), self.good.routes[1]])
        res = check(self.inst, bad)
        self.assertFalse(res.legal)
        self.assertTrue(any("out of bounds" in " ".join(n.reasons)
                            for n in res.nets if n.net == 0))

    def test_route_through_other_pin(self):
        # net0 detours through (0,2,0), which is net1's driver pin
        bad = self._sub([
            NetRoute(0, [((0, 0, 0), (0, 1, 0)), ((0, 1, 0), (0, 2, 0)),
                         ((0, 2, 0), (1, 2, 0)), ((1, 2, 0), (1, 1, 0)),
                         ((1, 1, 0), (1, 0, 0)), ((1, 0, 0), (2, 0, 0))]),
            NetRoute(1, [((2, 2, 0), (2, 1, 0)), ((2, 1, 0), (2, 0, 0))])])
        # note: (2,0,0) is net0's sink; make net1 avoid it -> route net1 elsewhere
        bad = self._sub([
            NetRoute(0, [((0, 0, 0), (0, 1, 0)), ((0, 1, 0), (0, 2, 0)),  # (0,2,0)=net1 pin
                         ((0, 2, 0), (1, 2, 0)), ((1, 2, 0), (1, 1, 0)),
                         ((1, 1, 0), (1, 0, 0)), ((1, 0, 0), (2, 0, 0))]),
            self.good.routes[1]])
        res = check(self.inst, bad)
        self.assertFalse(res.legal)
        joined = " ".join(res.reasons) + " " + " ".join(
            r for n in res.nets for r in n.reasons)
        self.assertTrue("pin" in joined and ("through" in joined or "short" in joined))

    def test_skip_layer_via(self):
        inst = Instance("t3", 1, 1, 3, [3, 1, 3], 2,
                        cells=[Cell(0, 0, 0, 0, 1, 1), Cell(1, 1, 0, 0, 1, 1)],
                        pins=[Pin(0, 0, 0, 0, 0, 0), Pin(1, 1, 1, 0, 0, 2)],
                        nets=[Net(0, 0, [1])])
        bad = Submission("t3", [NetRoute(0, [((0, 0, 0), (0, 0, 2))])])  # skip layer 1
        res = check(inst, bad)
        self.assertFalse(res.legal)
        self.assertTrue(any("illegal move" in " ".join(n.reasons) for n in res.nets))


if __name__ == "__main__":
    unittest.main()
