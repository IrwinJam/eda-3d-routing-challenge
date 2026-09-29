# Submissions

Each entry here is a routing result that appears on the [leaderboard](../LEADERBOARD.md).
Scores are recomputed from your **route files** by the independent checker
(`m3d/checker.py`), so the leaderboard cannot be gamed — you can only place higher
by submitting better *legal* routes.

## Layout

```
submissions/<tier>/<your-name>/
    <case>.sol.json      one per case in the tier (e.g. case_01.sol.json, ctrl.sol.json)
    runtime.json         optional: {"<case>": seconds, ...} — used for the runtime axis
    meta.json            author, method, url, date  (see _template/meta.json)
```

`<tier>` is one of: `intro`, `hard`, `scale`, `stress`, `congested`, `designs`.
`<case>` matches the instance `name` (the checker looks for `<name>.sol.json`).

A submission is **complete** (and ranked) only if it has a legal solution for
**every** case in the tier; otherwise it is listed as incomplete.

See [../CONTRIBUTING.md](../CONTRIBUTING.md) for the full step-by-step.
