# File formats

All files are JSON. Coordinates are integer triples `[x, y, z]` with
`0 <= x < width`, `0 <= y < height`, `0 <= z < layers`.

## Instance — `m3d-instance` (`benchmarks/case_NN.json`)

The participant-facing benchmark input.

```json
{
  "format": "m3d-instance",
  "version": 1,
  "name": "case_01",
  "grid": { "width": 16, "height": 16, "layers": 6 },
  "delay": { "layer_delay": [6, 4, 2, 2, 4, 6], "via_delay": 3 },
  "cells": [
    { "id": 0, "die": 0, "x": 0, "y": 12, "w": 2, "h": 3 }
  ],
  "pins": [
    { "id": 0, "cell": 0, "die": 0, "x": 1, "y": 12, "z": 0 }
  ],
  "nets": [
    { "id": 0, "driver": 0, "sinks": [1, 2] }
  ],
  "params": { "...": "generation parameters" },
  "seed": 123456,
  "master_seed": 20260923
}
```

* `grid.layers` is the number of routing layers; bottom-die pins have `z = 0`,
  top-die pins have `z = layers - 1`.
* `delay.layer_delay[z]` is the per-edge delay of an in-layer step on layer `z`.
  `delay.via_delay` is the delay of a via between adjacent layers. All are
  positive integers and are the authoritative delays used for scoring.
* `cells[i]` occupies vertices `x .. x+w-1` by `y .. y+h-1` on its die.
  `die` is `0` (bottom) or `1` (top).
* `pins[i]` sits at `(x, y, z)`; `cell` is its owning cell id; `die` matches the
  cell's die; `z` is `0` (bottom) or `layers-1` (top).
* `nets[i]` has exactly one `driver` (a pin id) and one or more `sinks` (pin
  ids). Every pin id appears in exactly one net.
* `params` and `seed` record how the instance was generated (for reproduction).

## Submission — `m3d-submission`

What a participant produces, one file per case (suggested name
`case_NN.sol.json`).

```json
{
  "format": "m3d-submission",
  "version": 1,
  "instance": "case_01",
  "routes": [
    {
      "net": 0,
      "edges": [
        [[1, 12, 0], [1, 12, 1]],
        [[1, 12, 1], [2, 12, 1]]
      ]
    }
  ]
}
```

* Exactly one `routes` entry per net in the instance.
* `edges` is the net's routing tree as an unordered list of edges; each edge is a
  pair of adjacent vertices. Vertices are implied by the edges. The tree must
  connect the net's driver to all its sinks (a connected, acyclic tree spanning
  all the net's pins).
* Both an in-layer edge (`z` equal, `x` or `y` differing by 1) and a via edge
  (`x`,`y` equal, `z` differing by 1) are legal; nothing else is.

## Result — `m3d-result`

What the checker/evaluator emits for one case.

```json
{
  "format": "m3d-result",
  "version": 1,
  "instance": "case_01",
  "legal": true,
  "total_delay": 240,
  "nets": [ { "net": 0, "legal": true, "delay": 60, "reasons": [] } ],
  "reasons": [],
  "conflict_vertices": [],
  "conflict_edges": []
}
```

* `legal` is true only if every net is individually legal and there is no global
  conflict. `total_delay` is `null` for an illegal submission.
* `nets[i].delay` is the sum of that net's driver→sink path delays.
* `reasons` lists global problems (missing net, short, etc.); each net's
  `reasons` lists its own problems.
* `conflict_vertices` / `conflict_edges` mark 3D resources shared by more than
  one net, for visualization of invalid submissions.

## Suite manifest — `m3d-suite` (`benchmarks/suite.json`)

Records the master seed, per-case seeds, sizes, and the **baseline total** used
as the scoring normalization for each case, plus generation bookkeeping.

## Leaderboard — `m3d-leaderboard`

Emitted by `score-suite`: `complete`, `aggregate_score`, per-case
`{legal, total_delay, baseline_delay, ratio, runtime_s}`, and the scoring
`formula` string.
