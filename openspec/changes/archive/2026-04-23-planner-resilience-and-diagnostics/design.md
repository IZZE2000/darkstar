## Context

Darkstar's planner is a MILP (Mixed Integer Linear Program) solved by PuLP with GLPK as the primary solver and CBC as fallback. It runs every ~60 seconds via `PlannerService.run_once()` and emits a `schedule_updated` WebSocket event on success or a `planner_error` event on failure. The frontend listens for `planner_error` in `QuickActions.tsx` and shows a 3-second grey toast with the literal string `"Planner failed"` — no reason, no hint, no retry visibility.

A reported production incident (log `ace75461_darkstar-dev_2026-04-22T13-53-37.260Z.log`, 2026-04-22) showed the planner silently re-failing every minute for hours with two distinct root causes:

1. **Kepler constraint asymmetry.** `planner/solver/kepler.py:219` sets `soc[0] == initial_soc` (a hard equality). `kepler.py:380` sets `soc[t] <= max_soc_kwh` (a hard upper bound). `kepler.py:218` clips `initial_soc` to `capacity_kwh` but *not* to `max_soc_kwh`. When `initial_soc > max_soc_kwh` (battery actually above its configured preference ceiling, as happens with `max_soc_percent=95` and a 98.9% reading), the LP is infeasible before any slot is scheduled. The corresponding lower bound is already soft via `soc_violation` slack — so the two sides of the constraint are handled inconsistently.
2. **EV charger registered with 0 kW.** `backend/loads/service.py:108` falls back silently to `nominal_power_kw = 0.0` when both `nominal_power_kw` and `max_power_kw` are missing from the `ev_chargers[]` entry. The `planner/solver/adapter.py:156` path has the same silent 0.0 fallback. The EV still appears in the UI as registered and plugged in, but `ev_energy[d][t] == ev_charge[d][t] * 0 * h == 0`, so the planner can never schedule charging.

Existing infrastructure we will reuse:

- `backend/health.py` defines `HealthIssue(category, severity, message, guidance, entity_id)` and `HealthStatus` with an aggregated critical/warning count. Already rendered by `SystemAlert.tsx` as a persistent top-of-app banner.
- `components/ui/Banner.tsx` and `components/ui/Toast.tsx` are the shared design primitives.
- `PlannerService` already has a lock to prevent concurrent runs, a `PlannerResult` dataclass, and progress phase tracking. It already calls `_notify_error()` on failure.

Stakeholders:
- End users: need to know why the planner isn't producing a plan and what to do about it.
- On-call / support: need structured diagnostics they can ask a user to copy-paste.
- Implementing agent: needs atomic tasks with clear acceptance criteria.

## Goals / Non-Goals

**Goals:**
- Eliminate infeasibility caused by `initial_soc > max_soc_kwh` — the user's reported failure must resolve.
- Every planner failure produces a typed error with code + human message + fix hint + structured details.
- Every planner failure is visible in the UI as a persistent banner, not a transient toast.
- Config-grade errors (missing EV power, stale SoC, etc.) are caught before the solver runs.
- Smart retry policy: suspend on user-actionable errors, backoff on transient errors, normal cadence on invariant violations.
- Reuse existing `SystemAlert` / `HealthIssue` / `Banner` infrastructure; extend minimally.
- Backwards-compatible API/WS changes (additive only).

**Non-Goals:**
- Fixing the inverter AC limit constraint that overcounts PV-to-battery (tracked in `docs/BACKLOG.md`).
- Validating Home Assistant sensor attributes at selection time (device_class / state_class / unit). Explicitly deferred — improved tooltips are the current mitigation.
- Changing the overall solver architecture (GLPK → alternative, model reformulation, etc.).
- Adding a migration for existing users' configs — soft max-SoC is transparently better; no config changes required.
- Restructuring `PlannerService` or changing its lock/lifecycle model.
- New settings surface — all new behavior is either derived from existing config or hardcoded with reasonable defaults.

## Decisions

### D1: Max-SoC becomes soft via slack + penalty (not by clipping initial_soc)

**Decision:** Introduce a `soc_overshoot[t]` slack variable analogous to the existing `soc_violation[t]`. Replace `prob += soc[t] <= max_soc_kwh` with `prob += soc[t] <= max_soc_kwh + soc_overshoot[t]`, and add `MAX_SOC_PENALTY * lpSum(soc_overshoot)` to the objective. Set `MAX_SOC_PENALTY = 1000.0` to mirror the existing `MIN_SOC_PENALTY`.

**Alternatives considered:**
- *Clip `initial_soc` to `max_soc_kwh`.* Rejected — loses real kWh that physically exist in the battery, leading to under-planned discharges and incorrect projected SoC values downstream.
- *Relax `soc[0]` equality into a range (`initial_soc − slack ≤ soc[0] ≤ initial_soc`).* Rejected as primary mechanism — more invasive and changes more code paths; the slack-on-ceiling approach is a minimal symmetric fix. A future refinement could combine both but is unnecessary for this incident.

**Rationale:** The existing min-SoC constraint is already soft, the asymmetry was a latent bug, and the tooltip already describes max-SoC as a "target ceiling". The fix aligns code with documented intent. The high penalty ensures the solver always prefers to discharge back within limits if physically possible, matching real-world behavior where batteries above their preferred ceiling simply discharge to settle back.

### D2: Pre-flight validator is deterministic and runs before Kepler

**Decision:** New module `planner/preflight.py` with a `run_preflight(input_data, config) -> None | raises PlannerPreflightError` function. Performs a fixed ordered sequence of checks (battery config → initial SoC → EV chargers → price data → forecast data → numeric sanity). Raises `PlannerPreflightError` carrying a `PlannerErrorCode`, human message, fix hint, and diagnostic payload on the first failure encountered.

**Alternatives considered:**
- *Fail-fast vs. collect-all.* Choosing fail-fast (first failure halts) for simplicity and to avoid cascading error spam. Collecting all errors is a nicer UX but more complex to implement and most root causes mask downstream checks anyway.
- *Put checks inside Kepler's `__post_init__` / `solve()`.* Rejected — mixes concerns. Pre-flight is about refusing to even attempt the solver with garbage input.

**Checks (final list, PV-peak check removed per user):**

| # | Check | Error code |
|---|---|---|
| 1 | Battery `min_soc_percent < max_soc_percent` | `CONFIG_INVALID` |
| 2 | Battery `capacity_kwh > 0` if battery enabled | `CONFIG_INVALID` |
| 3 | Battery `max_charge_power_kw > 0` AND `max_discharge_power_kw > 0` if battery enabled | `CONFIG_INVALID` |
| 4 | `initial_soc_kwh` within `[0, capacity_kwh]` (not `[min, max]` — soft now) | `INITIAL_SOC_OUT_OF_RANGE` |
| 5 | `initial_soc_kwh` timestamp within 30 min of now | `DATA_STALE` (warning, not blocking) |
| 6 | Every plugged-in EV charger has `max_power_kw > 0` | `EV_MISSING_POWER` |
| 7 | Every plugged-in EV charger has `battery_capacity_kwh > 0` | `EV_INVALID_CAPACITY` |
| 8 | Every EV with a `deadline` has `deadline > now` | `EV_DEADLINE_PAST` (warning — deadline will bind to 0 anyway) |
| 9 | Price data covers planning horizon (≥ 4h ahead) | `PRICES_UNAVAILABLE` |
| 10 | Forecast data non-empty and covers planning horizon | `FORECAST_UNAVAILABLE` |
| 11 | No NaN/Inf in prices or forecasts | `NUMERIC_INVALID` |

The 30-minute staleness threshold is hardcoded — no config surface.

### D3: Error codes are a typed enum with user messages attached

**Decision:** New module `planner/errors.py` defining `PlannerErrorCode` as a Python `StrEnum` (or `Enum` with string values for pre-3.11 safety) and a `PlannerError` exception class carrying `code: PlannerErrorCode`, `message: str`, `fix_hint: str`, `details: dict[str, Any]`.

```
PlannerErrorCode values (final list):
  CONFIG_INVALID
  INITIAL_SOC_OUT_OF_RANGE
  DATA_STALE
  EV_MISSING_POWER
  EV_INVALID_CAPACITY
  EV_DEADLINE_PAST
  PRICES_UNAVAILABLE
  FORECAST_UNAVAILABLE
  NUMERIC_INVALID
  SOLVER_INFEASIBLE
  SOLVER_TIMEOUT
  SOLVER_UNDEFINED
  INVALID_SCHEDULE  (post-solve safety guard)
  UNKNOWN           (catch-all for unexpected exceptions)
```

Each code has `user_message() -> str` (short, displayed in banner) and `fix_hints() -> list[str]` (actionable, displayed in details drawer).

**Alternatives considered:**
- *String error codes (no enum).* Rejected — loses type safety, makes refactoring risky.
- *Per-error subclasses.* Rejected — adds classes without adding value; all errors share the same shape.

### D4: EV with missing power is registered-as-disabled (Option B)

**Decision:** In `backend/loads/service.py`, when processing `ev_chargers[]`, if `nominal_power_kw ≤ 0` and the charger is `enabled`, register the `DeferrableLoad` with a new field `disabled_reason: str = "missing_power_kw"`. The load appears in the UI registry, but (a) the planner's adapter skips it when building `KeplerConfig.ev_chargers`, and (b) a HealthIssue with code `EV_MISSING_POWER` is emitted.

**Alternatives considered:**
- *Hard reject (Option A).* Rejected per user direction — EV disappearing from UI makes the problem harder to diagnose, not easier.
- *Default to 11 kW silently.* Rejected — hides the config bug and produces wrong plans.

**Rationale:** Visible-broken > invisible-broken. The UI can show the EV with a "Config incomplete" badge so the user sees the problem *and* knows which charger is affected.

### D5: HealthIssue gains code, details, retry_in_s — additive only

**Decision:** Extend the `HealthIssue` dataclass in `backend/health.py` with three new optional fields:

```python
@dataclass
class HealthIssue:
    category: str
    severity: str
    message: str
    guidance: str
    entity_id: str | None = None
    code: str | None = None        # NEW — machine-readable error code
    details: dict[str, Any] | None = None  # NEW — structured diagnostic data
    retry_in_s: int | None = None  # NEW — seconds until next planner retry
```

`to_dict()` includes the new fields when non-None, omits them otherwise. Frontend `HealthIssue` TypeScript interface mirrors this with `?:` optional fields. Fully backwards compatible.

**Alternatives considered:**
- *New subtype (`PlannerHealthIssue`).* Rejected — would require API versioning or a discriminated union in the frontend. Optional fields are simpler.
- *Embed structured data in the `message` or `guidance` string.* Rejected — loses machine readability; the "Copy diagnostic bundle" button needs structured JSON.

### D6: Planner retry policy is keyed on error code

**Decision:** `PlannerService` maintains retry state:

```python
_last_error_code: PlannerErrorCode | None
_last_error_at: datetime | None
_next_retry_at: datetime | None
_consecutive_failures: int
_retry_suspended: bool
```

Policy by code:

| Code category | Behavior | Example codes |
|---|---|---|
| **Config-blocking** | Suspend retries until config changes (listen to `settings_saved` event). On backend restart: one retry attempt, then suspend again if still broken. | `CONFIG_INVALID`, `EV_MISSING_POWER`, `EV_INVALID_CAPACITY`, `INITIAL_SOC_OUT_OF_RANGE` |
| **Transient** | Exponential backoff 60s → 120 → 240 → 300s cap. Reset on success. | `PRICES_UNAVAILABLE`, `FORECAST_UNAVAILABLE`, `SOLVER_TIMEOUT` |
| **Invariant/state** | Normal 60s cadence (state may change without config change). | `DATA_STALE`, `SOLVER_INFEASIBLE`, `SOLVER_UNDEFINED`, `NUMERIC_INVALID`, `INVALID_SCHEDULE`, `UNKNOWN` |
| **Warning only** | Do not block scheduling. | `EV_DEADLINE_PAST` (planner still runs; EV excluded from deadline constraints) |

`SchedulerService` (or wherever the retry loop lives) queries `planner_service.next_retry_at` and respects suspension. On `settings_saved` emit, `PlannerService.clear_retry_suspension()` is called to re-enable planning immediately.

**Alternatives considered:**
- *Uniform 60s retries regardless of code.* Rejected — spams logs and hides the real state.
- *Full circuit breaker (halt permanently after N failures).* Rejected — over-engineered for a home tool; user would need to figure out how to un-halt.

### D7: Persistent banner extends SystemAlert, not a new top-level component

**Decision:** `SystemAlert.tsx` gains the ability to render a "View details" button for any `HealthIssue` with a `details` payload. Clicking it opens `PlannerErrorDetails.tsx`, a right-side drawer (matching existing drawer patterns in the codebase) showing:

- Error code (monospace chip)
- Human message + fix hint
- Diagnostics table (initial_soc_kwh, max_soc_kwh, capacity_kwh, solver status, timestamp, …)
- Live retry countdown (ticks down from `retry_in_s`, auto-refreshes on new health snapshot)
- "Copy diagnostic bundle" button (copies JSON blob to clipboard for support)
- "Open Settings" link when error code is config-blocking

The banner itself cannot be hidden entirely. A small collapse toggle (chevron) shrinks the banner to a one-line summary bar, but a red indicator remains visible in the app header until the underlying failure clears.

**Alternatives considered:**
- *Modal dialog.* Rejected — interrupts the user; drawer is less intrusive.
- *Full dismissibility.* Rejected per user direction — planner failure is too important to hide.
- *New `PlannerBanner.tsx` component.* Rejected — duplicates `SystemAlert` for no structural benefit. The extension is small.

### D8: Toast on `planner_error` WebSocket event is removed

**Decision:** `QuickActions.tsx` no longer binds to `planner_error`. The event is still emitted by the backend (for logs/telemetry compatibility), but the frontend reads planner state exclusively from the health endpoint/stream.

**Rationale:** Two sources of truth (toast + banner) would be confusing. Health is the canonical source.

### D9: Tooltips updated in place; no runtime sensor validation

**Decision:** Rewrite tooltip strings in `frontend/src/config-help.json` for:
- `battery.max_soc_percent` — now explicitly "soft penalty ceiling; solver prefers to stay below but will tolerate overshoots"
- `system.battery.max_soc_percent` — same message
- EV `max_power_kw` (per-charger, in EntityArrayEditor) — "REQUIRED: your charger's maximum power in kW (e.g. 11, 22). If missing or zero, the charger will be registered as disabled."
- The six `input_sensors.total_*` keys — explicit about cumulative energy counters, monotonic, device_class=energy, units kWh/Wh/MWh, and explicit warning that power sensors are wrong.

No backend validation of sensor attributes. Deferred.

## Risks / Trade-offs

**[Soft max-SoC lets battery genuinely exceed user preference]** → Mitigation: penalty of 1000 SEK/kWh overshoot makes it prohibitively expensive; the solver will always prefer to discharge back under. In the pathological case where physical constraints prevent discharge (e.g., load too low, export disabled, PV still producing), the overshoot persists but the plan succeeds — which is strictly better than the current behavior of no plan at all.

**[Pre-flight adds latency]** → Mitigation: the checks are all in-memory and fast (<10ms combined). Measurable impact on total planner runtime is negligible compared to solver time (hundreds of ms to seconds).

**[Retry suspension could confuse users who expect continuous retries]** → Mitigation: banner clearly states "Waiting for you to fix the configuration" with a direct link to settings. A `Retry now` button in the details drawer allows manual override. On `settings_saved`, retry resumes automatically within the next scheduler tick.

**[Register-as-disabled EV still shows in UI]** → Mitigation: a "Config incomplete" badge makes the disabled state obvious. This is a feature, not a bug — users can see which charger is broken.

**[Additive HealthIssue fields require frontend/backend deployed together]** → Mitigation: all new fields are optional with sensible defaults (`None`/`undefined`). Old frontends ignore them; old backends don't emit them. No migration needed.

**[Diagnostic bundle could leak sensitive info]** → Mitigation: the bundle includes config snapshot with `secrets.yaml` style values redacted (`***`). Review in implementation to ensure no HA tokens, API keys, or location data leak.

**[Hardcoded 30-min SoC staleness threshold is wrong for some users]** → Acceptable — warning only, does not block. If someone reports a case where it's wrong, promote to config.

## Migration Plan

**Deploy order:** Single deployable unit. Backend and frontend must ship together because the new `details`/`code`/`retry_in_s` fields on `HealthIssue` have no frontend consumer before this change. No data migration, no config migration.

**Rollout:**
1. Merge change. CI runs unit + integration tests including the regression test for the reported incident.
2. Deploy to dev (ace75461 user). Observe that the persistent banner appears with the correct error for their current state; observe that fixing `max_soc_percent` (or waiting for battery to discharge) produces a successful plan.
3. Deploy to all users.

**Rollback:** Git revert. No data state mutated by this change. Old `HealthIssue` records will simply lose the new optional fields.

**Version bump:** Patch version (additive + bug fix; the "BREAKING" tag in the proposal refers to semantic behavior of the solver's max-SoC enforcement, which is intended-breaking and strictly better — no users would have been relying on the old infeasibility behavior).

## Open Questions

None. All seven open questions from the exploration phase were locked in:

1. Max-SoC overshoot penalty = 1000.0 (mirrors `MIN_SOC_PENALTY`) — confirmed.
2. EV with 0 kW → register-as-disabled (Option B) — confirmed.
3. Config-error retry behavior → try once on restart, then suspend — confirmed.
4. Banner dismissibility → collapse to small indicator, never fully hidden — confirmed.
5. Details drawer content → code + message + fix hint + diagnostics table + countdown + copy-bundle — confirmed.
6. SoC staleness threshold → hardcoded 30 min — confirmed.
7. Change name → `planner-resilience-and-diagnostics` — confirmed.
