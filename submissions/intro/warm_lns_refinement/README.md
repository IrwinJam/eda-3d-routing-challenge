# warm_lns_refinement — intro

By [kesudh](https://github.com/kesudh).

Warm starts are [Taz33m's pathfinder_lns, PR #3](https://github.com/partcleda/eda-3d-routing-challenge/pull/3)
pinned to commit `4e21227867ee1f8f72c9f4d9ad446e05c20fe452` — the version that led all six tier aggregates
before this refinement. Route geometry on retained cases is credited to Taz33m;
gains below are incremental refinements on top, produced by a Rust warm-start
large-neighborhood search and re-verified with `m3d/checker.py`.

| Tier | Legal | PR#3 aggregate | This aggregate | Delta | Refined | Verbatim PR#3 | Own tie |
|---|---:|---:|---:|---:|---:|---:|---:|
| intro | 20/20 | 1.15082522 | 1.15087837 | +0.0046% | 2/20 | 14 | 4 |

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
| case_01 | 206 | 206 | +0 | own earlier route (ties PR#3) |
| case_02 | 1,030 | 1,030 | +0 | own earlier route (ties PR#3) |
| case_03 | 1,611 | 1,611 | +0 | own earlier route (ties PR#3) |
| case_04 | 1,980 | 1,980 | +0 | own earlier route (ties PR#3) |
| case_05 | 3,687 | 3,687 | +0 | PR#3 route verbatim |
| case_06 | 5,189 | 5,189 | +0 | PR#3 route verbatim |
| case_07 | 5,267 | 5,263 | +4 | refined (rust LNS) |
| case_08 | 7,487 | 7,487 | +0 | PR#3 route verbatim |
| case_09 | 8,144 | 8,144 | +0 | PR#3 route verbatim |
| case_10 | 10,551 | 10,551 | +0 | PR#3 route verbatim |
| case_11 | 12,200 | 12,198 | +2 | refined (rust LNS) |
| case_12 | 16,093 | 16,093 | +0 | PR#3 route verbatim |
| case_13 | 19,593 | 19,593 | +0 | PR#3 route verbatim |
| case_14 | 21,197 | 21,197 | +0 | PR#3 route verbatim |
| case_15 | 23,938 | 23,938 | +0 | PR#3 route verbatim |
| case_16 | 32,866 | 32,866 | +0 | PR#3 route verbatim |
| case_17 | 41,622 | 41,622 | +0 | PR#3 route verbatim |
| case_18 | 44,601 | 44,601 | +0 | PR#3 route verbatim |
| case_19 | 40,024 | 40,024 | +0 | PR#3 route verbatim |
| case_20 | 44,726 | 44,726 | +0 | PR#3 route verbatim |
