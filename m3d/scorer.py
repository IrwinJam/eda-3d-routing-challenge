"""Scoring and the normalized leaderboard.

Per case we report the *raw* total routing delay recomputed by the independent
checker. For the aggregate leaderboard we normalize each case against the
baseline so that a large case cannot dominate simply because its absolute delay
is bigger.

Normalization
-------------
For a legal submission on case ``c`` with total delay ``s_c`` and baseline total
``b_c``::

    ratio_c = b_c / s_c          # > 1 means better (lower delay) than baseline

The aggregate score is the geometric mean of the per-case ratios::

    aggregate = ( product_c ratio_c ) ** (1 / N)

The geometric mean is scale-free, so every case contributes equally regardless
of its absolute delay. Higher is better; the baseline itself scores exactly 1.0.

A complete ranked submission must be legal on **all** cases. If any case is
illegal (or missing) the submission is marked incomplete and receives an
aggregate score of 0.0 — partial routing never earns a competitive score.

Runtime is recorded separately from quality and never affects the delay score.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .checker import CheckResult, check
from .model import Instance, Submission


@dataclass
class CaseScore:
    case: str
    legal: bool
    total_delay: Optional[int]
    baseline_delay: Optional[int]
    ratio: Optional[float]        # baseline/total, None if illegal
    runtime_s: Optional[float] = None
    reasons: List[str] = field(default_factory=list)


@dataclass
class Leaderboard:
    complete: bool
    aggregate_score: float
    n_cases: int
    n_legal: int
    cases: List[CaseScore]
    formula: str = ("aggregate = geomean_c(baseline_total_c / submission_total_c); "
                    "higher is better; baseline scores 1.0; all cases must be legal "
                    "for a complete ranked submission (else aggregate = 0.0)")

    def to_dict(self) -> Dict:
        return {
            "format": "m3d-leaderboard",
            "complete": self.complete,
            "aggregate_score": self.aggregate_score,
            "n_cases": self.n_cases,
            "n_legal": self.n_legal,
            "formula": self.formula,
            "cases": [
                {
                    "case": c.case,
                    "legal": c.legal,
                    "total_delay": c.total_delay,
                    "baseline_delay": c.baseline_delay,
                    "ratio": c.ratio,
                    "runtime_s": c.runtime_s,
                    "reasons": c.reasons,
                }
                for c in self.cases
            ],
        }


def score_case(inst: Instance, sub: Submission, baseline_delay: int,
               runtime_s: Optional[float] = None) -> CaseScore:
    res: CheckResult = check(inst, sub)
    if res.legal and res.total_delay and res.total_delay > 0:
        ratio = baseline_delay / res.total_delay
        return CaseScore(inst.name, True, res.total_delay, baseline_delay, ratio,
                         runtime_s, [])
    reasons = list(res.reasons)
    for n in res.nets:
        if not n.legal:
            reasons.append(f"net {n.net}: " + "; ".join(n.reasons or ["illegal"]))
    return CaseScore(inst.name, False, res.total_delay, baseline_delay, None,
                     runtime_s, reasons[:20])


def leaderboard(case_scores: List[CaseScore]) -> Leaderboard:
    n = len(case_scores)
    n_legal = sum(1 for c in case_scores if c.legal)
    complete = n > 0 and n_legal == n
    if complete:
        log_sum = sum(math.log(c.ratio) for c in case_scores if c.ratio)
        aggregate = math.exp(log_sum / n)
    else:
        aggregate = 0.0
    return Leaderboard(complete=complete, aggregate_score=aggregate,
                       n_cases=n, n_legal=n_legal, cases=case_scores)


# --------------------------------------------------------------------------- #
# Multi-submission leaderboard + Pareto support
# --------------------------------------------------------------------------- #
@dataclass
class SubmissionScore:
    name: str
    complete: bool
    aggregate: float
    n_legal: int
    n_cases: int
    total_delay: Optional[int]        # sum of raw delays over cases (None if incomplete)
    total_runtime: Optional[float]    # sum of per-case runtimes (None if unknown)
    cases: List[CaseScore]

    def to_dict(self) -> Dict:
        return {
            "name": self.name, "complete": self.complete,
            "aggregate": self.aggregate, "n_legal": self.n_legal,
            "n_cases": self.n_cases, "total_delay": self.total_delay,
            "total_runtime": self.total_runtime,
            "cases": [
                {"case": c.case, "legal": c.legal, "total_delay": c.total_delay,
                 "baseline_delay": c.baseline_delay, "ratio": c.ratio,
                 "runtime_s": c.runtime_s} for c in self.cases
            ],
        }


def score_submission_set(manifest: Dict, suite_dir: str, submission_dir: str,
                         name: str, runtimes: Optional[Dict[str, float]] = None
                         ) -> SubmissionScore:
    import os
    from .model import Instance, Submission
    runtimes = runtimes or {}
    cases: List[CaseScore] = []
    for c in manifest["cases"]:
        inst = Instance.load(os.path.join(suite_dir, c["instance_file"]))
        sol = os.path.join(submission_dir, f"{inst.name}.sol.json")
        rt = runtimes.get(inst.name)
        if not os.path.exists(sol):
            cases.append(CaseScore(inst.name, False, None, c["baseline_total"],
                                   None, rt, ["submission file missing"]))
            continue
        cases.append(score_case(inst, Submission.load(sol), c["baseline_total"], rt))
    lb = leaderboard(cases)
    total_delay = sum(c.total_delay for c in cases) if lb.complete else None
    have_rt = [c.runtime_s for c in cases if c.runtime_s is not None]
    total_runtime = sum(have_rt) if have_rt else None
    return SubmissionScore(name, lb.complete, lb.aggregate_score, lb.n_legal,
                           lb.n_cases, total_delay, total_runtime, cases)


def rank_submissions(subs: List[SubmissionScore]) -> List[SubmissionScore]:
    # complete submissions first, then by aggregate desc, then total delay asc
    return sorted(subs, key=lambda s: (not s.complete, -s.aggregate,
                                       s.total_delay if s.total_delay is not None else 1 << 62))


def pareto_frontier(points: List["SubmissionScore"]) -> List[str]:
    """Names on the runtime-vs-total-delay Pareto frontier (minimize both).

    Only complete submissions with a known runtime are eligible.
    """
    elig = [s for s in points if s.complete and s.total_runtime is not None
            and s.total_delay is not None]
    names = []
    for s in elig:
        dominated = any(
            o is not s and o.total_runtime <= s.total_runtime
            and o.total_delay <= s.total_delay
            and (o.total_runtime < s.total_runtime or o.total_delay < s.total_delay)
            for o in elig)
        if not dominated:
            names.append(s.name)
    return names
