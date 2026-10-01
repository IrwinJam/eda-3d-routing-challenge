# warm_lns_refinement — congested

By [kesudh](https://github.com/kesudh).

Warm starts are [Taz33m's pathfinder_lns, PR #3](https://github.com/partcleda/eda-3d-routing-challenge/pull/3)
pinned to commit `4e21227867ee1f8f72c9f4d9ad446e05c20fe452` — the version that led all six tier aggregates
before this refinement. Route geometry on retained cases is credited to Taz33m;
gains below are incremental refinements on top, produced by a Rust warm-start
large-neighborhood search and re-verified with `m3d/checker.py`.

| Tier | Legal | PR#3 aggregate | This aggregate | Delta | Refined | Verbatim PR#3 | Own tie |
|---|---:|---:|---:|---:|---:|---:|---:|
| congested | 4/4 | 1.30832897 | 1.30847510 | +0.0112% | 4/4 | 0 | 0 |

## Method

- **Exact per-net reroute** — root-distance Dijkstra to a shortest-path tree,
  with random tie-breaking among equal-cost tight predecessors so plateau
  structure is explored rather than fixed.
- **Group rip-up rerouting** — region- and blocker-scoped groups of interacting
  nets are ripped and rerouted jointly (Gauss-Seidel passes), which no sequence
  of single-net reroutes can express.
- **Negotiated-congestion rounds inside group moves** — PathFinder-style present
  and history costs let group members transiently share resources, then an
  escalation to a strictly-legal exact reroute legalises the state; bounded
  threshold acceptance permits small temporary increases, best legal state kept.
- **Multi-worker portfolio** — independent workers with different seeds share a
  best-found state; every accepted state is re-verified before selection.

Selection keeps the lowest independently checked delay per case. A case is
labelled **verbatim** only when the submitted file is byte-identical (same
sha256) to the credited warm start; **own tie** means the route is an earlier
`warm_lns_refinement` route that matches PR#3's delay without being a copy of it.

## Case provenance

| Case | PR#3 delay | Submitted | Delta | Provenance |
|---|---:|---:|---:|---|
| case_01 | 54,077 | 54,073 | +4 | refined (rust LNS) |
| case_02 | 95,660 | 95,650 | +10 | refined (rust LNS) |
| case_03 | 164,165 | 164,145 | +20 | refined (rust LNS) |
| case_04 | 177,625 | 177,599 | +26 | refined (rust LNS) |
