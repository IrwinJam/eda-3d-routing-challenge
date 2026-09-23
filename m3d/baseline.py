"""Baseline router: sequential shortest-path tree routing with rip-up-and-reroute.

This is a deliberately simple, deterministic reference router. It is *not* meant
to be state of the art; it exists to (a) certify that a generated instance is
routable and (b) provide the per-case normalization baseline for scoring.

Strategy
--------
* Route nets one at a time, in a deterministic order (largest bounding box
  first by default).
* Build each net as a tree with a Prim-like growth: start from the driver, then
  repeatedly attach the *closest* not-yet-connected sink to the current tree via
  a multi-source Dijkstra shortest path (minimizing routing delay). Attaching to
  the nearest existing tree vertex, and never routing *through* an existing tree
  vertex, keeps the result a connected acyclic tree.
* Hard capacity: a route never uses a vertex/edge owned by another net, and
  never passes through another net's pin.
* On failure, rip up the nets that block a capacity-ignoring path, put them back
  on the queue, and retry. Bounded by per-net rip counts and a global operation
  budget so it always terminates.

When it succeeds the output is conflict-free by construction and passes the
independent checker. When it cannot converge it reports failure (the generator
then discards that candidate instance).
"""
from __future__ import annotations

import heapq
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from .grid import Grid, edge_key
from .model import Instance, NetRoute, Submission, Vertex


@dataclass
class BaselineStats:
    routed_nets: int
    total_nets: int
    rip_ups: int
    ops: int
    success: bool


class Baseline:
    def __init__(self, inst: Instance, order: str = "bbox_desc",
                 rip_limit: int = 40, ops_factor: int = 200):
        self.inst = inst
        self.g = Grid(inst)
        self.pin_vid = {p.id: self.g.vid(p.vertex()) for p in inst.pins}
        self.net_pin_vids: Dict[int, List[int]] = {}
        for n in inst.nets:
            self.net_pin_vids[n.id] = [self.pin_vid[p] for p in n.pins()]
        # every pin vertex, mapped to its owning net
        self.pin_owner: Dict[int, int] = {}
        for n in inst.nets:
            for pid in n.pins():
                self.pin_owner[self.pin_vid[pid]] = n.id
        self.order = order
        self.rip_limit = rip_limit
        self.ops_max = ops_factor * max(1, len(inst.nets))

        # occupancy
        self.vertex_owner: Dict[int, int] = {}
        self.edge_owner: Dict[Tuple[int, int], int] = {}
        self.routed: Dict[int, Tuple[Set[int], Set[Tuple[int, int]]]] = {}

    # -- ordering ------------------------------------------------------------
    def _order_nets(self) -> List[int]:
        def bbox(nid: int) -> int:
            vids = self.net_pin_vids[nid]
            xs, ys, zs = [], [], []
            for vid in vids:
                x, y, z = self.g.coord(vid)
                xs.append(x); ys.append(y); zs.append(z)
            return (max(xs) - min(xs)) + (max(ys) - min(ys)) + (max(zs) - min(zs))
        nids = [n.id for n in self.inst.nets]
        if self.order == "bbox_desc":
            nids.sort(key=lambda i: (-bbox(i), i))
        elif self.order == "bbox_asc":
            nids.sort(key=lambda i: (bbox(i), i))
        else:  # "id"
            nids.sort()
        return nids

    # -- occupancy helpers ---------------------------------------------------
    def _commit(self, nid: int, tv: Set[int], te: Set[Tuple[int, int]]) -> None:
        for v in tv:
            self.vertex_owner[v] = nid
        for e in te:
            self.edge_owner[e] = nid
        self.routed[nid] = (tv, te)

    def _uncommit(self, nid: int) -> None:
        tv, te = self.routed.pop(nid)
        for v in tv:
            if self.vertex_owner.get(v) == nid:
                del self.vertex_owner[v]
        for e in te:
            if self.edge_owner.get(e) == nid:
                del self.edge_owner[e]

    # -- core tree build -----------------------------------------------------
    def _forbidden_pins(self, nid: int) -> Set[int]:
        own = set(self.net_pin_vids[nid])
        return {v for v in self.pin_owner if v not in own}

    def _build_tree(self, nid: int, hard: bool):
        """Return ``(tree_vertices, tree_edges, blockers)``.

        ``tree_*`` are ``None`` if the net cannot be connected at all (even
        ignoring other-net occupancy — i.e. blocked by pins/bounds). ``blockers``
        is the set of other nets whose resources were traversed when ``hard`` is
        False (used to decide what to rip up).
        """
        g = self.g
        pin_vids = self.net_pin_vids[nid]
        driver = pin_vids[0]
        remaining = set(pin_vids[1:])
        forbidden_pins = self._forbidden_pins(nid)

        tree_v: Set[int] = {driver}
        tree_e: Set[Tuple[int, int]] = set()
        blockers: Set[int] = set()

        if not remaining:
            return tree_v, tree_e, blockers

        while remaining:
            # multi-source Dijkstra from all current tree vertices to any remaining sink
            dist: Dict[int, int] = {}
            prev: Dict[int, int] = {}
            heap: List[Tuple[int, int]] = []
            for s in tree_v:
                dist[s] = 0
                heapq.heappush(heap, (0, s))
            found: Optional[int] = None
            while heap:
                d, u = heapq.heappop(heap)
                if d > dist.get(u, d):
                    continue
                if u in remaining:
                    found = u
                    break
                for v, w in g.neighbors(u):
                    # never route through another net's pin
                    if v in forbidden_pins:
                        continue
                    # never step onto our own existing tree vertex (would cycle),
                    # unless it is a source we started from (those seed the search).
                    if v in tree_v:
                        continue
                    ek = edge_key(u, v)
                    if hard:
                        if v in self.vertex_owner and self.vertex_owner[v] != nid:
                            continue
                        if ek in self.edge_owner and self.edge_owner[ek] != nid:
                            continue
                    else:
                        vo = self.vertex_owner.get(v)
                        if vo is not None and vo != nid:
                            blockers.add(vo)
                        eo = self.edge_owner.get(ek)
                        if eo is not None and eo != nid:
                            blockers.add(eo)
                    nd = d + w
                    if nd < dist.get(v, 1 << 62):
                        dist[v] = nd
                        prev[v] = u
                        heapq.heappush(heap, (nd, v))
            if found is None:
                return None, None, blockers
            # reconstruct path from `found` back to a source tree vertex
            path_v: List[int] = [found]
            cur = found
            while cur in prev:
                cur = prev[cur]
                path_v.append(cur)
            # cur is now a source (a tree vertex); add the whole path
            for i in range(len(path_v) - 1):
                a, b = path_v[i], path_v[i + 1]
                tree_v.add(a)
                tree_v.add(b)
                tree_e.add(edge_key(a, b))
            remaining.discard(found)
        return tree_v, tree_e, blockers

    # -- driver --------------------------------------------------------------
    def run(self) -> Tuple[Optional[Submission], BaselineStats]:
        queue = deque(self._order_nets())
        rip_counts: Dict[int, int] = defaultdict(int)
        ops = 0
        rip_ups = 0
        while queue and ops < self.ops_max:
            ops += 1
            nid = queue.popleft()
            if nid in self.routed:
                continue
            tv, te, _ = self._build_tree(nid, hard=True)
            if tv is not None:
                self._commit(nid, tv, te)
                continue
            # hard failed: find blockers on a capacity-ignoring route
            stv, ste, blockers = self._build_tree(nid, hard=False)
            if stv is None:
                # truly unroutable (pins/bounds) — cannot help by ripping up
                return None, BaselineStats(len(self.routed), len(self.inst.nets),
                                           rip_ups, ops, False)
            blockers.discard(nid)
            if not blockers or rip_counts[nid] >= self.rip_limit:
                return None, BaselineStats(len(self.routed), len(self.inst.nets),
                                           rip_ups, ops, False)
            for b in blockers:
                if b in self.routed:
                    self._uncommit(b)
                    queue.append(b)
                    rip_ups += 1
            rip_counts[nid] += 1
            queue.appendleft(nid)

        success = len(self.routed) == len(self.inst.nets)
        stats = BaselineStats(len(self.routed), len(self.inst.nets), rip_ups, ops, success)
        if not success:
            return None, stats
        routes = []
        for n in self.inst.nets:
            _tv, te = self.routed[n.id]
            edges = [(self.g.coord(a), self.g.coord(b)) for (a, b) in te]
            routes.append(NetRoute(net=n.id, edges=edges))
        return Submission(instance=self.inst.name, routes=routes), stats


def route(inst: Instance, order: str = "bbox_desc",
          rip_limit: int = 40, ops_factor: int = 200) -> Tuple[Optional[Submission], BaselineStats]:
    return Baseline(inst, order=order, rip_limit=rip_limit, ops_factor=ops_factor).run()
