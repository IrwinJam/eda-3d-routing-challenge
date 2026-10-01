# Root-aware routing portfolio

Complete hard-tier submission: **9/9 legal**, total delay **158455**, aggregate score **1.274474947945242**.

This offline portfolio keeps the lowest-delay verified complete solution for each released case across repeated searches. It combines root-distance-aware negotiated congestion, coordinated neighborhood repair, neural-assisted candidate-tree selection, and a joint-grid mixed-integer refinement. Public cases were used for search and selection; this score is not a held-out evaluation of a single learned solver. Runtime is omitted because producing the portfolio involved multiple runs and warm starts.

The underlying search starts from saved legal solutions. It selects groups of blocking or nearby nets, removes their routes, and jointly repairs the group while keeping all other routes fixed. Negotiated congestion penalizes contested resources; root-aware shortest-path searches account for driver-to-sink delay, including shared-trunk delay once for each downstream sink. Parallel repair workers explore route orders and neighborhoods, and legal improvements are retained.

Some selected outputs came from repairs that harvested candidate trees and used a neural candidate/resource message-passing model to guide compatible-tree selection. That model was trained on 72 separately generated layouts with layout-disjoint, configuration-stratified four-fold validation. Although some public cases contributed better saved outputs, the neural variant underperformed the heuristic on fresh layouts; this submission makes no claim that neural selection is generally better. Earlier search stages also explored GPU-trained XGBoost policies and beam-search variants.

Case 07 adds an eight-net heuristic repair saving 32 delay units. Case 08 adds a six-net joint-grid MILP repair saving 10 units. The MILP uses binary vertex ownership, continuous driver-to-sink aggregate flow, and exclusive vertex capacity. Its objective counts flow-weighted physical delay; the decoded trees are checked with the original checker. That solve fixes outside-group routes and restricts the selected nets to search corridors, so its optimum does not certify a globally optimal case solution.

The implementation derives from the repository's negotiated-congestion router by Partcl, Inc., under its MIT license. Earlier portfolio stages included the published reference routes credited to Anthropic (reference); the current case 02 is a subsequently optimized route, not an unchanged copy of the published `negotiated_x2` submission.

`provenance.json` records each final route's SHA-256, method, and local experiment artifact identifier. These identifiers describe the offline search archive; the experimental source code and training artifacts are not included in this route-only submission. All submitted routes can be independently checked and scored using the unchanged repository toolkit.

| Case | Total delay | Final source method |
|---|---:|---|
| case_01 | 9428 | Neural-assisted candidate-tree selection within neighborhood repair |
| case_02 | 14020 | Neural-assisted candidate-tree selection within neighborhood repair |
| case_03 | 11718 | Neural-assisted candidate-tree selection within neighborhood repair |
| case_04 | 14353 | Neural-assisted candidate-tree selection within neighborhood repair |
| case_05 | 16455 | Neural-assisted candidate-tree selection within neighborhood repair |
| case_06 | 21412 | Neural-assisted candidate-tree selection within neighborhood repair |
| case_07 | 23685 | Neural-assisted repair, then an eight-net negotiated-congestion repair |
| case_08 | 23982 | Heuristic repair, then a six-net joint-grid MILP solve |
| case_09 | 23402 | Neural-assisted candidate-tree selection within neighborhood repair |

Verify from the repository root:

```bash
python3 -m m3d.cli score-suite --suite benchmarks_hard --submission-dir submissions/hard/erikqu_root_aware_portfolio
python3 scripts/verify_submissions.py
python3 -m m3d.cli leaderboard-all --check
```
