# warm_lns_refinement

By [kesudh](https://github.com/kesudh).

All initial legal routes are from [jay-tau's coordinated_refinement, PR #5](https://github.com/partcleda/eda-3d-routing-challenge/pull/5),
which itself continues from [Taz33m's pathfinder_lns, PR #3](https://github.com/partcleda/eda-3d-routing-challenge/pull/3),
pinned to commit `a5ef5e2406682473b99c6496a87a6279b64db9ba`. This submission continues warm-start
optimisation from those public warm starts; the warm-start route geometry is
credited to jay-tau and Taz33m. Improvements below are incremental refinements.

| Tier | Legal | Previous aggregate | Aggregate | Previous delay → delay | Improved cases |
|---|---:|---:|---:|---:|---:|
| intro | 20/20 | 1.14951946 | 1.14953197 | 342,578 → 342,570 | 2/20 |

## Method

Rust warm-start large-neighborhood search over the credited warm starts:

- **Exact per-net reroute** — root-distance Dijkstra to a shortest-path tree,
  with random tie-breaking among equal-cost tight predecessors (random and
  compact equal-delay variants) so plateau structure is explored, not fixed.
- **Group rip-up rerouting** — region- and blocker-scoped groups of
  interacting nets are ripped and rerouted jointly (Gauss-Seidel passes), which
  no sequence of single-net reroutes can express.
- **Negotiated-congestion rounds inside group moves** — PathFinder-style present
  and history costs let group members transiently share resources, then an
  escalation to a strictly-legal exact reroute legalises the state; bounded
  threshold acceptance permits small temporary increases, best legal state kept.
- **Multi-worker portfolio** — independent workers with different seeds share a
  best-found state; every accepted state is re-verified before it can be
  selected.

Selection keeps the lowest independently checked delay per case; the warm-start
route is retained on ties. All submitted routes are legal under the repository
checker (each tier's aggregate exceeds the pinned PR#5 result).

## Attribution and case provenance

| Tier | Case | Previous delay | Submitted delay | Provenance |
|---|---|---:|---:|---|
| intro | case_01 | 206 | 206 | retained warm-start route |
| intro | case_02 | 1,030 | 1,030 | retained warm-start route |
| intro | case_03 | 1,611 | 1,611 | retained warm-start route |
| intro | case_04 | 1,980 | 1,980 | retained warm-start route |
| intro | case_05 | 3,691 | 3,691 | retained warm-start route |
| intro | case_06 | 5,201 | 5,201 | retained warm-start route |
| intro | case_07 | 5,263 | 5,263 | retained warm-start route |
| intro | case_08 | 7,505 | 7,505 | retained warm-start route |
| intro | case_09 | 8,156 | 8,156 | retained warm-start route |
| intro | case_10 | 10,561 | 10,561 | retained warm-start route |
| intro | case_11 | 12,198 | 12,198 | retained warm-start route |
| intro | case_12 | 16,109 | 16,109 | retained warm-start route |
| intro | case_13 | 19,621 | 19,621 | retained warm-start route |
| intro | case_14 | 21,235 | 21,235 | retained warm-start route |
| intro | case_15 | 23,978 | 23,976 | warm refinement |
| intro | case_16 | 32,906 | 32,906 | retained warm-start route |
| intro | case_17 | 41,810 | 41,810 | retained warm-start route |
| intro | case_18 | 44,683 | 44,677 | warm refinement |
| intro | case_19 | 40,060 | 40,060 | retained warm-start route |
| intro | case_20 | 44,774 | 44,774 | retained warm-start route |
