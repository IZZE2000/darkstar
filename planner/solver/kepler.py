"""
Kepler MILP Solver

Mixed-Integer Linear Programming solver for optimal battery scheduling.
Migrated from backend/kepler/solver.py during Rev K13 modularization.
"""

import logging
from collections import defaultdict
from datetime import timedelta  # Rev WH2
from typing import Any

import pulp  # type: ignore[import,no-redef]

from .types import EVChargerInput, KeplerConfig, KeplerInput, KeplerResult, KeplerResultSlot

logger = logging.getLogger("darkstar.kepler")


class KeplerSolver:
    def solve(self, input_data: KeplerInput, config: KeplerConfig) -> KeplerResult:
        """Solve the energy scheduling problem using MILP.

        Args:
            input_data: Input data containing slots, initial SoC, etc.
            config: Solver configuration parameters

        Returns:
            KeplerResult with optimized schedule slots and cost information
        """
        """
        Solve the energy scheduling problem using MILP.
        """
        slots = input_data.slots
        T = len(slots)
        if T == 0:
            return KeplerResult(
                slots=[],
                total_cost_sek=0.0,
                is_optimal=True,
                status_msg="No slots to schedule",
            )

        # Calculate slot duration in hours
        slot_hours: list[float] = []
        for s in slots:
            duration = (s.end_time - s.start_time).total_seconds() / 3600.0
            slot_hours.append(duration)

        # Problem Definition
        prob: Any = pulp.LpProblem("KeplerSchedule", pulp.LpMinimize)

        # Variables (all in kWh per slot)
        charge: dict[int, Any] = pulp.LpVariable.dicts("charge_kwh", range(T), lowBound=0.0)  # type: ignore[reportUnknownMemberType]
        discharge: dict[int, Any] = pulp.LpVariable.dicts("discharge_kwh", range(T), lowBound=0.0)  # type: ignore[reportUnknownMemberType]
        grid_import: dict[int, Any] = pulp.LpVariable.dicts("import_kwh", range(T), lowBound=0.0)  # type: ignore[reportUnknownMemberType]
        grid_export: dict[int, Any] = pulp.LpVariable.dicts("export_kwh", range(T), lowBound=0.0)  # type: ignore[reportUnknownMemberType]
        curtailment: dict[int, Any] = pulp.LpVariable.dicts(  # type: ignore[reportUnknownMemberType]
            "curtailment_kwh", range(T), lowBound=0.0
        )
        load_shedding: dict[int, Any] = pulp.LpVariable.dicts(  # type: ignore[reportUnknownMemberType]
            "load_shedding_kwh", range(T), lowBound=0.0
        )

        # Water heating as deferrable load (Rev K17)
        water_enabled: bool = config.water_heating_power_kw > 0
        water_heat: dict[int, Any]
        water_start: dict[int, Any] | None
        needs_water_start: bool
        if water_enabled:
            water_heat = pulp.LpVariable.dicts("water_heat", range(T), cat="Binary")  # type: ignore[reportUnknownMemberType]
            # Optimization (Rev K16): Only create water_start if needed for constraints
            # This saves ~T binary variables when spacing/start_penalty are disabled
            needs_water_start = (
                config.water_min_spacing_hours > 0 or config.water_block_start_penalty_sek > 0
            )
            if needs_water_start:
                water_start = pulp.LpVariable.dicts("water_start", range(T), cat="Binary")  # type: ignore[reportUnknownMemberType]
            else:
                water_start = None
        else:
            water_heat = dict.fromkeys(range(T), 0)
            water_start = None
            needs_water_start = False

        # EV Charging as deferrable load (per-device, multi-charger support)
        # Only create variables for plugged-in chargers
        plugged_chargers: list[EVChargerInput] = [c for c in config.ev_chargers if c.plugged_in]
        ev_any_enabled: bool = len(plugged_chargers) > 0

        # Per-device indexed variables: ev_charge[device_id][t], ev_energy[device_id][t]
        # dict[charger_id -> dict[t -> lp_var]]
        ev_charge: dict[str, dict[int, Any]] = {}
        ev_energy: dict[str, dict[int, Any]] = {}
        # Per-device incentive bucket variables: ev_bucket_charged[device_id][bucket_idx]
        ev_bucket_charged: dict[str, dict[int, Any]] = {}

        for charger in plugged_chargers:
            d = charger.id
            safe_d = d.replace("-", "_").replace(".", "_")
            if charger.deadline:
                logger.info(
                    "EV %s: deadline constraint active at %s",
                    d,
                    charger.deadline.strftime("%Y-%m-%d %H:%M"),
                )
            else:
                logger.info("EV %s: no deadline constraint", d)

            ev_charge[d] = pulp.LpVariable.dicts(  # type: ignore[reportUnknownMemberType]
                f"ev_charge_{safe_d}", range(T), cat="Binary"
            )
            ev_energy[d] = pulp.LpVariable.dicts(  # type: ignore[reportUnknownMemberType]
                f"ev_energy_{safe_d}_kwh", range(T), lowBound=0.0
            )
            buckets = charger.incentive_buckets or []
            num_buckets = len(buckets)
            ev_bucket_charged[d] = pulp.LpVariable.dicts(  # type: ignore[reportUnknownMemberType]
                f"ev_bucket_{safe_d}", range(num_buckets), lowBound=0.0
            )

        # any_ev_charging[t]: auxiliary binary - 1 if ANY charger is active in slot t
        any_ev_charging: dict[int, Any]
        if ev_any_enabled:
            any_ev_charging = pulp.LpVariable.dicts(  # type: ignore[reportUnknownMemberType]
                "any_ev_charging", range(T), cat="Binary"
            )
        else:
            any_ev_charging = dict.fromkeys(range(T), 0)

        # SoC state variables (T+1 states for T slots)

        # SoC state variables (T+1 states for T slots)
        min_soc_kwh: float = config.capacity_kwh * config.min_soc_percent / 100.0
        max_soc_kwh: float = config.capacity_kwh * config.max_soc_percent / 100.0

        soc: dict[int, Any] = pulp.LpVariable.dicts(  # type: ignore[reportUnknownMemberType]
            "soc_kwh", range(T + 1), lowBound=0.0, upBound=config.capacity_kwh
        )

        # Slack variables
        soc_violation: dict[int, Any] = pulp.LpVariable.dicts(  # type: ignore[reportUnknownMemberType]
            "soc_violation_kwh", range(T + 1), lowBound=0.0
        )
        target_under_violation: Any = pulp.LpVariable(
            "target_under_violation_kwh", lowBound=0.0
        )  # Penalty for being BELOW target at end of horizon
        import_breach: dict[int, Any] = pulp.LpVariable.dicts(  # type: ignore[reportUnknownMemberType]
            "import_breach_kwh", range(T), lowBound=0.0
        )
        ramp_up: dict[int, Any] = pulp.LpVariable.dicts("ramp_up_kwh", range(T), lowBound=0.0)  # type: ignore[reportUnknownMemberType]
        ramp_down: dict[int, Any] = pulp.LpVariable.dicts("ramp_down_kwh", range(T), lowBound=0.0)  # type: ignore[reportUnknownMemberType]

        # Discomfort variable removed.
        # "Block Overshoot" variable (soft penalty for massive blocks)
        block_overshoot: dict[int, Any] = pulp.LpVariable.dicts(  # type: ignore[reportUnknownMemberType]
            "block_overshoot", range(T), lowBound=0.0
        )

        # Per-device incentive bucket setup
        for charger in plugged_chargers:
            d = charger.id
            buckets = charger.incentive_buckets or []
            num_buckets = len(buckets)
            if num_buckets == 0:
                continue

            ev_capacity: float = charger.battery_capacity_kwh
            ev_current_kwh: float = ev_capacity * (charger.current_soc_percent / 100.0)

            prev_threshold_soc: float = 0.0
            accum_energy_cap: float = 0.0

            for i, b in enumerate(buckets):
                bucket_soc_range: float = b.threshold_soc - prev_threshold_soc
                bucket_capacity_kwh: float = max(0.0, ev_capacity * (bucket_soc_range / 100.0))

                already_full: float = max(
                    0.0, min(bucket_capacity_kwh, ev_current_kwh - accum_energy_cap)
                )
                remaining_cap: float = max(0.0, bucket_capacity_kwh - already_full)

                prob += ev_bucket_charged[d][i] <= remaining_cap

                prev_threshold_soc = b.threshold_soc
                accum_energy_cap += bucket_capacity_kwh

            # Total energy for this device must equal sum of its buckets
            prob += pulp.lpSum(ev_energy[d][t] for t in range(T)) == pulp.lpSum(
                ev_bucket_charged[d][i] for i in range(num_buckets)
            )

        # Slack variables for soft constraints (Phase 2)
        # We index min_kwh_violation by day index (max 365 days, sufficient size)
        water_min_kwh_violation: dict[int, Any] = pulp.LpVariable.dicts(  # type: ignore[reportUnknownMemberType]
            "water_min_kwh_violation", range(100), lowBound=0.0
        )

        # Initial SoC Constraint
        initial_soc: float = max(0.0, min(config.capacity_kwh, input_data.initial_soc_kwh))
        prob += soc[0] == initial_soc

        # Objective Function Terms
        total_cost: list[Any] = []

        # Penalty constants
        MIN_SOC_PENALTY = 1000.0  # Hard constraint - don't violate min_soc!
        # Target penalty comes from config (derived from risk_appetite in pipeline)
        target_soc_penalty = config.target_soc_penalty_sek
        curtailment_penalty = config.curtailment_penalty_sek
        LOAD_SHEDDING_PENALTY = 10000.0
        IMPORT_BREACH_PENALTY = 5000.0

        for t in range(T):
            s: Any = slots[t]
            h: float = slot_hours[t]

            # Water heating load for this slot (kWh)
            water_load_kwh: Any = (
                water_heat[t] * config.water_heating_power_kw * h if water_enabled else 0
            )

            # Per-device EV constraints
            for charger in plugged_chargers:
                d = charger.id
                # Energy coupling: binary ON/OFF at max power
                prob += ev_energy[d][t] == ev_charge[d][t] * charger.max_power_kw * h

                # Deadline constraint: zero charging after deadline
                if charger.deadline is not None and s.end_time > charger.deadline:
                    prob += ev_energy[d][t] == 0.0

                # Grid-only constraint: EV cannot charge from battery discharge
                prob += ev_energy[d][t] <= grid_import[t] + s.pv_kwh + 1e-6

            # any_ev_charging[t] linking constraints
            if ev_any_enabled:
                for charger in plugged_chargers:
                    d = charger.id
                    prob += any_ev_charging[t] >= ev_charge[d][t]
                prob += any_ev_charging[t] <= pulp.lpSum(ev_charge[d][t] for d in ev_charge)
                # Discharge blocking: block when any charger active
                M_discharge = config.max_discharge_power_kw * h
                prob += discharge[t] <= (1 - any_ev_charging[t]) * M_discharge

            # Total EV energy in this slot (sum across all plugged-in chargers)
            total_ev_energy_t: Any = (
                pulp.lpSum(ev_energy[d][t] for d in ev_energy) if ev_any_enabled else 0.0
            )

            # Energy Balance Constraint (water and EV loads added to demand side)
            prob += (
                s.load_kwh
                + water_load_kwh
                + total_ev_energy_t
                + charge[t]
                + grid_export[t]
                + curtailment[t]
                == s.pv_kwh + discharge[t] + grid_import[t] + load_shedding[t]
            )

            # Phase 4 Pivot: Re-introduced water_start binary for guidance
            if water_enabled and needs_water_start:
                assert water_start is not None
                if t == 0:
                    prob += water_start[t] == water_heat[t]
                else:
                    prob += water_start[t] >= water_heat[t] - water_heat[t - 1]

            # Rev WH2: Force specific slots ON (Mid-block locking)
            if water_enabled and config.force_water_on_slots:
                for t_idx in config.force_water_on_slots:
                    if 0 <= t_idx < T:
                        prob += water_heat[t_idx] == 1

            # Battery Dynamics Constraint
            prob += soc[t + 1] == soc[t] + charge[t] * config.charge_efficiency - discharge[t] / (
                config.discharge_efficiency if config.discharge_efficiency > 0 else 1.0
            )

            # Power Limits
            max_chg_kwh: float = config.max_charge_power_kw * h
            max_dis_kwh: float = config.max_discharge_power_kw * h

            prob += charge[t] <= max_chg_kwh
            prob += discharge[t] <= max_dis_kwh

            if config.max_export_power_kw is not None:
                prob += grid_export[t] <= config.max_export_power_kw * h

            if config.max_import_power_kw is not None:
                prob += grid_import[t] <= config.max_import_power_kw * h

            # Soft Grid Import Limit
            if config.grid_import_limit_kw is not None:
                limit_kwh: float = config.grid_import_limit_kw * h
                prob += grid_import[t] <= limit_kwh + import_breach[t]

            # Rev E4: Strict Export Toggle
            if not config.enable_export:
                prob += grid_export[t] == 0

            # Ramping Constraints
            if t > 0:
                prob += (charge[t] - discharge[t]) - (charge[t - 1] - discharge[t - 1]) == ramp_up[
                    t
                ] - ramp_down[t]
            else:
                prob += ramp_up[t] == 0
                prob += ramp_down[t] == 0

            # Objective Terms
            # Wear cost modeling: Apply 50% of config value per action (charge OR discharge)
            # so that a full cycle (charge + discharge) costs exactly config.wear_cost_sek_per_kwh
            slot_wear_cost: Any = (charge[t] + discharge[t]) * config.wear_cost_sek_per_kwh * 0.5
            slot_import_cost: Any = grid_import[t] * s.import_price_sek_kwh
            effective_export_price: float = (
                s.export_price_sek_kwh - config.export_threshold_sek_per_kwh
            )
            slot_export_revenue: Any = grid_export[t] * effective_export_price
            slot_ramping_cost: Any = (
                (ramp_up[t] + ramp_down[t]) / h
            ) * config.ramping_cost_sek_per_kw
            slot_curtailment_cost: Any = curtailment[t] * curtailment_penalty
            slot_shedding_cost: Any = load_shedding[t] * LOAD_SHEDDING_PENALTY
            slot_import_breach_cost: Any = import_breach[t] * IMPORT_BREACH_PENALTY

            # NOTE: Rev K20 stored_energy_cost was removed - it incorrectly made
            # charging unprofitable by adding cost on discharge without offsetting
            # credit on charge. The terminal_value and wear_cost are sufficient
            # for arbitrage decisions.

            slot_ev_cost: float = 0.0  # EV incentive handled in aggregate objective below

            total_cost.append(
                slot_import_cost
                - slot_export_revenue
                + slot_wear_cost
                + slot_ramping_cost
                + slot_curtailment_cost
                + slot_shedding_cost
                + slot_import_breach_cost
                + slot_ev_cost
            )

            # Soft Min/Max SoC Constraints
            prob += soc[t] >= min_soc_kwh - soc_violation[t]
            prob += soc[t] <= max_soc_kwh

        # Terminal constraints
        prob += soc[T] >= min_soc_kwh - soc_violation[T]
        prob += soc[T] <= max_soc_kwh

        # Terminal SoC Target (BIDIRECTIONAL soft constraint)
        # Penalize both being UNDER target (risk) AND OVER target (missed discharge opportunity)
        target_soc_kwh: float = (
            config.target_soc_kwh if config.target_soc_kwh is not None else min_soc_kwh
        )

        # Terminal SoC Target (BIDIRECTIONAL soft constraint)
        # Penalize both being UNDER target (risk) AND OVER target (missed discharge opportunity)
        target_soc_kwh = config.target_soc_kwh if config.target_soc_kwh is not None else min_soc_kwh

        if config.target_soc_kwh is not None:
            # Under target: soc[T] >= target - under_violation
            prob += soc[T] >= target_soc_kwh - target_under_violation

            # Penalize UNDER target (important)
            total_cost.append(target_soc_penalty * target_under_violation)
        else:
            # If no target, we don't care where we end up (within min_soc limits)
            pass

        # Rev // F51: Removed legacy EV target SoC constraint.
        # Replaced by Incentive Buckets in the objective function.

        # Water Heating Constraints (Rev K17/K18/K21)
        gap_violation_penalty: float = 0.0
        # spacing_violation_penalty removed in PERF1
        sorted_days: list[Any] = []  # Initialize to avoid unbound error
        if water_enabled:
            avg_slot_hours: float = sum(slot_hours) / len(slot_hours) if slot_hours else 0.25
            water_kwh_per_slot: float = config.water_heating_power_kw * avg_slot_hours

            # Constraint 1: Per-day min_kwh requirements
            # Group slots by date to apply daily minimum constraints
            # Rev WH2: Smart Deferral - extend buckets into next morning
            slots_by_day: defaultdict[Any, list[int]] = defaultdict(list)
            defer_hours: float = config.defer_up_to_hours

            for t in range(T):
                dt: Any = slots[t].start_time
                bucket_date: Any = dt.date()
                if defer_hours > 0 and dt.hour < defer_hours:
                    bucket_date = bucket_date - timedelta(days=1)

                slots_by_day[bucket_date].append(t)

            # Sort days to identify "today" (first day in horizon)
            sorted_days: list[Any] = sorted(slots_by_day.keys())

            for i, day in enumerate(sorted_days):
                day_slot_indices: list[int] = slots_by_day[day]
                if i == 0:
                    # First day: reduce by what's already heated today
                    day_min_kwh: float = max(
                        0.0,
                        config.water_heating_min_kwh - config.water_heated_today_kwh,
                    )
                else:
                    # Future days: full daily requirement
                    day_min_kwh = config.water_heating_min_kwh

                if day_min_kwh > 0:
                    # Rev K16 Phase 2: Soft Constraint
                    # sum(...) >= day_min_kwh - violation
                    prob += (  # type: ignore[operator]
                        pulp.lpSum(water_heat[t] for t in day_slot_indices) * water_kwh_per_slot
                        >= day_min_kwh - water_min_kwh_violation[i]
                    )

            # Constraint 2: Soft Block Breaker (Rev K16 Phase 1 Pivot)
            # Replaces linear discomfort.
            # Goal: Penalize blocks longer than comfort-level-dependent hours.
            # Logic: In any window of size (MaxBlock + 1), we should have at most MaxBlock heated slots.
            # If we have MaxBlock + 1, we are overshooting.
            if config.water_block_penalty_sek > 0:
                max_block_hours: float = (
                    config.max_block_hours
                )  # Rev K24: Dynamic per comfort level
                max_block_slots: int = int(max_block_hours / avg_slot_hours)
                # Window size = max_block_slots + 1 (e.g., 9 slots if max is 8)
                window_size: int = max_block_slots + 1

                for t in range(T - window_size + 1):
                    # sum(water_heat[t : t+window]) <= max_block_slots + overshoot[t]
                    prob += (  # type: ignore[operator]
                        pulp.lpSum(water_heat[j] for j in range(t, t + window_size))
                        <= max_block_slots + block_overshoot[t]
                    )

            # Constraint 3: Hard Spacing Constraint (Option 4: Restore Hard Pruning)
            if config.water_min_spacing_hours > 0:
                spacing_slots: int = max(1, int(config.water_min_spacing_hours / avg_slot_hours))
                M: int = spacing_slots
                for t in range(T):
                    # Check preceding slots in spacing window
                    # Option 4: HARD Constraint (No slack variable)
                    # sum(...) + start*M <= M
                    start_idx: int = max(0, t - spacing_slots)
                    prob += (  # type: ignore[operator]
                        pulp.lpSum(water_heat[j] for j in range(start_idx, t)) + water_start[t] * M  # type: ignore[operator]
                        <= M
                    )

            # Constraint 4: Max Block Length (Prevent "Single Huge Block")
            # REMOVED in Rev K16 Phase 1: Replaced by linear discomfort cost which naturally
            # breaks up blocks if penalty is low enough.

        # Terminal SoC Target (BIDIRECTIONAL soft constraint)
        # - min_soc violation: HARD penalty (1000 SEK/kWh)
        # - target violation: SOFT penalty (from config, derived from risk_appetite)
        #   * UNDER target: Risk penalty (configurable)
        #   * OVER target: Opportunity cost penalty (same as under)
        # - gap violation: SOFT comfort penalty (Rev K18)
        prob += (  # type: ignore[operator]
            pulp.lpSum(total_cost)
            + MIN_SOC_PENALTY * pulp.lpSum(soc_violation)
            + gap_violation_penalty  # Deprecated in K16 (0.0)
            + gap_violation_penalty  # Deprecated in K16 (0.0)
            + (
                pulp.lpSum(block_overshoot[t] for t in range(T)) * config.water_block_penalty_sek
                if water_enabled
                else 0.0
            )  # Rev K16: Soft Block Penalty
            + (
                pulp.lpSum(water_start[t] for t in range(T)) * config.water_block_start_penalty_sek  # type: ignore[index,reportUnknownVariableType]
                if water_enabled and needs_water_start and config.water_block_start_penalty_sek > 0
                else 0.0
            )  # Rev WH2: Block start penalty
            # Rev K16 Phase 5: Symmetry Breaker
            # Add tiny cost (increasing with t) to break ties in flat price scenarios
            + (pulp.lpSum(water_heat[t] * (t * 1e-5) for t in range(T)) if water_enabled else 0.0)
            # Rev K16 Phase 2: Reliability Penalties
            + (
                pulp.lpSum(water_min_kwh_violation[i] for i in range(len(sorted_days)))
                * config.water_reliability_penalty_sek
                if water_enabled
                else 0.0
            )
            # Per-device incentive bucket values: subtract from objective (negative cost = gain)
            - (
                pulp.lpSum(
                    ev_bucket_charged[charger.id][i] * charger.incentive_buckets[i].value_sek
                    for charger in plugged_chargers
                    for i in range(len(charger.incentive_buckets or []))
                )
                if ev_any_enabled
                else 0.0
            )
        )

        # Solve using GLPK (available in Alpine) or CBC as fallback
        import time

        build_start: float = time.time()
        # Solver setup is fast, but let's track the overhead of calling the solver command
        # Note: pulp.LpProblem construction happened above, so 'build_time' here is mostly
        # just the overhead of writing the LP file in prob.solve()

        try:
            # Try GLPK first (installed in Alpine Docker image) with timeout
            solver_cmd: Any = pulp.GLPK_CMD(msg=False, timeLimit=30)
            prob.solve(solver_cmd)  # type: ignore[reportUnknownMemberType]
        except Exception:
            # Fall back to CBC if GLPK not available, also with timeout
            solver_cmd: Any = pulp.PULP_CBC_CMD(msg=False, timeLimit=30)
            prob.solve(solver_cmd)  # type: ignore[reportUnknownMemberType]

        solve_end: float = time.time()

        # Extract Results
        status: str = pulp.LpStatus[prob.status]  # type: ignore[index]
        is_optimal: bool = status == "Optimal"

        # Log Performance Metrics
        solve_duration: float = solve_end - build_start  # This is just the solve() call duration
        # Count stats
        var_count: int = len(prob.variables())  # type: ignore[reportUnknownMemberType,arg-type]
        const_count: int = len(prob.constraints)  # type: ignore[reportUnknownMemberType,arg-type]

        if not is_optimal:
            prob.writeLP("kepler_debug.lp")  # type: ignore[reportUnknownMemberType]
            print(f"Solver failed: {status}. LP written to kepler_debug.lp")

        result_slots: list[KeplerResultSlot] = []
        final_total_cost: float = 0.0

        if is_optimal:
            for t in range(T):
                s: Any = slots[t]
                h: float = slot_hours[t]

                c_val: float | None = pulp.value(charge[t])  # type: ignore[assignment]
                d_val: float | None = pulp.value(discharge[t])  # type: ignore[assignment]
                i_val: float | None = pulp.value(grid_import[t])  # type: ignore[assignment]
                e_val: float | None = pulp.value(grid_export[t])  # type: ignore[assignment]
                soc_val: float | None = pulp.value(soc[t + 1])  # type: ignore[assignment]

                # Water heating power (kW) from binary decision
                if water_enabled:
                    w_val: float | None = pulp.value(water_heat[t])  # type: ignore[assignment]
                    w_kw: float = config.water_heating_power_kw if w_val and w_val > 0.5 else 0.0
                else:
                    w_kw: float = 0.0

                # Per-device EV charging results
                ev_charger_results: dict[str, float] = {}
                total_ev_kw: float = 0.0
                for charger in plugged_chargers:
                    d = charger.id
                    ev_val: float | None = pulp.value(ev_energy[d][t])  # type: ignore[assignment]
                    device_kw: float = ev_val / h if ev_val is not None and h > 0 else 0.0
                    ev_charger_results[d] = device_kw
                    total_ev_kw += device_kw
                ev_kw = total_ev_kw

                wear: float = (
                    (c_val + d_val) * config.wear_cost_sek_per_kwh * 0.5
                    if c_val is not None and d_val is not None
                    else 0.0
                )
                cost: float = (
                    (i_val * s.import_price_sek_kwh) - (e_val * s.export_price_sek_kwh) + wear
                    if i_val is not None and e_val is not None
                    else 0.0
                )
                final_total_cost += cost

                result_slots.append(
                    KeplerResultSlot(
                        start_time=s.start_time,
                        end_time=s.end_time,
                        charge_kwh=c_val,  # type: ignore[arg-type]
                        discharge_kwh=d_val,  # type: ignore[arg-type]
                        grid_import_kwh=i_val,  # type: ignore[arg-type]
                        grid_export_kwh=e_val,  # type: ignore[arg-type]
                        soc_kwh=soc_val,  # type: ignore[arg-type]
                        cost_sek=cost,
                        import_price_sek_kwh=s.import_price_sek_kwh,
                        export_price_sek_kwh=s.export_price_sek_kwh,
                        water_heat_kw=w_kw,
                        ev_charge_kw=ev_kw,
                        ev_charger_results=ev_charger_results,
                        is_optimal=True,
                    )
                )

            # Update the log with correct cost (since we calculated it in the loop)
            logger_perf = logging.getLogger("darkstar.performance")
            logger_perf.setLevel(logging.INFO)  # Ensure we see it
            logger_perf.info(
                "Kepler Solved: %d slots in %.3fs (Vars: %d, Const: %d) | Cost: %.2f SEK",
                T,
                solve_duration,
                var_count,
                const_count,
                final_total_cost,
            )

        return KeplerResult(
            slots=result_slots,
            total_cost_sek=final_total_cost,
            is_optimal=is_optimal,
            status_msg=status,
        )
