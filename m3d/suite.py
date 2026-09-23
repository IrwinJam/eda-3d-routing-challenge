"""The released 20-case benchmark suite: a fixed master seed, a reproducible
per-case seed schedule, and a size ladder that grows the grid, cell/pin count and
net count together, mixing local and long-distance connections.

Building the suite writes, for each case:

* ``benchmarks/case_NN.json``            — the participant-facing instance;
* ``benchmarks/reference/case_NN.sol.json`` — the verified reference solution
  (baseline output), kept separate from participant inputs;

and a ``benchmarks/suite.json`` manifest recording every seed, the generation
parameters and the baseline total for each case (the scoring baseline).
"""
from __future__ import annotations

import json
import os
import random
import time
from dataclasses import asdict
from typing import Dict, List

from .generator import GenConfig, generate_feasible

MASTER_SEED = 20260923
N_CASES = 20
DEFAULT_LAYERS = 6          # configurable; the final layer count can change here


def suite_configs(layers: int = DEFAULT_LAYERS,
                  master_seed: int = MASTER_SEED) -> List[GenConfig]:
    """Return the 20 GenConfigs (deterministic per-case seed schedule)."""
    base_rng = random.Random(master_seed)
    cfgs: List[GenConfig] = []
    for i in range(N_CASES):
        case_seed = base_rng.randrange(1, 2 ** 31 - 1)
        side = 16 + 4 * i                       # 16 .. 92
        n_nets = 6 + 7 * i                      # 6 .. 139
        cfg = GenConfig(
            name=f"case_{i + 1:02d}",
            width=side,
            height=side,
            layers=layers,
            center_delay=1,
            layer_slope=1,
            via_delay=3,
            n_nets=n_nets,
            frac_cross=0.4,
            p_twopin=max(0.45, 0.70 - 0.015 * i),
            max_fanout=4 + i // 5,              # 4 .. 7
            frac_local=0.5,
            cell_min=2,
            cell_max=4,
            pins_per_cell=3,
            seed=case_seed,
            master_seed=master_seed,
            max_attempts=16,
        )
        cfgs.append(cfg)
    return cfgs


def build_suite(out_dir: str, layers: int = DEFAULT_LAYERS,
                master_seed: int = MASTER_SEED, verbose: bool = True) -> Dict:
    ref_dir = os.path.join(out_dir, "reference")
    os.makedirs(ref_dir, exist_ok=True)
    manifest = {
        "format": "m3d-suite",
        "master_seed": master_seed,
        "layers": layers,
        "n_cases": N_CASES,
        "cases": [],
    }
    for cfg in suite_configs(layers=layers, master_seed=master_seed):
        t0 = time.time()
        result = generate_feasible(cfg)
        dt = time.time() - t0
        inst = result.instance
        inst_file = f"{cfg.name}.json"
        ref_file = os.path.join("reference", f"{cfg.name}.sol.json")
        inst.save(os.path.join(out_dir, inst_file))
        result.reference.save(os.path.join(out_dir, ref_file))
        entry = {
            "name": cfg.name,
            "seed": inst.seed,
            "width": inst.width,
            "height": inst.height,
            "layers": inst.layers,
            "n_cells": len(inst.cells),
            "n_pins": len(inst.pins),
            "n_nets": len(inst.nets),
            "baseline_total": result.baseline_total,
            "gen_attempts": result.attempts,
            "gen_seconds": round(dt, 2),
            "instance_file": inst_file,
            "reference_file": ref_file,
        }
        manifest["cases"].append(entry)
        if verbose:
            print(f"  {cfg.name}: {inst.width}x{inst.height}x{inst.layers} grid, "
                  f"{len(inst.nets)} nets, {len(inst.pins)} pins, "
                  f"baseline={result.baseline_total}, "
                  f"attempts={result.attempts}, {dt:.1f}s")
    with open(os.path.join(out_dir, "suite.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    return manifest


def load_manifest(out_dir: str) -> Dict:
    with open(os.path.join(out_dir, "suite.json")) as fh:
        return json.load(fh)
