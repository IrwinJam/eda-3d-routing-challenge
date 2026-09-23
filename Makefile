SUITE ?= benchmarks
CASE  ?= benchmarks/case_01.json
SUBS  ?= examples/submissions

.PHONY: generate baseline baseline-suite example score-example evaluate visualize test info

generate:
	python -m m3d.cli generate --out $(SUITE)

baseline:
	python -m m3d.cli baseline --case $(CASE) --out baseline.sol.json

baseline-suite:
	python -m m3d.cli baseline-suite --suite $(SUITE) --out-dir /tmp/m3d-baseline

example:
	python examples/example_submission.py --suite $(SUITE) --out-dir $(SUBS)

score-example:
	python -m m3d.cli score-suite --suite $(SUITE) --submission-dir $(SUBS)

evaluate:
	python -m m3d.cli evaluate --case $(CASE) --sol baseline.sol.json --suite $(SUITE)

visualize:
	python -m m3d.cli visualize --case $(CASE) --sol benchmarks/reference/case_01.sol.json --out case_01.png

info:
	python -m m3d.cli info --case $(CASE)

test:
	python -m unittest discover -s tests -t .
