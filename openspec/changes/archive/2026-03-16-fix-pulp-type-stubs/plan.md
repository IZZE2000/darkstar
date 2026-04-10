# Fix: Expand PuLP Type Stubs

## Goal

Eliminate the 95 `# type: ignore` comments in `planner/solver/kepler.py` by expanding the
incomplete type stubs in `typings/pulp/__init__.pyi` (currently only 24 lines).

## What to do

### 1. Expand `typings/pulp/__init__.pyi`

The current stubs are missing:

- `LpVariable.dicts()` classmethod — this alone causes ~21 `reportUnknownMemberType` ignores
- `LpVariable.varValue` as a `@property float | None` (currently typed as a method)
- `LpVariable` arithmetic operators (`__add__`, `__mul__`, `__rmul__`, `__sub__`) so LP
  expressions typecheck without `[operator]` ignores
- `LpAffineExpression` type (return type of LP arithmetic)
- `LpProblem.__iadd__` accepting constraints (the `prob += ...` pattern)
- `LpProblem.__init__` kwargs: `name: str`, `sense: int`
- `LpVariable.__init__` kwargs: `name`, `lowBound`, `upBound`, `cat`
- `PULP_CBC_CMD` solver class with `msg` kwarg

Keep everything typed as concretely as possible; use `Any` only where PuLP genuinely
returns unknown types (e.g. solver internals).

### 2. Remove `# type: ignore` comments in `planner/solver/kepler.py`

After expanding the stubs, remove all `# type: ignore` comments that are now resolved.
Some may remain legitimate — keep only those where the ignore is still needed with a
brief inline comment explaining why.

**Do not change any logic in kepler.py** — only remove/trim the ignore comments.

### 3. Verify

```bash
uv run pyright planner/solver/kepler.py
python -m pytest tests/planner/ -q
```

Zero new pyright errors. All planner tests pass.

### 4. Commit

```
fix(types): expand PuLP type stubs, remove type:ignore noise in kepler.py
```

## What NOT to do

- Do not change any logic in `kepler.py`
- Do not touch any other files
- Do not create a full OpenSpec change — this is a single-file stub fix
