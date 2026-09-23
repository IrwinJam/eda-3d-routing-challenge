"""Independent legality checker and delay recomputation.

The checker never trusts anything a participant reports. It reconstructs each
net's routing tree from the submitted edges, validates it against every rule in
the challenge, and recomputes the delay from the instance's stored delay values.

Legality rules (identical to the ones the generator, baseline and docs use):

1. Every net in the instance appears exactly once in the submission.
2. Each edge is a legal move (one grid step in x or y on a layer, or a via to an
   adjacent layer), with both endpoints inside the grid/layer bounds. No
   duplicate edges, no self loops.
3. Each net's edges form a single connected, acyclic tree whose vertex set
   contains all of that net's pins (driver + sinks).
4. Capacity: every 3D vertex and every 3D edge belongs to at most one net.
   Branches of the *same* net may share vertices/edges (a tree already does).
5. A net's route may not pass through a pin that belongs to a different net.

A submission is legal only if all nets are individually legal and no global
conflict exists. Anything else (missing nets, disconnected pins, cycles, shorts,
resource conflicts, invalid coordinates, illegal transitions) is rejected, and a
partial routing is reported as illegal so it cannot earn a competitive score.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .model import Instance, Submission, Vertex, Edge, canon_edge


@dataclass
class NetResult:
    net: int
    legal: bool
    delay: Optional[int]
    reasons: List[str] = field(default_factory=list)


@dataclass
class CheckResult:
    instance: str
    legal: bool
    total_delay: Optional[int]
    nets: List[NetResult]
    reasons: List[str] = field(default_factory=list)          # global reasons
    conflict_vertices: List[Vertex] = field(default_factory=list)
    conflict_edges: List[Edge] = field(default_factory=list)

    def to_dict(self) -> Dict:
        from .model import RESULT_FORMAT, FORMAT_VERSION
        return {
            "format": RESULT_FORMAT,
            "version": FORMAT_VERSION,
            "instance": self.instance,
            "legal": self.legal,
            "total_delay": self.total_delay,
            "nets": [
                {"net": n.net, "legal": n.legal, "delay": n.delay, "reasons": n.reasons}
                for n in self.nets
            ],
            "reasons": self.reasons,
            "conflict_vertices": [list(v) for v in self.conflict_vertices],
            "conflict_edges": [[list(a), list(b)] for (a, b) in self.conflict_edges],
        }


def _tree_delays(driver: Vertex, adj: Dict[Vertex, List[Tuple[Vertex, int]]],
                 sinks: List[Vertex]) -> Dict[Vertex, int]:
    """BFS from driver over the (already validated) tree; return delay to each vertex."""
    dist: Dict[Vertex, int] = {driver: 0}
    q = deque([driver])
    while q:
        u = q.popleft()
        for v, w in adj[u]:
            if v not in dist:
                dist[v] = dist[u] + w
                q.append(v)
    return dist


def check(inst: Instance, sub: Submission) -> CheckResult:
    pin_vertex = inst.pin_vertex()
    vertex_to_pin = inst.vertex_to_pin()
    pin_to_net = inst.pin_to_net()
    nets_by_id = {n.id: n for n in inst.nets}

    net_results: List[NetResult] = []
    global_reasons: List[str] = []

    # Global resource ownership, filled only from *individually legal* nets so a
    # broken net does not mask a genuine short between two good nets.
    vertex_owner: Dict[Vertex, int] = {}
    edge_owner: Dict[Edge, int] = {}
    conflict_vertices: Set[Vertex] = set()
    conflict_edges: Set[Edge] = set()

    # 1. net presence
    submitted = {}
    dup = set()
    for r in sub.routes:
        if r.net in submitted:
            dup.add(r.net)
        submitted[r.net] = r
    for nid in dup:
        global_reasons.append(f"net {nid} submitted more than once")
    for nid in nets_by_id:
        if nid not in submitted:
            global_reasons.append(f"missing net {nid}")
    for nid in submitted:
        if nid not in nets_by_id:
            global_reasons.append(f"unknown net {nid} in submission")

    # per-net validation
    net_vertices: Dict[int, Set[Vertex]] = {}
    net_edges: Dict[int, Set[Edge]] = {}

    for net in inst.nets:
        reasons: List[str] = []
        route = submitted.get(net.id)
        if route is None:
            net_results.append(NetResult(net.id, False, None, ["missing"]))
            continue

        edges: Set[Edge] = set()
        vertices: Set[Vertex] = set()
        edge_ok = True
        for (u, v) in route.edges:
            if u == v:
                reasons.append(f"self-loop at {u}")
                edge_ok = False
                continue
            if not inst.in_bounds(u) or not inst.in_bounds(v):
                reasons.append(f"edge out of bounds {u}-{v}")
                edge_ok = False
                continue
            try:
                inst.edge_delay(u, v)
            except ValueError:
                reasons.append(f"illegal move {u}-{v}")
                edge_ok = False
                continue
            e = canon_edge(u, v)
            if e in edges:
                reasons.append(f"duplicate edge {u}-{v}")
                edge_ok = False
                continue
            edges.add(e)
            vertices.add(u)
            vertices.add(v)

        # required pins present as vertices
        pin_ids = net.pins()
        pin_verts = [pin_vertex[p] for p in pin_ids]
        for p, pv in zip(pin_ids, pin_verts):
            vertices.add(pv)  # a pin must be in the tree; add so isolation shows as disconnection

        # tree structure: connected from driver, acyclic, spans all pins
        driver_v = pin_vertex[net.driver]
        adj: Dict[Vertex, List[Tuple[Vertex, int]]] = {v: [] for v in vertices}
        for (a, b) in edges:
            w = inst.edge_delay(a, b)
            adj[a].append((b, w))
            adj[b].append((a, w))

        # connectivity
        seen: Set[Vertex] = set()
        q = deque([driver_v])
        seen.add(driver_v)
        while q:
            u = q.popleft()
            for (v, _w) in adj[u]:
                if v not in seen:
                    seen.add(v)
                    q.append(v)
        connected = len(seen) == len(vertices)
        if not connected:
            missing_pins = [p for p, pv in zip(pin_ids, pin_verts) if pv not in seen]
            if missing_pins:
                reasons.append(f"pins not connected to driver: {missing_pins}")
            else:
                reasons.append("route has vertices disconnected from the driver")

        # acyclic: a connected graph with V vertices is a tree iff it has V-1 edges
        if connected and len(edges) != len(vertices) - 1:
            reasons.append(
                f"not a tree: {len(vertices)} vertices but {len(edges)} edges "
                f"(a tree needs exactly {len(vertices) - 1})"
            )

        # route may not pass through another net's pin
        for v in vertices:
            other_pin = vertex_to_pin.get(v)
            if other_pin is not None and pin_to_net[other_pin] != net.id:
                reasons.append(
                    f"passes through pin {other_pin} of net {pin_to_net[other_pin]} at {v}"
                )

        legal = edge_ok and connected and (len(edges) == len(vertices) - 1) and not reasons
        delay: Optional[int] = None
        if legal:
            dist = _tree_delays(driver_v, adj, pin_verts)
            delay = sum(dist[pin_vertex[s]] for s in net.sinks)
            net_vertices[net.id] = vertices
            net_edges[net.id] = edges

        net_results.append(NetResult(net.id, legal, delay, reasons))

    # 4/5. global capacity across individually-legal nets
    for nid in sorted(net_vertices):
        for v in net_vertices[nid]:
            if v in vertex_owner and vertex_owner[v] != nid:
                conflict_vertices.add(v)
                global_reasons.append(
                    f"vertex {v} shared by nets {vertex_owner[v]} and {nid} (short)"
                )
            else:
                vertex_owner[v] = nid
        for e in net_edges[nid]:
            if e in edge_owner and edge_owner[e] != nid:
                conflict_edges.add(e)
                global_reasons.append(
                    f"edge {e[0]}-{e[1]} shared by nets {edge_owner[e]} and {nid} (short)"
                )
            else:
                edge_owner[e] = nid

    all_nets_legal = all(n.legal for n in net_results)
    legal = all_nets_legal and not global_reasons
    total = sum(n.delay for n in net_results if n.delay is not None) if legal else None

    # de-duplicate global reasons while preserving order
    seen_r: Set[str] = set()
    dedup_reasons = [r for r in global_reasons if not (r in seen_r or seen_r.add(r))]

    return CheckResult(
        instance=inst.name,
        legal=legal,
        total_delay=total,
        nets=net_results,
        reasons=dedup_reasons,
        conflict_vertices=sorted(conflict_vertices),
        conflict_edges=sorted(conflict_edges),
    )
