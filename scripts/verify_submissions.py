#!/usr/bin/env python3
"""Verify every submission under submissions/<tier>/<name>/.

For each present `<case>.sol.json`, re-run the independent checker against the
canonical instance. Fails (exit 1) if any present solution is illegal or
unparseable. Missing cases are allowed (that submission is just 'incomplete' and
stays unranked) -- only *broken* solutions fail the build.

Usage: python scripts/verify_submissions.py [submissions_root]
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from m3d.model import Instance, Submission           # noqa: E402
from m3d.checker import check                         # noqa: E402
from m3d.cli import _tier_dir_map, _load_manifest, _submission_entries  # noqa: E402


def main(root: str = "submissions") -> int:
    # report lines contain non-ASCII (✓, —); don't crash on a cp1252 Windows console
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    tier_dirs = _tier_dir_map()
    errors = []
    checked = 0
    if not os.path.isdir(root):
        print(f"no submissions dir at {root!r}; nothing to verify")
        return 0
    for tier in sorted(os.listdir(root)):
        troot = os.path.join(root, tier)
        # tier suites live at the repo root; resolve them from there so the
        # script also works when run from another directory
        suite_dir = tier_dirs.get(tier)
        if suite_dir and not os.path.isabs(suite_dir):
            suite_dir = os.path.join(REPO_ROOT, suite_dir)
        if not os.path.isdir(troot) or tier.startswith("_"):
            continue
        if not suite_dir or not os.path.exists(os.path.join(suite_dir, "suite.json")):
            errors.append(f"{tier}: unknown tier (no suite dir); "
                          f"valid tiers: {sorted(tier_dirs)}")
            continue
        man = _load_manifest(suite_dir)
        insts = {c["name"]: os.path.join(suite_dir, c["instance_file"])
                 for c in man["cases"]}
        for name, d in _submission_entries(troot):
            present = legal = 0
            for cname, ipath in insts.items():
                sol = os.path.join(d, f"{cname}.sol.json")
                if not os.path.exists(sol):
                    continue
                present += 1
                try:
                    res = check(Instance.load(ipath), Submission.load(sol))
                except Exception as exc:
                    errors.append(f"{tier}/{name}/{cname}: unreadable ({exc})")
                    continue
                checked += 1
                if res.legal:
                    legal += 1
                else:
                    why = list(res.reasons) + [
                        f"net {n.net}: " + "; ".join(n.reasons or ["illegal"])
                        for n in res.nets if not n.legal]
                    more = f" (+{len(why) - 5} more)" if len(why) > 5 else ""
                    errors.append(f"{tier}/{name}/{cname}: ILLEGAL — {why[:5]}{more}")
            status = "complete" if legal == len(insts) else "incomplete"
            print(f"  {tier}/{name}: {legal}/{len(insts)} legal "
                  f"({present} present) [{status}]")
    print(f"checked {checked} solution file(s)")
    if errors:
        print("\nVERIFICATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("all present solutions are legal ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "submissions"))
