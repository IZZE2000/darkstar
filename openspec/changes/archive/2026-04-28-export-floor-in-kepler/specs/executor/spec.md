## REMOVED Requirements

### Requirement: Low SoC Export Prevention Override
**Reason**: Export SoC floor is now enforced by the Kepler planner as a constraint. The executor override is redundant since the planner replans every 30 minutes and SoC drift is minimal.
**Migration**: The `executor.override.low_soc_export_floor` config value is moved to `planner.export_floor_soc_percent`. Config migration handles the move automatically. No user action required.

## MODIFIED Requirements

### Requirement: Executor background loop cleans up async resources on exit

The `_async_run_loop` method SHALL wrap its main loop in a `try/finally` block that cancels all tracked background tasks and closes the `HAClient` session on every exit path (normal stop, early return, exception). The `OverrideEvaluator` SHALL no longer include `LOW_SOC_EXPORT_PREVENTION` in its evaluation. The `OverrideType` enum SHALL NOT include `LOW_SOC_EXPORT_PREVENTION`. The `low_soc_threshold` parameter SHALL be removed from `OverrideEvaluator.__init__`.

#### Scenario: Normal shutdown closes session
- **WHEN** the stop event is set and the while loop exits
- **THEN** all in-flight background tasks are cancelled
- **AND THEN** `ha_client.close()` is called
- **AND THEN** no `Unclosed client session` warning is logged

#### Scenario: Override evaluator does not evaluate low SoC export prevention
- **WHEN** a slot plan has `export_kw > 0` and current SoC is below the old threshold
- **THEN** the override evaluator SHALL return `OverrideResult(override_needed=False)`
- **AND** the planned export SHALL proceed as scheduled (the planner already ensured SoC is adequate)
