# warm_lns_refinement

By [kesudh](https://github.com/kesudh).

All initial legal routes are from [jay-tau's coordinated_refinement, PR #5](https://github.com/partcleda/eda-3d-routing-challenge/pull/5),
which itself continues from [Taz33m's pathfinder_lns, PR #3](https://github.com/partcleda/eda-3d-routing-challenge/pull/3),
pinned to commit `a5ef5e2406682473b99c6496a87a6279b64db9ba`. This submission continues warm-start
optimisation from those public warm starts; the warm-start route geometry is
credited to jay-tau and Taz33m. Improvements below are incremental refinements.

| Tier | Legal | Previous aggregate | Aggregate | Previous delay → delay | Improved cases |
|---|---:|---:|---:|---:|---:|
| scale | 8/8 | 1.12483800 | 1.12484647 | 538,876 → 538,872 | 1/8 |

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
| scale | case_01 | 39,398 | 39,398 | retained warm-start route |
| scale | case_02 | 45,508 | 45,508 | retained warm-start route |
| scale | case_03 | 56,530 | 56,530 | retained warm-start route |
| scale | case_04 | 57,190 | 57,190 | retained warm-start route |
| scale | case_05 | 66,361 | 66,357 | warm refinement |
| scale | case_06 | 78,349 | 78,349 | retained warm-start route |
| scale | case_07 | 86,611 | 86,611 | retained warm-start route |
| scale | case_08 | 108,929 | 108,929 | retained warm-start route |
