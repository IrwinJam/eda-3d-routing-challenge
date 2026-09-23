"""Command-line interface: ``python -m m3d.cli <command> ...``

Commands
--------
  generate        build the deterministic 20-case suite
  baseline        run the baseline router on one case
  baseline-suite  run the baseline on every case in a suite
  evaluate        check + score one submission against one case
  score-suite     check + score a full 20-case submission (leaderboard)
  visualize       render a case (and optional submission) to PNG
  info            print a short summary of a case
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Dict, Optional

from .baseline import route
from .checker import check
from .model import Instance, Submission
from .scorer import CaseScore, leaderboard, score_case


def _load_manifest(suite_dir: str) -> Dict:
    with open(os.path.join(suite_dir, "suite.json")) as fh:
        return json.load(fh)


def _baseline_total_for(suite_dir: Optional[str], case_name: str,
                        explicit: Optional[int]) -> Optional[int]:
    if explicit is not None:
        return explicit
    if suite_dir:
        man = _load_manifest(suite_dir)
        for c in man["cases"]:
            if c["name"] == case_name:
                return c["baseline_total"]
    return None


# --------------------------------------------------------------------------- #
def cmd_generate(args: argparse.Namespace) -> int:
    from .suite import build_suite, MASTER_SEED
    os.makedirs(args.out, exist_ok=True)
    print(f"generating 20-case suite into {args.out} "
          f"(layers={args.layers}, master_seed={args.master_seed}) ...")
    man = build_suite(args.out, layers=args.layers, master_seed=args.master_seed)
    print(f"done: {len(man['cases'])} cases; manifest at "
          f"{os.path.join(args.out, 'suite.json')}")
    return 0


def cmd_baseline(args: argparse.Namespace) -> int:
    inst = Instance.load(args.case)
    t0 = time.time()
    sub, stats = route(inst, order=args.order, rip_limit=args.rip_limit,
                       ops_factor=args.ops_factor)
    dt = time.time() - t0
    if sub is None:
        print(f"baseline FAILED to route {inst.name}: "
              f"routed {stats.routed_nets}/{stats.total_nets} nets, "
              f"rip-ups={stats.rip_ups}, ops={stats.ops}", file=sys.stderr)
        return 2
    res = check(inst, sub)
    out = args.out or (os.path.splitext(args.case)[0] + ".baseline.sol.json")
    sub.save(out)
    print(f"{inst.name}: legal={res.legal} total_delay={res.total_delay} "
          f"nets={stats.total_nets} rip_ups={stats.rip_ups} time={dt:.2f}s")
    print(f"wrote submission -> {out}")
    return 0 if res.legal else 3


def cmd_baseline_suite(args: argparse.Namespace) -> int:
    man = _load_manifest(args.suite)
    os.makedirs(args.out_dir, exist_ok=True)
    ok = True
    for c in man["cases"]:
        inst = Instance.load(os.path.join(args.suite, c["instance_file"]))
        t0 = time.time()
        sub, stats = route(inst, order=args.order)
        dt = time.time() - t0
        if sub is None:
            print(f"  {inst.name}: FAILED ({stats.routed_nets}/{stats.total_nets})")
            ok = False
            continue
        res = check(inst, sub)
        out = os.path.join(args.out_dir, f"{inst.name}.sol.json")
        sub.save(out)
        print(f"  {inst.name}: legal={res.legal} total={res.total_delay} time={dt:.2f}s")
        ok = ok and res.legal
    return 0 if ok else 3


def cmd_evaluate(args: argparse.Namespace) -> int:
    inst = Instance.load(args.case)
    sub = Submission.load(args.sol)
    res = check(inst, sub)
    baseline_total = _baseline_total_for(args.suite, inst.name, args.baseline)
    print(f"{inst.name}: legal={res.legal} total_delay={res.total_delay}")
    if not res.legal:
        for r in res.reasons[:10]:
            print(f"  ! {r}")
        for n in res.nets:
            if not n.legal:
                print(f"  ! net {n.net}: {'; '.join(n.reasons) or 'illegal'}")
    if baseline_total is not None and res.legal and res.total_delay:
        cs = score_case(inst, sub, baseline_total)
        print(f"  baseline={baseline_total} ratio={cs.ratio:.4f} "
              f"(>1 beats baseline)")
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(res.to_dict(), fh, indent=1)
        print(f"wrote result -> {args.out}")
    return 0 if res.legal else 1


def cmd_score_suite(args: argparse.Namespace) -> int:
    man = _load_manifest(args.suite)
    runtimes: Dict[str, float] = {}
    if args.runtimes:
        with open(args.runtimes) as fh:
            runtimes = json.load(fh)
    scores = []
    for c in man["cases"]:
        inst = Instance.load(os.path.join(args.suite, c["instance_file"]))
        sol_path = os.path.join(args.submission_dir, f"{inst.name}.sol.json")
        if not os.path.exists(sol_path):
            scores.append(CaseScore(inst.name, False, None, c["baseline_total"],
                                    None, runtimes.get(inst.name),
                                    ["submission file missing"]))
            continue
        sub = Submission.load(sol_path)
        scores.append(score_case(inst, sub, c["baseline_total"],
                                 runtimes.get(inst.name)))
    lb = leaderboard(scores)
    for cs in lb.cases:
        flag = "OK " if cs.legal else "BAD"
        ratio = f"{cs.ratio:.4f}" if cs.ratio else "  -   "
        print(f"  [{flag}] {cs.case}: total={cs.total_delay} "
              f"baseline={cs.baseline_delay} ratio={ratio}")
    print(f"complete={lb.complete}  legal={lb.n_legal}/{lb.n_cases}  "
          f"AGGREGATE={lb.aggregate_score:.4f}")
    print(f"formula: {lb.formula}")
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(lb.to_dict(), fh, indent=1)
        print(f"wrote leaderboard -> {args.out}")
    return 0 if lb.complete else 1


def cmd_visualize(args: argparse.Namespace) -> int:
    from .viz import visualize
    inst = Instance.load(args.case)
    sub = Submission.load(args.sol) if args.sol else None
    out = args.out or (os.path.splitext(args.case)[0] +
                       (f".layer{args.layer}" if args.layer is not None else "") + ".png")
    visualize(inst, sub, layer=args.layer, out_path=out, show=args.show)
    print(f"wrote visualization -> {out}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    inst = Instance.load(args.case)
    n_cross = 0
    p2n = inst.pin_to_net()
    for net in inst.nets:
        dies = {inst.pin_by_id()[p].die for p in net.pins()}
        if len(dies) > 1:
            n_cross += 1
    fanouts = [len(n.sinks) for n in inst.nets]
    print(f"{inst.name}: {inst.width}x{inst.height}x{inst.layers} grid")
    print(f"  layer_delay={inst.layer_delay} via_delay={inst.via_delay}")
    print(f"  cells={len(inst.cells)} pins={len(inst.pins)} nets={len(inst.nets)}")
    print(f"  cross-die nets={n_cross} ({100*n_cross/max(1,len(inst.nets)):.0f}%)")
    print(f"  fanout: min={min(fanouts)} max={max(fanouts)} "
          f"avg={sum(fanouts)/len(fanouts):.2f}")
    print(f"  seed={inst.seed} master_seed={inst.master_seed}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="m3d", description="M3D routing challenge toolkit")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="build the deterministic 20-case suite")
    g.add_argument("--out", default="benchmarks")
    g.add_argument("--layers", type=int, default=6)
    g.add_argument("--master-seed", type=int, default=20260923, dest="master_seed")
    g.set_defaults(func=cmd_generate)

    b = sub.add_parser("baseline", help="run the baseline router on one case")
    b.add_argument("--case", required=True)
    b.add_argument("--out", default=None)
    b.add_argument("--order", default="bbox_desc",
                   choices=["bbox_desc", "bbox_asc", "id"])
    b.add_argument("--rip-limit", type=int, default=40, dest="rip_limit")
    b.add_argument("--ops-factor", type=int, default=200, dest="ops_factor")
    b.set_defaults(func=cmd_baseline)

    bs = sub.add_parser("baseline-suite", help="run the baseline on every case")
    bs.add_argument("--suite", default="benchmarks")
    bs.add_argument("--out-dir", required=True, dest="out_dir")
    bs.add_argument("--order", default="bbox_desc",
                    choices=["bbox_desc", "bbox_asc", "id"])
    bs.set_defaults(func=cmd_baseline_suite)

    e = sub.add_parser("evaluate", help="check + score one submission")
    e.add_argument("--case", required=True)
    e.add_argument("--sol", required=True)
    e.add_argument("--suite", default=None, help="suite dir for the baseline total")
    e.add_argument("--baseline", type=int, default=None, help="explicit baseline total")
    e.add_argument("--out", default=None)
    e.set_defaults(func=cmd_evaluate)

    s = sub.add_parser("score-suite", help="score a full 20-case submission")
    s.add_argument("--suite", default="benchmarks")
    s.add_argument("--submission-dir", required=True, dest="submission_dir")
    s.add_argument("--runtimes", default=None, help="optional JSON {case: seconds}")
    s.add_argument("--out", default=None)
    s.set_defaults(func=cmd_score_suite)

    v = sub.add_parser("visualize", help="render a case to PNG")
    v.add_argument("--case", required=True)
    v.add_argument("--sol", default=None)
    v.add_argument("--layer", type=int, default=None)
    v.add_argument("--out", default=None)
    v.add_argument("--show", action="store_true")
    v.set_defaults(func=cmd_visualize)

    i = sub.add_parser("info", help="print a summary of a case")
    i.add_argument("--case", required=True)
    i.set_defaults(func=cmd_info)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
