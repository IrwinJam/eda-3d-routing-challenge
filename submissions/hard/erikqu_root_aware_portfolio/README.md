# Root-aware routing portfolio

Complete hard-tier submission: 9/9 legal, total delay 191341, aggregate score 1.0563405766751923.

This offline portfolio keeps the minimum-delay legal saved route for each released case. The route pool contains root-distance-aware negotiated-congestion variants evaluated by XGBoost-guided and fixed candidate policies, plus the published reference variants. This score describes the saved portfolio; it is not a held-out score of a single learned selector.

The root-aware variants initialize each existing tree vertex in the multi-source shortest-path search with its actual driver-to-vertex delay. This makes sink attachment account for the complete driver path. Variants differ in net order and congestion pressure/history schedules. Every selected route is checked independently with the unchanged repository checker.

The learned selector was trained on separate generated layouts with layout-level stratified four-fold validation and GPU XGBoost. A later 12-feature tree-shape extension did not improve this portfolio. Candidate selection and minimum-delay retention on released cases constitute offline search. Runtime is omitted because the search used multiple runs.

Case 02 reuses the published `negotiated_x2` route, credited to Anthropic (reference) in this repository. The router is derived from the repository’s negotiated-congestion implementation by Partcl, Inc., under the repository MIT license. See `provenance.json` for per-case origins.

| Case | Candidate | Total delay |
|---|---|---:|
| case_01 | root_id | 11154 |
| case_02 | published negotiated_x2 | 18760 |
| case_03 | root_id | 14164 |
| case_04 | root_access | 16165 |
| case_05 | root_id | 19761 |
| case_06 | root_gentle | 26160 |
| case_07 | root_standard | 29021 |
| case_08 | root_low_present | 30000 |
| case_09 | root_access | 26156 |

Verify from the repository root:

```bash
python3 -m m3d.cli score-suite --suite benchmarks_hard --submission-dir submissions/hard/erikqu_root_aware_portfolio
python3 scripts/verify_submissions.py
python3 -m m3d.cli leaderboard-all --check
```
