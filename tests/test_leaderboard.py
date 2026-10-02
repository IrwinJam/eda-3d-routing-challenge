import os
import unittest

from m3d.cli import _render_leaderboard_md, _load_manifest, _load_runtimes
from m3d.scorer import score_submission_set, rank_submissions, pareto_frontier

HARD_SUITE = "benchmarks_hard"
HARD_SUBS = "submissions/hard"


class TestLeaderboardRender(unittest.TestCase):
    def test_render_is_deterministic_and_lists_seed_entries(self):
        a = _render_leaderboard_md("submissions")
        b = _render_leaderboard_md("submissions")
        self.assertEqual(a, b)                     # deterministic
        self.assertIn("## hard", a)
        for name in ("negotiated", "negotiated_x2", "negotiated_fast"):
            self.assertIn(name, a)

    def test_committed_leaderboard_is_current(self):
        # the invariant CI enforces with `leaderboard-all --check`
        self.assertTrue(os.path.exists("LEADERBOARD.md"))
        with open("LEADERBOARD.md", encoding="utf-8") as fh:
            on_disk = fh.read().strip()
        self.assertEqual(on_disk, _render_leaderboard_md("submissions").strip())


SEED_HARD = ("negotiated", "negotiated_x2", "negotiated_fast")


def _score_seed_entries(hard_root: str) -> dict:
    """Score only the three reference entries, whatever else is submitted.

    Scoring every directory under submissions/hard made this test fail for any
    new hard entry that ships a runtime.json and is not dominated by a seed (it
    joins the Pareto frontier), or for any incomplete entry whose name sorts
    after negotiated_fast."""
    man = _load_manifest(HARD_SUITE)
    subs = {}
    for name in SEED_HARD:
        d = os.path.join(hard_root, name)
        subs[name] = score_submission_set(man, HARD_SUITE, d, name, _load_runtimes(d))
    return subs


class TestSeedSubmissions(unittest.TestCase):
    def test_seed_hard_entries_score_as_expected(self):
        subs = _score_seed_entries(HARD_SUBS)
        # two complete, one incomplete
        self.assertTrue(subs["negotiated"].complete)
        self.assertTrue(subs["negotiated_x2"].complete)
        self.assertFalse(subs["negotiated_fast"].complete)
        # baseline == the 'negotiated' reference, so its aggregate is exactly 1.0
        self.assertAlmostEqual(subs["negotiated"].aggregate, 1.0, places=6)
        # complete submissions rank ahead of the incomplete one
        ranked = rank_submissions(list(subs.values()))
        self.assertEqual(ranked[-1].name, "negotiated_fast")
        # both complete entries are on the runtime-vs-delay frontier
        self.assertEqual(set(pareto_frontier(list(subs.values()))),
                         {"negotiated", "negotiated_x2"})


    def test_seed_checks_ignore_other_hard_entries(self):
        # a faster/better entry with a runtime.json, and an incomplete entry whose
        # name sorts after negotiated_fast, must not affect the seed assertions
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            for name in SEED_HARD:
                shutil.copytree(os.path.join(HARD_SUBS, name), os.path.join(tmp, name))
            shutil.copytree(os.path.join(HARD_SUBS, "negotiated_x2"), os.path.join(tmp, "a_new_router"))
            with open(os.path.join(tmp, "a_new_router", "runtime.json"), "w", encoding="utf-8") as fh:
                fh.write('{"case_0%d": 1.0' % 1 + "".join(', "case_0%d": 1.0' % i for i in range(2, 10)) + "}")
            shutil.copytree(os.path.join(HARD_SUBS, "negotiated_fast"), os.path.join(tmp, "zz_work_in_progress"))
            subs = _score_seed_entries(tmp)
            self.assertEqual(set(subs), set(SEED_HARD))
            self.assertEqual(rank_submissions(list(subs.values()))[-1].name, "negotiated_fast")
            self.assertEqual(set(pareto_frontier(list(subs.values()))), {"negotiated", "negotiated_x2"})


if __name__ == "__main__":
    unittest.main()
