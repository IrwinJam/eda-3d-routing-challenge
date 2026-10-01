# warm_lns_refinement

By [kesudh](https://github.com/kesudh).

All initial legal routes are from [jay-tau's coordinated_refinement, PR #5](https://github.com/partcleda/eda-3d-routing-challenge/pull/5),
which itself continues from [Taz33m's pathfinder_lns, PR #3](https://github.com/partcleda/eda-3d-routing-challenge/pull/3),
pinned to commit `a5ef5e2406682473b99c6496a87a6279b64db9ba`. This submission continues warm-start
optimisation from those public warm starts; the warm-start route geometry is
credited to jay-tau and Taz33m. Improvements below are incremental refinements.

| Tier | Legal | Previous aggregate | Aggregate | Previous delay → delay | Improved cases |
|---|---:|---:|---:|---:|---:|
| hard | 9/9 | 1.38576514 | 1.38576514 | 145,305 → 145,305 | 0/9 |

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
| hard | case_01 | 8,668 | 8,668 | retained warm-start route |
| hard | case_02 | 13,158 | 13,158 | retained warm-start route |
| hard | case_03 | 11,072 | 11,072 | retained warm-start route |
| hard | case_04 | 13,075 | 13,075 | retained warm-start route |
| hard | case_05 | 15,211 | 15,211 | retained warm-start route |
| hard | case_06 | 19,810 | 19,810 | retained warm-start route |
| hard | case_07 | 21,361 | 21,361 | retained warm-start route |
| hard | case_08 | 21,508 | 21,508 | retained warm-start route |
| hard | case_09 | 21,442 | 21,442 | retained warm-start route |
