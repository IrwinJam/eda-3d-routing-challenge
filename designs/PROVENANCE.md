# Vendored open-source designs

The `.blif` files in `blif/` are real gate-level netlists taken **verbatim** from
the **EPFL Combinational Benchmark Suite**, which is distributed under the MIT
license (see `EPFL_LICENSE.txt`).

* Upstream: https://github.com/lsils/benchmarks
* Reference: L. Amarú, P.-E. Gaillardon, G. De Micheli, "The EPFL Combinational
  Benchmark Suite," Proc. IWLS 2015.

Only the **connectivity** of each netlist is used to build a routing instance
(gates/inputs/outputs become cells, signals become nets); the logic itself (the
`.names` truth tables) is irrelevant to the routing challenge and is ignored.

| file | circuit | in released `designs` tier? | notes |
|---|---|---|---|
| `ctrl.blif`      | `ctrl`      | yes | control logic (small) |
| `int2float.blif` | `int2float` | yes | integer-to-float converter |
| `router.blif`    | `router`    | yes | network-on-chip router (low fanout) |
| `dec.blif`       | `dec`       | no (importable) | decoder; ~1.2k pins, so the reference router is slow here |
| `cavlc.blif`     | `cavlc`     | no (importable) | coding-audio-video logic; high fanout (max ~69) |

The released tier keeps the three circuits whose reference solution the
(pure-Python) negotiated router certifies in a few minutes. `dec` and `cavlc`
ship as well so you can turn them into instances yourself; they are just larger,
so certifying them takes longer.

To build a routing instance from any of these (or your own BLIF):

    python -m m3d.cli import-design --blif designs/blif/ctrl.blif --name ctrl \
        --out benchmarks_designs/ctrl.json --reference benchmarks_designs/reference/ctrl.sol.json

or rebuild the whole released `designs` tier with `python -m m3d.cli generate --tier designs`.
