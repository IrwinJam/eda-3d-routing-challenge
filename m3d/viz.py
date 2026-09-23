"""Visualization of instances and submissions (matplotlib).

Renders, per routing layer:

* cells and pins on both dies (pins colored by their die on the die layers);
* in-layer route segments colored by net;
* vias as markers (a route segment that changes layer is drawn as a via marker on
  both the layer it leaves and the layer it enters);
* routing conflicts (from a checker result) highlighted in red, for inspecting
  invalid submissions.

Matplotlib is only needed for visualization; the rest of the toolkit is pure
standard library.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from .checker import CheckResult, check
from .model import Instance, Submission, Vertex, canon_edge

_PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
    "#e377c2", "#7f7f7f", "#bcbd22", "#17becf", "#393b79", "#637939",
    "#8c6d31", "#843c39", "#7b4173", "#3182bd", "#31a354", "#756bb1",
]


def _net_color(net_id: int) -> str:
    return _PALETTE[net_id % len(_PALETTE)]


def visualize(inst: Instance, sub: Optional[Submission] = None,
              layer: Optional[int] = None, out_path: Optional[str] = None,
              show: bool = False, result: Optional[CheckResult] = None):
    """Draw the instance (and optional submission) and save/show it.

    If ``layer`` is given, draw only that routing layer; otherwise draw a grid of
    subplots, one per layer. If a submission is given and ``result`` is None, the
    checker is run so conflicts can be highlighted.
    """
    try:
        import matplotlib
        matplotlib.use("Agg") if not show else None
        import matplotlib.pyplot as plt
        from matplotlib.lines import Line2D
        from matplotlib.patches import Rectangle
    except Exception as exc:  # pragma: no cover - depends on environment
        raise RuntimeError("matplotlib is required for visualization "
                           "(pip install matplotlib)") from exc

    if sub is not None and result is None:
        result = check(inst, sub)

    conflict_v = set(tuple(v) for v in result.conflict_vertices) if result else set()
    conflict_e = set(canon_edge(tuple(a), tuple(b))
                     for (a, b) in result.conflict_edges) if result else set()

    # group submitted edges by layer and by kind (in-layer vs via)
    layer_segments: Dict[int, List[Tuple[Vertex, Vertex, int]]] = {}
    via_marks: Dict[int, List[Tuple[int, int, int]]] = {}  # z -> (x,y,net)
    if sub is not None:
        for r in sub.routes:
            for (a, b) in r.edges:
                (ax, ay, az), (bx, by, bz) = a, b
                if az == bz:
                    layer_segments.setdefault(az, []).append((a, b, r.net))
                else:
                    via_marks.setdefault(az, []).append((ax, ay, r.net))
                    via_marks.setdefault(bz, []).append((bx, by, r.net))

    pins_by_layer: Dict[int, List] = {}
    for p in inst.pins:
        pins_by_layer.setdefault(p.z, []).append(p)
    cells_by_die = {0: [c for c in inst.cells if c.die == 0],
                    1: [c for c in inst.cells if c.die == 1]}
    bottom_layer, top_layer = 0, inst.layers - 1

    layers = [layer] if layer is not None else list(range(inst.layers))
    n = len(layers)
    cols = min(3, n)
    rows = math.ceil(n / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(5.2 * cols, 5.0 * rows), squeeze=False)

    for idx, z in enumerate(layers):
        ax = axes[idx // cols][idx % cols]
        ax.set_title(f"layer z={z}  (edge delay {inst.layer_delay[z]})")
        ax.set_xlim(-1, inst.width)
        ax.set_ylim(-1, inst.height)
        ax.set_aspect("equal")
        ax.set_xlabel("x"); ax.set_ylabel("y")

        # cells that sit on this layer (bottom die at z=0, top die at z=L-1)
        if z == bottom_layer:
            for c in cells_by_die[0]:
                ax.add_patch(Rectangle((c.x - 0.5, c.y - 0.5), c.w, c.h,
                                       fill=True, facecolor="#eaeaf2",
                                       edgecolor="#9999bb", lw=0.8, zorder=1))
        if z == top_layer:
            for c in cells_by_die[1]:
                ax.add_patch(Rectangle((c.x - 0.5, c.y - 0.5), c.w, c.h,
                                       fill=True, facecolor="#f2eaea",
                                       edgecolor="#bb9999", lw=0.8, zorder=1))

        # route segments on this layer
        for (a, b, net) in layer_segments.get(z, []):
            e = canon_edge(a, b)
            color = "#d62728" if e in conflict_e else _net_color(net)
            lw = 2.6 if e in conflict_e else 1.6
            ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=lw,
                    solid_capstyle="round", zorder=3)

        # vias touching this layer
        for (vx, vy, net) in via_marks.get(z, []):
            ax.scatter([vx], [vy], s=42, marker="s", facecolors="none",
                       edgecolors=_net_color(net), linewidths=1.6, zorder=4)

        # pins on this layer
        for p in pins_by_layer.get(z, []):
            v = (p.x, p.y, p.z)
            if v in conflict_v:
                ax.scatter([p.x], [p.y], s=60, marker="X", color="#d62728", zorder=6)
            else:
                face = "#3333aa" if p.die == 0 else "#aa3333"
                ax.scatter([p.x], [p.y], s=26, marker="o", color=face,
                           edgecolors="white", linewidths=0.5, zorder=5)

        # conflict vertices that are not pins
        for v in conflict_v:
            if v[2] == z:
                ax.scatter([v[0]], [v[1]], s=70, marker="X", color="#d62728", zorder=6)

    # hide any unused subplots
    for j in range(n, rows * cols):
        axes[j // cols][j % cols].axis("off")

    legend = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#3333aa",
               markersize=7, label="bottom-die pin"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#aa3333",
               markersize=7, label="top-die pin"),
        Line2D([0], [0], marker="s", color="w", markeredgecolor="#333333",
               markerfacecolor="none", markersize=8, label="via"),
    ]
    if conflict_v or conflict_e:
        legend.append(Line2D([0], [0], marker="X", color="w",
                             markerfacecolor="#d62728", markersize=9, label="conflict"))
    title = inst.name
    if result is not None:
        title += "  —  " + ("LEGAL" if result.legal else "ILLEGAL")
        if result.total_delay is not None:
            title += f", total delay {result.total_delay}"
    fig.suptitle(title, fontsize=13)
    fig.legend(handles=legend, loc="lower center", ncol=len(legend), fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))

    if out_path:
        fig.savefig(out_path, dpi=130)
    if show:  # pragma: no cover
        plt.show()
    plt.close(fig)
    return out_path
