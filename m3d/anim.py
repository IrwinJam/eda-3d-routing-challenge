"""Animated GIF renderers for instances + solutions (reproducible, part of the toolkit).

* ``layer_sweep_gif`` — sweep up and down the routing stack of one case, showing
  each layer's routes (colored by net), its vias, and the die cells/pins, with a
  faint "ghost" of the whole routing for context and a delay-profile strip. Shows
  the 3D nature of the problem.
* ``suite_sweep_gif`` — sweep across the suite (small to large), each case's full
  routed design flattened top-down with a stats caption. Shows the size ladder.

Drawing is batched (matplotlib ``LineCollection`` + grouped scatter) so rendering
is fast; frames are assembled into a GIF with Pillow. Playback speed is set by
per-frame duration, not by duplicating frames.
"""
from __future__ import annotations

import io
import json
import os
from typing import List, Optional

from .checker import check
from .model import Instance, Submission
from .viz import _net_color


def _fig_to_pil(fig, width_px: int):
    from PIL import Image
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=fig.get_dpi())
    buf.seek(0)
    im = Image.open(buf).convert("RGB")
    if im.width != width_px:
        h = round(im.height * width_px / im.width)
        im = im.resize((width_px, h), Image.LANCZOS)
    return im


def _save_gif(frames, durations_ms, out_path: str):
    from PIL import Image
    pal = [f.quantize(colors=255, method=Image.Quantize.MEDIANCUT,
                      dither=Image.Dither.NONE) for f in frames]
    pal[0].save(out_path, save_all=True, append_images=pal[1:],
                duration=durations_ms, loop=0, optimize=True, disposal=2)
    return out_path


def _draw_delay_strip(ax, inst: Instance, active_z: int):
    n = inst.layers
    dmax = max(inst.layer_delay)
    ax.bar(range(n), [inst.layer_delay[z] / dmax for z in range(n)], width=0.8,
           color=["#d62728" if z == active_z else "#9aa0b4" for z in range(n)],
           edgecolor="none")
    ax.set_xlim(-0.6, n - 0.4); ax.set_ylim(0, 1.15)
    ax.set_xticks(range(n)); ax.set_yticks([])
    ax.set_xlabel("layer z  (bar height = per-edge delay)", fontsize=8)
    ax.tick_params(labelsize=7)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)


def layer_sweep_gif(inst: Instance, sub: Submission, out_path: str,
                    width_px: int = 720, end_hold_ms: int = 900,
                    mid_ms: int = 650) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.patches import Rectangle

    res = check(inst, sub)
    layer_segs = {z: ([], []) for z in range(inst.layers)}   # z -> (segments, colors)
    vias = {z: ([], [], []) for z in range(inst.layers)}     # z -> (xs, ys, colors)
    ghost = []
    for r in sub.routes:
        col = _net_color(r.net)
        for (a, b) in r.edges:
            if a[2] == b[2]:
                seg = [(a[0], a[1]), (b[0], b[1])]
                layer_segs[a[2]][0].append(seg); layer_segs[a[2]][1].append(col)
                ghost.append(seg)
            else:
                for (vx, vy, z) in ((a[0], a[1], a[2]), (b[0], b[1], b[2])):
                    vias[z][0].append(vx); vias[z][1].append(vy); vias[z][2].append(col)

    bx = [p.x for p in inst.pins]; by = [p.y for p in inst.pins]
    bc = ["#3333aa" if p.die == 0 else "#aa3333" for p in inst.pins]
    pins_on = {z: ([p.x for p in inst.pins if p.z == z],
                   [p.y for p in inst.pins if p.z == z],
                   ["#3333aa" if p.die == 0 else "#aa3333" for p in inst.pins if p.z == z])
               for z in range(inst.layers)}
    bcells = [c for c in inst.cells if c.die == 0]
    tcells = [c for c in inst.cells if c.die == 1]
    bottom, top = 0, inst.layers - 1

    order = list(range(inst.layers)) + list(range(inst.layers - 2, 0, -1))
    frames, durations = [], []
    for z in order:
        fig = plt.figure(figsize=(6.0, 6.6), dpi=112)
        ax = fig.add_axes([0.06, 0.20, 0.9, 0.72])
        strip = fig.add_axes([0.12, 0.105, 0.76, 0.055])
        ax.set_xlim(-1, inst.width); ax.set_ylim(-1, inst.height)
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
        ax.add_patch(Rectangle((-0.5, -0.5), inst.width, inst.height, fill=False,
                               edgecolor="#cccccc", lw=1.0))
        for c in bcells:
            ax.add_patch(Rectangle((c.x - 0.5, c.y - 0.5), c.w, c.h, facecolor="#eef0f8",
                                   edgecolor="none", zorder=0))
        for c in tcells:
            ax.add_patch(Rectangle((c.x - 0.5, c.y - 0.5), c.w, c.h, facecolor="#f8eeee",
                                   edgecolor="none", zorder=0))
        ax.add_collection(LineCollection(ghost, colors="#e6e6ee", linewidths=1.0, zorder=1))
        ax.scatter(bx, by, s=9, c=bc, alpha=0.22, zorder=2, linewidths=0)
        ax.add_collection(LineCollection(layer_segs[z][0], colors=layer_segs[z][1],
                                         linewidths=2.1, zorder=3, capstyle="round"))
        vx, vy, vcol = vias[z]
        if vx:
            ax.scatter(vx, vy, s=44, marker="s", facecolors="none",
                       edgecolors=vcol, linewidths=1.6, zorder=4)
        ox, oy, ocol = pins_on[z]
        if ox:
            ax.scatter(ox, oy, s=28, c=ocol, edgecolors="white", linewidths=0.5, zorder=5)

        where = "bottom die" if z == bottom else ("top die" if z == top else "mid-stack")
        ax.set_title(f"{inst.name}   layer z={z}/{inst.layers-1}   "
                     f"({where}, edge delay {inst.layer_delay[z]})", fontsize=11)
        fig.text(0.5, 0.965, f"{inst.width}x{inst.height}x{inst.layers} grid   "
                 f"{len(inst.nets)} nets   {len(inst.pins)} pins   "
                 f"total delay {res.total_delay}", ha="center", fontsize=9, color="#444")
        _draw_delay_strip(strip, inst, z)
        frames.append(_fig_to_pil(fig, width_px))
        durations.append(end_hold_ms if z in (bottom, top) else mid_ms)
        plt.close(fig)
    return _save_gif(frames, durations, out_path)


def suite_sweep_gif(suite_dir: str, out_path: str, width_px: int = 720,
                    ms_per_case: int = 1100, max_cases: Optional[int] = None) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.patches import Rectangle

    man = json.load(open(os.path.join(suite_dir, "suite.json")))
    cases = man["cases"][:max_cases] if max_cases else man["cases"]
    frames, durations = [], []
    for c in cases:
        inst = Instance.load(os.path.join(suite_dir, c["instance_file"]))
        sub = Submission.load(os.path.join(suite_dir, c["reference_file"]))
        segs, cols, vx, vy, vc = [], [], [], [], []
        for r in sub.routes:
            col = _net_color(r.net)
            for (a, b) in r.edges:
                if a[2] == b[2]:
                    segs.append([(a[0], a[1]), (b[0], b[1])]); cols.append(col)
                else:
                    vx.append(a[0]); vy.append(a[1]); vc.append(col)
        fig = plt.figure(figsize=(6.2, 6.6), dpi=110)
        ax = fig.add_axes([0.05, 0.05, 0.9, 0.85])
        ax.set_xlim(-1, inst.width); ax.set_ylim(-1, inst.height)
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
        ax.add_patch(Rectangle((-0.5, -0.5), inst.width, inst.height, fill=False,
                               edgecolor="#cccccc", lw=1.0))
        ax.add_collection(LineCollection(segs, colors=cols, linewidths=1.2,
                                         alpha=0.9, zorder=2, capstyle="round"))
        if vx:
            ax.scatter(vx, vy, s=7, c=vc, alpha=0.7, zorder=3, linewidths=0)
        ax.scatter([p.x for p in inst.pins], [p.y for p in inst.pins], s=6,
                   c=["#3333aa" if p.die == 0 else "#aa3333" for p in inst.pins],
                   alpha=0.55, zorder=1, linewidths=0)
        fig.text(0.5, 0.955, inst.name, ha="center", fontsize=13, weight="bold")
        fig.text(0.5, 0.915, f"{inst.width}x{inst.height}x{inst.layers} grid   "
                 f"{len(inst.nets)} nets   {len(inst.pins)} pins   "
                 f"baseline delay {c['baseline_total']}", ha="center", fontsize=9,
                 color="#444")
        frames.append(_fig_to_pil(fig, width_px))
        durations.append(ms_per_case)
        plt.close(fig)
    return _save_gif(frames, durations, out_path)
