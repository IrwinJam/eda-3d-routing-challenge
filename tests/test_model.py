import unittest

from m3d.model import (Cell, Instance, Net, Pin, Submission, NetRoute,
                      layer_delay_profile)
from m3d.checker import check


def delay_instance():
    """A tiny, hand-built instance with known delays.

    layers=3, layer_delay=[3,1,3], via_delay=2. One 3-pin net:
      driver D=(0,0,0), sink A=(2,0,0) bottom, sink B=(2,0,2) top.
    """
    inst = Instance(
        name="t", width=3, height=1, layers=3,
        layer_delay=[3, 1, 3], via_delay=2,
        cells=[Cell(0, 0, 0, 0, 3, 1), Cell(1, 1, 2, 0, 1, 1)],
        pins=[Pin(0, 0, 0, 0, 0, 0), Pin(1, 0, 0, 2, 0, 0), Pin(2, 1, 1, 2, 0, 2)],
        nets=[Net(0, driver=0, sinks=[1, 2])],
    )
    good = Submission(instance="t", routes=[NetRoute(0, [
        ((0, 0, 0), (1, 0, 0)),
        ((1, 0, 0), (2, 0, 0)),
        ((2, 0, 0), (2, 0, 1)),
        ((2, 0, 1), (2, 0, 2)),
    ])])
    return inst, good


class TestDelayProfile(unittest.TestCase):
    def test_symmetric_min_middle_integer(self):
        for layers in range(1, 9):
            prof = layer_delay_profile(layers, center_delay=1, slope=1)
            self.assertEqual(len(prof), layers)
            self.assertEqual(prof, prof[::-1], "profile must be symmetric")
            self.assertTrue(all(isinstance(d, int) and d >= 1 for d in prof))
            mid = prof[layers // 2]
            self.assertLessEqual(mid, prof[0])
            self.assertLessEqual(mid, prof[-1])

    def test_specific_values(self):
        self.assertEqual(layer_delay_profile(6, 1, 1), [6, 4, 2, 2, 4, 6])
        self.assertEqual(layer_delay_profile(5, 1, 1), [5, 3, 1, 3, 5])
        self.assertEqual(layer_delay_profile(4, 2, 1), [5, 3, 3, 5])

    def test_edge_delay(self):
        inst, _ = delay_instance()
        self.assertEqual(inst.edge_delay((0, 0, 0), (1, 0, 0)), 3)  # layer 0
        self.assertEqual(inst.edge_delay((2, 0, 0), (2, 0, 1)), 2)  # via
        with self.assertRaises(ValueError):
            inst.edge_delay((0, 0, 0), (1, 1, 0))                   # diagonal
        with self.assertRaises(ValueError):
            inst.edge_delay((0, 0, 0), (0, 0, 2))                   # skip layer


class TestPathDelay(unittest.TestCase):
    def test_multipin_shared_segment_counts_per_sink(self):
        inst, good = delay_instance()
        res = check(inst, good)
        self.assertTrue(res.legal, res.reasons)
        # A path = 3+3 = 6 ; B path = 3+3+2+2 = 10 ; shared 0-1-2 counted in both
        self.assertEqual(res.nets[0].delay, 16)
        self.assertEqual(res.total_delay, 16)


class TestJsonRoundTrip(unittest.TestCase):
    def test_instance_and_submission_roundtrip(self):
        inst, good = delay_instance()
        self.assertEqual(Instance.from_dict(inst.to_dict()).to_dict(), inst.to_dict())
        self.assertEqual(Submission.from_dict(good.to_dict()).to_dict(), good.to_dict())


if __name__ == "__main__":
    unittest.main()
