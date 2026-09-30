# coordinated_refinement

By [jay-tau](https://github.com/jay-tau).

All 45 initial legal routes are from [Taz33m's pathfinder_lns submission, PR #3](https://github.com/partcleda/eda-3d-routing-challenge/pull/3), pinned to [commit a5ef5e2406682473b99c6496a87a6279b64db9ba](https://github.com/Taz33m/eda-3d-routing-challenge/commit/a5ef5e2406682473b99c6496a87a6279b64db9ba). This submission continues optimization from those public warm starts. The initial routing is credited to Taz33m.

The submitted snapshot strictly improves 36 cases and retains the original PR3 routes for 9 cases. All route files use compact JSON; retained routes preserve the original parsed geometry. Every case is legal under the repository checker, and each tier's aggregate exceeds the pinned PR3 result. Selection keeps the lowest independently checked delay per case; the original wins ties. These are heuristic refinements without a global optimality certificate.

| Tier | Legal | PR3 aggregate | Aggregate | PR3 delay → delay | Improved cases |
|---|---:|---:|---:|---:|---:|
| intro | 20/20 | 1.14860492 | 1.14951946 | 342,914 → 342,578 | 14/20 |
| hard | 9/9 | 1.38550181 | 1.38576514 | 145,333 → 145,305 | 6/9 |
| scale | 8/8 | 1.12347220 | 1.12483800 | 539,504 → 538,876 | 8/8 |
| stress | 1/1 | 1.09057379 | 1.09062989 | 1,049,818 → 1,049,764 | 1/1 |
| congested | 4/4 | 1.30365441 | 1.30421310 | 493,503 → 493,227 | 4/4 |
| designs | 3/3 | 1.42416814 | 1.42569639 | 210,847 → 210,639 | 3/3 |

## Method

The C++ refinement router uses exact root-distance-seeded A*: existing tree vertices enter the queue with their delay from the driver, preserving the scored sum of driver-to-sink delays while other nets are fixed. Equal-delay compact and random tie choices explore alternative trees. Small groups are rerouted with bounded conflict-based search or sequential repair. Bounded annealing variants also explore temporary delay increases while retaining the best legal state. Final selection keeps the best legal result across trials.

Warm negotiated-congestion trials produced the selected improvements for hard/case_03 (11,074 → 11,072), hard/case_04 (13,079 → 13,075), hard/case_08 (21,516 → 21,508). Their initial legal routing also comes from the same PR3 routes.

## Attribution and case provenance

The original route content retained from PR3 is intro: case_01, case_02, case_03, case_04, case_05, case_08; hard: case_01, case_05, case_07. Every other row below is a strict delay improvement over the same credited public start. Each tier's meta.json also records the pinned source, original and submitted delays, and hashes of the pinned public source file and compact submitted file.

| Tier | Case | PR3 delay | Submitted delay | Provenance |
|---|---|---:|---:|---|
| intro | case_01 | 206 | 206 | retained original route |
| intro | case_02 | 1,030 | 1,030 | retained original route |
| intro | case_03 | 1,611 | 1,611 | retained original route |
| intro | case_04 | 1,980 | 1,980 | retained original route |
| intro | case_05 | 3,691 | 3,691 | retained original route |
| intro | case_06 | 5,203 | 5,201 | exact and group refinement |
| intro | case_07 | 5,275 | 5,263 | exact and group refinement |
| intro | case_08 | 7,505 | 7,505 | retained original route |
| intro | case_09 | 8,164 | 8,156 | exact and group refinement |
| intro | case_10 | 10,567 | 10,561 | exact and group refinement |
| intro | case_11 | 12,232 | 12,198 | exact and group refinement |
| intro | case_12 | 16,127 | 16,109 | exact and group refinement |
| intro | case_13 | 19,633 | 19,621 | exact and group refinement |
| intro | case_14 | 21,257 | 21,235 | exact and group refinement |
| intro | case_15 | 24,014 | 23,978 | exact and group refinement |
| intro | case_16 | 32,960 | 32,906 | exact and group refinement |
| intro | case_17 | 41,828 | 41,810 | exact and group refinement |
| intro | case_18 | 44,771 | 44,683 | exact and group refinement |
| intro | case_19 | 40,076 | 40,060 | exact and group refinement |
| intro | case_20 | 44,784 | 44,774 | exact and group refinement |
| hard | case_01 | 8,668 | 8,668 | retained original route |
| hard | case_02 | 13,164 | 13,158 | exact and group refinement |
| hard | case_03 | 11,074 | 11,072 | warm negotiated refinement |
| hard | case_04 | 13,079 | 13,075 | warm negotiated refinement |
| hard | case_05 | 15,211 | 15,211 | retained original route |
| hard | case_06 | 19,816 | 19,810 | exact and group refinement |
| hard | case_07 | 21,361 | 21,361 | retained original route |
| hard | case_08 | 21,516 | 21,508 | warm negotiated refinement |
| hard | case_09 | 21,444 | 21,442 | exact and group refinement with bounded annealing |
| scale | case_01 | 39,430 | 39,398 | exact and group refinement |
| scale | case_02 | 45,588 | 45,508 | exact and group refinement |
| scale | case_03 | 56,634 | 56,530 | exact and group refinement |
| scale | case_04 | 57,256 | 57,190 | exact and group refinement |
| scale | case_05 | 66,439 | 66,361 | exact and group refinement |
| scale | case_06 | 78,455 | 78,349 | exact and group refinement |
| scale | case_07 | 86,673 | 86,611 | exact and group refinement |
| scale | case_08 | 109,029 | 108,929 | exact and group refinement |
| stress | case_01 | 1,049,818 | 1,049,764 | exact and group refinement |
| congested | case_01 | 54,193 | 54,191 | exact and group refinement |
| congested | case_02 | 95,910 | 95,892 | exact and group refinement |
| congested | case_03 | 165,309 | 165,191 | exact and group refinement with bounded annealing |
| congested | case_04 | 178,091 | 177,953 | exact and group refinement with bounded annealing |
| designs | ctrl | 50,340 | 50,256 | exact and group refinement |
| designs | int2float | 91,270 | 91,200 | exact and group refinement |
| designs | router | 69,237 | 69,183 | exact and group refinement |

## Runtime and verification

runtime.json is omitted for every tier. The measured runs cover incremental optimization of existing routes, excluding the work that produced the public warm starts. Those measurements are not an end-to-end route-generation runtime, so this entry makes no runtime or Pareto claim.

Comparisons use snapshot 2026-09-30T15:28:35.117491+00:00. Scores are recomputed from the route geometry against the released benchmark manifests. To reproduce the submission checks from the repository root:

```bash
python scripts/verify_submissions.py
python -m m3d.cli leaderboard-all --check
python -m unittest discover -s tests -q
```
