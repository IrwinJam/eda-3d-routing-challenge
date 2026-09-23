"""Deterministic benchmark generator with a verified-feasible guarantee.

Every released instance is produced by:

1. planning the nets (count, size distribution, cross-die fraction, locality);
2. placing non-overlapping rectangular cells and grid-aligned pins that supply
   exactly the number of bottom/top pins the plan needs;
3. assigning pins to nets honoring the requested locality (local nets take
   nearby pins, long nets take spread-out pins);
4. routing the candidate with the baseline router and validating that route with
   the independent checker.

If step 4 fails, the candidate is discarded and regenerated from a fresh derived
seed (and, after several misses, a slightly larger grid). An accepted instance is
therefore guaranteed to have at least one checker-verified legal solution — the
baseline output, which is stored separately as the reference solution and also
serves as the per-case scoring baseline.

Determinism note: generation uses Python's ``random.Random`` (Mersenne Twister),
which is stable across CPython versions for a given seed and call sequence.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

from . import baseline as _baseline
from .checker import check
from .model import (BOTTOM_DIE, TOP_DIE, Cell, Instance, Net, Pin, Submission,
                    layer_delay_profile)


@dataclass
class GenConfig:
    name: str = "case"
    width: int = 24
    height: int = 24
    layers: int = 6
    # delay profile (stored explicitly on the instance)
    center_delay: int = 1
    layer_slope: int = 1
    via_delay: int = 3
    # nets
    n_nets: int = 12
    frac_cross: float = 0.4       # fraction of nets that span both dies
    p_twopin: float = 0.6         # fraction of nets that are simple 2-pin nets
    max_fanout: int = 5           # multi-pin nets have 2..max_fanout sinks
    frac_local: float = 0.5       # fraction of nets whose pins are chosen nearby
    # cells / pins
    cell_min: int = 2             # cell footprint side (vertices)
    cell_max: int = 4
    pins_per_cell: int = 3        # up to this many pins per cell
    # feasibility search
    seed: int = 0
    master_seed: int = 0
    max_attempts: int = 16
    baseline_order: str = "bbox_desc"

    def to_params(self) -> Dict:
        return asdict(self)


@dataclass
class _NetPlan:
    cross: bool
    local: bool
    size: int                 # total pins
    n_bottom: int
    n_top: int
    die: int                  # for same-die nets (BOTTOM/TOP); -1 for cross


def _plan_nets(cfg: GenConfig, rng: random.Random) -> List[_NetPlan]:
    plans: List[_NetPlan] = []
    for _ in range(cfg.n_nets):
        cross = rng.random() < cfg.frac_cross
        local = rng.random() < cfg.frac_local
        if rng.random() < cfg.p_twopin:
            size = 2
        else:
            size = rng.randint(3, max(3, cfg.max_fanout + 1))
        if cross:
            nb = rng.randint(1, size - 1)
            nt = size - nb
            plans.append(_NetPlan(True, local, size, nb, nt, -1))
        else:
            die = rng.choice([BOTTOM_DIE, TOP_DIE])
            if die == BOTTOM_DIE:
                plans.append(_NetPlan(False, local, size, size, 0, die))
            else:
                plans.append(_NetPlan(False, local, size, 0, size, die))
    return plans


def _place_pins(die: int, n_pins: int, cfg: GenConfig, rng: random.Random,
                start_cell_id: int, start_pin_id: int,
                z: int) -> Tuple[List[Cell], List[Pin]]:
    """Place non-overlapping cells on one die, each carrying some pins, until
    exactly ``n_pins`` pins exist. Returns (cells, pins)."""
    cells: List[Cell] = []
    pins: List[Pin] = []
    occupied: List[Tuple[int, int, int, int]] = []  # x0,y0,x1,y1 inclusive
    cid = start_cell_id
    pid = start_pin_id
    tries_budget = 2000 + 200 * n_pins
    tries = 0
    while len(pins) < n_pins and tries < tries_budget:
        tries += 1
        w = rng.randint(cfg.cell_min, cfg.cell_max)
        h = rng.randint(cfg.cell_min, cfg.cell_max)
        if w > cfg.width or h > cfg.height:
            continue
        x = rng.randint(0, cfg.width - w)
        y = rng.randint(0, cfg.height - h)
        x1, y1 = x + w - 1, y + h - 1
        # non-overlap on this die (1-vertex separation to leave routing room)
        clash = False
        for (ox0, oy0, ox1, oy1) in occupied:
            if not (x1 < ox0 - 1 or x > ox1 + 1 or y1 < oy0 - 1 or y > oy1 + 1):
                clash = True
                break
        if clash:
            continue
        occupied.append((x, y, x1, y1))
        cells.append(Cell(id=cid, die=die, x=x, y=y, w=w, h=h))
        # pins for this cell
        capacity = w * h
        want = min(rng.randint(1, cfg.pins_per_cell), capacity, n_pins - len(pins))
        verts = [(vx, vy) for vx in range(x, x1 + 1) for vy in range(y, y1 + 1)]
        rng.shuffle(verts)
        for (vx, vy) in verts[:want]:
            pins.append(Pin(id=pid, cell=cid, die=die, x=vx, y=vy, z=z))
            pid += 1
        cid += 1
    if len(pins) < n_pins:
        raise _PlacementError(f"could not place {n_pins} pins on die {die}")
    return cells, pins


class _PlacementError(RuntimeError):
    pass


def _pop_nearest(pool: List[Pin], anchor: Tuple[int, int], k: int,
                 farthest: bool = False) -> List[Pin]:
    """Remove and return k pins from pool nearest (or farthest) to anchor XY."""
    if k <= 0:
        return []
    ax, ay = anchor
    pool.sort(key=lambda p: abs(p.x - ax) + abs(p.y - ay), reverse=farthest)
    chosen = pool[:k]
    del pool[:k]
    return chosen


def _assign_nets(plans: List[_NetPlan], bottom: List[Pin], top: List[Pin],
                 rng: random.Random) -> List[Net]:
    """Assign the placed pins to nets honoring locality. Consumes all pins."""
    bpool = list(bottom)
    tpool = list(top)
    rng.shuffle(bpool)
    rng.shuffle(tpool)
    nets: List[Net] = []
    # process larger / cross nets first so late small nets can mop up leftovers
    order = sorted(range(len(plans)), key=lambda i: (-plans[i].size, plans[i].cross))
    for nid_index, i in enumerate(order):
        plan = plans[i]
        chosen: List[Pin] = []
        if plan.cross:
            # anchor from whichever die the plan needs more of (or bottom)
            if plan.n_bottom >= plan.n_top and bpool:
                anchor_pin = bpool.pop(rng.randrange(len(bpool)))
            elif tpool:
                anchor_pin = tpool.pop(rng.randrange(len(tpool)))
            else:
                anchor_pin = bpool.pop(rng.randrange(len(bpool)))
            chosen.append(anchor_pin)
            anchor = (anchor_pin.x, anchor_pin.y)
            need_b = plan.n_bottom - (1 if anchor_pin.die == BOTTOM_DIE else 0)
            need_t = plan.n_top - (1 if anchor_pin.die == TOP_DIE else 0)
            chosen += _pop_nearest(bpool, anchor, need_b, farthest=not plan.local)
            chosen += _pop_nearest(tpool, anchor, need_t, farthest=not plan.local)
        else:
            pool = bpool if plan.die == BOTTOM_DIE else tpool
            anchor_pin = pool.pop(rng.randrange(len(pool)))
            chosen.append(anchor_pin)
            anchor = (anchor_pin.x, anchor_pin.y)
            chosen += _pop_nearest(pool, anchor, plan.size - 1, farthest=not plan.local)
        if len(chosen) < 2:
            raise _PlacementError("net assignment ran short of pins")
        driver = chosen[0]
        sinks = [p.id for p in chosen[1:]]
        nets.append(Net(id=0, driver=driver.id, sinks=sinks))  # id fixed below
    # renumber nets by a stable order (by driver id) for determinism
    nets.sort(key=lambda n: n.driver)
    for new_id, n in enumerate(nets):
        n.id = new_id
    return nets


def generate_candidate(cfg: GenConfig, seed: int) -> Instance:
    rng = random.Random(seed)
    plans = _plan_nets(cfg, rng)
    n_bottom = sum(p.n_bottom for p in plans)
    n_top = sum(p.n_top for p in plans)

    cells_b, pins_b = _place_pins(BOTTOM_DIE, n_bottom, cfg, rng,
                                  start_cell_id=0, start_pin_id=0, z=0)
    cells_t, pins_t = _place_pins(TOP_DIE, n_top, cfg, rng,
                                  start_cell_id=len(cells_b),
                                  start_pin_id=len(pins_b), z=cfg.layers - 1)

    nets = _assign_nets(plans, pins_b, pins_t, rng)

    inst = Instance(
        name=cfg.name,
        width=cfg.width,
        height=cfg.height,
        layers=cfg.layers,
        layer_delay=layer_delay_profile(cfg.layers, cfg.center_delay, cfg.layer_slope),
        via_delay=cfg.via_delay,
        cells=cells_b + cells_t,
        pins=pins_b + pins_t,
        nets=nets,
        params=cfg.to_params(),
        seed=seed,
        master_seed=cfg.master_seed,
    )
    return inst


@dataclass
class GenResult:
    instance: Instance
    reference: Submission
    baseline_total: int
    attempts: int


def generate_feasible(cfg: GenConfig) -> GenResult:
    """Generate an instance with a verified legal reference solution."""
    grow = 0
    attempt = 0
    total_attempts = 0
    while True:
        seed = cfg.seed + attempt * 100003 + grow * 1_000_003
        c = GenConfig(**{**asdict(cfg),
                         "width": cfg.width + grow * 6,
                         "height": cfg.height + grow * 6})
        try:
            inst = generate_candidate(c, seed)
        except _PlacementError:
            attempt += 1
            total_attempts += 1
            if attempt >= cfg.max_attempts:
                attempt = 0
                grow += 1
            if grow > 6:
                raise RuntimeError(f"{cfg.name}: could not place pins after growth")
            continue
        sub, stats = _baseline.route(inst, order=cfg.baseline_order)
        total_attempts += 1
        if sub is not None:
            res = check(inst, sub)
            if res.legal and res.total_delay is not None:
                inst.seed = seed
                return GenResult(instance=inst, reference=sub,
                                 baseline_total=res.total_delay, attempts=total_attempts)
        attempt += 1
        if attempt >= cfg.max_attempts:
            attempt = 0
            grow += 1
        if grow > 6:
            raise RuntimeError(f"{cfg.name}: no feasible instance found after growth")
