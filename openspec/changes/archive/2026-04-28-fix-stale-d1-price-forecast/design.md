## Context

The planner assembles price data by combining real Nordpool slots (today) with a D+1 ML forecast fallback (when tomorrow's auction prices aren't yet published). The fallback is keyed by `days_ahead=1` in the DB — a relative label meaning "one day after the forecast was generated". Once midnight passes, yesterday's `days_ahead=1` slots are for *today*, not tomorrow. The fallback function has no awareness of this calendar shift.

The result is that `all_entries` in `get_nordpool_data` ends up with two entries for almost every 15-minute slot of today: one real Nordpool price, one stale ML forecast. These duplicates propagate through the pipeline and crash the solver when it tries to write results back to a DataFrame with duplicate index labels.

## Goals / Non-Goals

**Goals:**
- D+1 fallback never contributes slots for today or the past
- Assembled `price_data` is always free of duplicate `start_time` values, regardless of source
- Real Nordpool prices always win if they and the fallback somehow agree on a slot

**Non-Goals:**
- Changing how forecasts are stored or labelled in the DB
- Fixing anything beyond the two-function scope identified

## Decisions

**Decision 1: Filter stale slots in `get_d1_price_forecast_fallback`, not the caller**

The fallback function is the natural owner of "only return future slots". Filtering in `get_nordpool_data` would work too, but it would be a workaround at the wrong level — the fallback function should not be able to return past slots to any caller, not just this one.

Alternative considered: filter in `get_nordpool_data` when appending fallback entries. Rejected because it distances the guard from the data source.

**Decision 2: Deduplicate by `start_time` in `_process_nordpool_data`, keeping first occurrence**

`all_entries` is assembled as `today_values + tomorrow_values + fallback`. Real Nordpool data always comes first. Keeping the first occurrence on dedup means Nordpool wins without any special-casing. This is a silent, unconditional guarantee — it fires even if something unexpected produces duplicates in the future.

Alternative considered: assert no duplicates and raise. Rejected because a crash is worse than silently preferring the authoritative source.

**Decision 3: "Future" means `slot_start.date() > today` (strictly tomorrow or later)**

Today's slots are already covered by real Nordpool data. The fallback is only needed for days Nordpool hasn't published yet. Using `>=` today would exclude today's slots correctly; `> today` (strictly after today) is the clearest expression of the intent.

## Risks / Trade-offs

- **If ML inference hasn't run today yet, no tomorrow fallback is available** → the planner plans only for remaining hours of today. Acceptable: this is honest behaviour. The `get_all_input_data` function runs inference before fetching prices, so in practice fresh D+1 slots should exist for tomorrow by the time the fallback is called.
- **Dedup silently drops data** → mitigated by keeping Nordpool (authoritative) and by the fact that a stale fallback slot has no value once the real price exists.

## Open Questions

None. Both changes are self-contained and independently testable.
