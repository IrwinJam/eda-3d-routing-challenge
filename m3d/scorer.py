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
