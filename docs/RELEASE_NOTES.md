## [v2.5.8-beta] - COMPLETE AURORA Pipeline Fix - 2026-01-22

> [!IMPORTANT]
> **FINAL COMPLETE FIX FOR AURORA ML PIPELINE**
> This release provides the definitive fix for the AURORA inference pipeline failure.
> All previous versions (v2.5.6-beta, v2.5.7-beta) were incomplete and still failed.

**🐛 Complete Fix - All 10 Locations**

- **ml/corrector.py**: Fixed ALL 6 occurrences of old data structure access
  - Lines 347, 348: Level 1 statistician corrections
  - Lines 367, 368: Level 2 ML model fallback
  - Lines 424, 425: Stats fallback values
  - Line 436: ML PV correction
  - Line 443: ML load correction
- **inputs.py**: Fixed 2 occurrences (completed in v2.5.6-beta)
- **backend/api/routers/forecast.py**: Fixed 1 occurrence (completed in v2.5.6-beta)
- **ml/simulation/data_loader.py**: Fixed 1 occurrence (completed in v2.5.6-beta)

**Technical Details**

The AURORA ML pipeline has 3 phases:
1. **Forward Generation** ✅ (was working - generates base forecasts)
2. **Correction Pipeline** ❌ (was failing - applies ML corrections)
3. **Database Persistence** ✅ (never reached due to phase 2 failure)

The error occurred in phase 2 where `predict_corrections()` calls `get_forecast_slots()` and expects nested data structure, but 6 locations in `ml/corrector.py` were still using the old flat format.

**Data Structure Migration**:
- **Old**: `rec["pv_forecast_kwh"]`, `rec["load_forecast_kwh"]`
- **New**: `rec["final"]["pv_kwh"]`, `rec["final"]["load_kwh"]`

**Comprehensive Fix Verification**:
- ✅ All 4 files that import `get_forecast_slots()` are fixed
- ✅ All 10 total occurrences of old format access are updated
- ✅ Complete pipeline flow traced and verified
- ✅ No remaining old format usage in critical path

**Impact**:
- ✅ AURORA ML pipeline completes fully end-to-end
- ✅ Battery schedules generate with proper charging/discharging actions
- ✅ ML correction models work correctly for improved forecast accuracy
- ✅ Error correction and graduation path function properly
- ✅ No more flat SoC schedules in HA add-on

---

## [v2.5.7-beta] - Complete AURORA Pipeline Fix - 2026-01-22

> [!IMPORTANT]
> **COMPLETE FIX FOR AURORA ML PIPELINE**
> This release provides the complete fix for the AURORA inference pipeline failure.
> v2.5.6-beta was incomplete and still failed - this version fixes ALL affected files.

**🐛 Complete Fix**

- **All AURORA Pipeline Consumers Fixed**: Updated all 4 files that consume `get_forecast_slots()` data to use the correct nested structure
- **ml/corrector.py**: Fixed correction pipeline data access (2 locations)
- **backend/api/routers/forecast.py**: Fixed forecast stats calculation
- **ml/simulation/data_loader.py**: Fixed simulation data loading
- **inputs.py**: Already fixed in v2.5.6-beta

**Technical Details**

The previous v2.5.6-beta fix was incomplete - it only fixed `inputs.py` but missed 3 other critical files that also consume `get_forecast_slots()` data. The error was still occurring in the correction phase of the ML pipeline.

**Complete Data Structure Migration**:
- **Old**: `rec["pv_forecast_kwh"]`, `rec["load_forecast_kwh"]`
- **New**: `rec["final"]["pv_kwh"]`, `rec["final"]["load_kwh"]`

**Impact**:
- ✅ AURORA ML pipeline completes fully without any KeyError
- ✅ Battery schedules generate with proper charging/discharging actions
- ✅ Correction models work correctly for improved accuracy
- ✅ All forecast consumers use consistent data structure

---

## [v2.5.6-beta] - AURORA Pipeline Fix - 2026-01-22

> [!IMPORTANT]
> **CRITICAL FIX FOR AURORA ML PIPELINE**
> This release fixes the AURORA inference pipeline failure that caused flat SoC schedules in v2.5.5-beta.
> The ML models were working correctly, but forecast data retrieval was broken due to a data structure mismatch.

**🐛 Critical Fix**

- **AURORA Pipeline Failure**: Fixed `KeyError: 'pv_forecast_kwh'` that caused the AURORA ML inference pipeline to fail, resulting in flat battery schedules with no charging/discharging actions.
- **Data Structure Mismatch**: Updated `inputs.py` to use the new nested forecast data structure from `ml/api.py` that was introduced in recent versions but not properly propagated.

**Technical Details**

The ML API changed the forecast data structure from flat to nested:
- **Old format**: `{"pv_forecast_kwh": 1.5, "load_forecast_kwh": 0.8}`
- **New format**: `{"final": {"pv_kwh": 1.5, "load_kwh": 0.8}, "probabilistic": {...}}`

The `inputs.py` file was still expecting the old format, causing the pipeline to crash during forecast data retrieval (not during ML inference itself).

**Impact Fixed**:
- ✅ AURORA ML pipeline completes successfully
- ✅ Proper battery charging/discharging schedules generated
- ✅ Accurate error reporting (distinguishes ML failures from data retrieval failures)
- ✅ Fallback logic works correctly when models are actually missing

---

## [v2.5.5-beta] - Critical Symlink Fix - 2026-01-22

> [!CAUTION]
> **CRITICAL HOTFIX FOR v2.5.4-beta USERS**
> If you installed v2.5.4-beta, the add-on is completely broken due to a symlink issue.
> This release fixes the critical startup crash. **Upgrade immediately.**

**🐛 Critical Fix**

- **Symlink Path Issue**: Fixed complete system failure where the application could not access persistent storage (database, ML models, logs, schedule cache). Root cause was a broken symlink that caused the app to use ephemeral storage instead of `/share/darkstar/`.

**Technical Details**

The Dockerfile incorrectly created `/app/data` as a directory, causing `ln -sf /share/darkstar /app/data` to create a **nested symlink** (`/app/data/darkstar -> /share/darkstar`) instead of a **direct symlink** (`/app/data -> /share/darkstar`).

**Impact**:
- ❌ Database errors: `sqlite3.OperationalError: no such table: slot_observations`
- ❌ ML model loading failures: `[LightGBM] [Fatal] Could not open data/ml/models/*.lgb`
- ❌ Forecast generation failures
- ❌ Schedule planning failures
- ❌ Complete add-on failure

**Changes**:
- Removed problematic `RUN mkdir -p data/ml/models` from `darkstar/Dockerfile`
- Enhanced `backend/main.py` to respect `DB_PATH` environment variable for consistency with Alembic migrations

**User Data**: All persistent data in `/share/darkstar/` is safe and untouched.

**Upgrade Path**:
- Users on v2.5.4-beta: **Must upgrade** to v2.5.5-beta
- Users on v2.5.3-beta and earlier: Can upgrade safely

---

## [v2.5.4-beta] - HA Add-on Critical Planner Fix - 2026-01-21

> [!CAUTION]
> **CRITICAL FIX FOR HA ADD-ON USERS EXPERIENCING FLAT SCHEDULES**
> If your HA Add-on deployment is producing "flat" schedules with no charge/discharge actions
> (only water heating), this release fixes the regression introduced in v2.5.0-beta.

**🐛 Critical Fixes**

- **HA Add-on Planner Regression (REV PERS2)**: Fixed complete planner failure in HA Add-on deployments where ML models were not included in Docker images, causing the planner to produce trivial schedules with zero forecasts. Solve times dropped from expected 30-60s to 0.2s with no battery actions.

- **Persistent Storage Architecture (REV PERS1)**: Fixed critical bug where ML models and `schedule.json` were stored in ephemeral container locations, being lost on every restart. All persistent data now correctly uses `/share/darkstar/` via symlinked `data/` directory.

**Root Causes Identified**

1. **Dockerfile Bug**: Only copied `ml/*.py`, not `ml/models/*.lgb` → Images shipped without baseline models
2. **Path Inconsistencies**: Mixed use of `ml/models/` and `data/ml/models/` across 10+ files
3. **Silent Failure**: `_load_models()` returned empty dict without error → Zero forecasts → Trivial optimization

**Changes Implemented**

- **Model Shipping**: `darkstar/Dockerfile` now includes 10 baseline ML models (40MB)
- **First-Boot Bootstrap**: `darkstar/run.sh` copies shipped models to persistent storage on startup
- **Robust Fallback**: When no ML models available:
  - **Load Forecast**: Uses 0.5 kWh baseline average (2 kW constant load)
  - **PV Forecast**: Uses Open-Meteo radiation data scaled by system capacity
- **Path Consistency**: Updated 10 files to use `data/ml/models` and `data/schedule.json`
- **Critical Logging**: Models missing now logs `CRITICAL` error instead of silent `Info`

**Impact**

- ✅ Fresh HA Add-on installs work immediately with baseline models
- ✅ Planner never silently runs with zero forecasts (logs critical + uses fallback)
- ✅ ML models and schedules persist across container restarts
- ✅ User-trained models are never overwritten by shipped baselines
- ✅ All code paths use consistent persistent storage locations

**Upgrade Notes**

- **First startup**: Logs will show "📦 Copied baseline model" messages (10 files)
- **Subsequent startups**: Models already present, skips copy
- **Local training**: User-trained models remain untouched in `/share/darkstar/ml/models/`

**Files Modified** (30 total)

- Core: `ml/forward.py`, `darkstar/Dockerfile`, `darkstar/run.sh`
- Path fixes: `ml/train.py`, `ml/corrector.py`, `ml/evaluate.py`, `ml/training_orchestrator.py`, `planner/output/schedule.py`, `executor/config.py`
- Scripts: `scripts/health_check.py`, `scripts/train_corrector.py`, `scripts/diagnose_ml.py`
- API: `backend/api/routers/learning.py`, `backend/api/routers/schedule.py`, `backend/services/planner_service.py`
- Docs: `docs/PLAN.md`, `docs/ARCHITECTURE.md`

---

## [v2.5.3-beta] - Critical Migration Hotfix - 2026-01-21

> [!CAUTION]
> **CRITICAL HOTFIX FOR v2.5.2-beta USERS**
> If you upgraded to v2.5.2-beta as a Home Assistant add-on and experienced database errors
> (`no such column: slot_forecasts.base_load_forecast_kwh`), this release fixes the issue.
> Your system will automatically migrate on first startup.

**🐛 Critical Fix**

- **HA Add-on Database Migration**: Fixed complete system failure for Home Assistant add-on users upgrading to v2.5.2-beta. The HA add-on startup script now automatically runs Alembic database migrations before starting the server, preventing "no such column" errors when new schema features are added.

**Technical Details**

- Added automatic database schema migration to `darkstar/run.sh` (HA add-on entrypoint)
- Migration runs after config setup but before uvicorn startup
- Idempotent and safe - preserves all existing data
- Fresh installations create database with full schema
- Already-migrated databases skip gracefully (~0.1s overhead)

**What to Expect**

- **First startup after upgrade**: Migration runs in ~0.5-2 seconds
- **Subsequent startups**: Migration is skipped (database already current)
- **New installations**: Fresh database created with correct schema

---

## [v2.5.2-beta] - ML Model Training Complete - 2026-01-21

**Core Features**
*   **Automatic ML Training (REV ARC11)**: The system now autonomously trains and updates both Main and Error Correction models based on a configurable schedule (default: Mon/Thu at 03:00).
*   **Training Orchestrator**: A unified engine (`training_orchestrator.py`) handles model lifecycle, including safety backups, graduation level checks, and partial failure recovery.
*   **Training UI**: New `ModelTrainingCard` provides real-time visibility into training status, history, and schedule.
*   **Corrector Training**: Integrated flow to train error correction models (requires "Graduate" maturity level).

**Fixes & Improvements**
*   **Chart Reliability**: Fixed history data merging and implemented smart auto-scaling that dynamically adjusts the chart window (24h vs 48h) based on available price data. Fixed timezone display issues.
*   **DevEx**: Performance reports are now correctly ignored in git to preventing repo bloat. Enforced ISO 24h date formats in UI.
*   **CI/CD**: Fixed frontend linting and backend test configuration.
*   **Documentation**: Updated docs with ARC11 completion.

---

## [v2.5.1-beta] - Recorder & Data Integrity Fixes - 2026-01-20

This maintenance release focuses on resolving critical data integrity issues in the
Recorder and ensuring accurate historical visualization and analysis.

> [!IMPORTANT]
> **v2.5.1-beta Startup Stabilization Update**
> This version includes critical fixes for config migration and database path resolution.

> [!WARNING]
> **Database Migration Required**
> This release includes significant database architecture changes (SQLAlchemy + Alembic
> migration). The system will automatically migrate your database on first startup, but this
> process may take a bit extra time for installations with large historical datasets. Backup
> your data/planner_learning.db file before updating as a precaution if you care about your recorded data.

## 🐛 Major Bug Fixes

### **Recorder & Data Pipeline**
- **Grid Meter Logic (REV F7)**: Fixed critical recorder crashes when referencing
configuration for specific grid meter types
- **Backfill Engine**: Resolved initialization failures that prevented historical data
backfilling on startup
- **Data Capture**: Improved robustness of battery power sign handling and grid import/
export recording

### **Historical Visualization**
- **History Overlay**: Fixed a major data mapping issue where historical planned actions (
charge/discharge bars, SoC targets) appeared as zero or missing in the "Schedule >
History" view
- **Forecast Comparison**: Corrected logical errors in the "Forecast vs Actual"
correlation analysis used by the Reflex learning engine

### **System Architecture & Performance**
- **Database Modernization (REV ARC9-ARC11)**: Complete migration to SQLAlchemy ORM with
Alembic migrations and full async/await implementation for all database operations
- **Kepler Optimization**: Upgraded water heating spacing constraint from O(T×S) to O(T)
linear complexity for faster planning
- **API Stability**: Fixed critical API routes that used blocking database calls, unified
router prefixes, and restored lost Aurora ML functionality

## 🚀 New Features

### **Machine Learning Pipeline (REV ML2)**
- **Load Disaggregation Framework**: Production-grade system to separate base load from
controllable appliances (water heater, EV, heat pump) for improved ML forecast accuracy
- **Smart Fallback**: Graceful degradation when individual sensors fail, with automatic
data quality monitoring

### **Structured Logging System (REV H2)**
- **JSON Logging**: Professional structured logging with rotation and management
- **Live Log Viewer**: Real-time log streaming in Debug UI with auto-scroll and viewport-
adaptive height

### **Developer Experience (REV DX4-DX5)**
- **Conventional Commits**: Enforced commit message standards with automated validation
- **UV Package Manager**: High-performance Python dependency management
- **Advanced Benchmarking**: Professional-grade performance analysis tools

## 🎨 User Experience Improvements

### **Chart & Visualization**
- **Dynamic Scaling**: Chart Y-axes now scale based on actual system configuration (solar
capacity, inverter limits)
- **Unit Conversion**: Fixed energy (kWh) to power (kW) conversion for consistent 15-
minute slot display
- **Price Visualization**: Improved price line rendering with step-line interpolation

### **Configuration & Stability**
- **Type Safety**: Robust type coercion prevents configuration corruption
- **Config Cleanup**: Removed leaked configuration keys and fixed YAML formatting issues
- **Entity Validation**: Conditional validation that respects hardware toggles (battery/
solar/water heater)
- **Executor Resilience**: Fixed pause/boost button logic flaws and UI synchronization
issues

## 🧪 Quality Assurance
- **Test Suite Stabilization**: Addressed async/sync fixture incompatibilities and schema
mismatches in the automated test suite, ensuring reliable CI/CD checks for future updates
- **Performance Monitoring**: Integrated benchmarking into development workflow
- **Documentation**: Updated architecture documentation to reflect async migration

## 🔄 Migration Notes
- **Backward Compatibility**: All changes maintain full compatibility with existing
configurations
- **Automatic Migration**: Database schema migrations handle structural changes
automatically
- **Config Soft-Merge**: New configuration keys are added without overwriting user
settings

## [v2.5.0-beta] - Configuration & Compatibility - 2026-01-16

This release solidifies the **Configuration Architecture**. It introduces a unified battery configuration, finalizes the Settings UI visibility logic, and improves startup resilience.

> [!WARNING]
> **Breaking Configuration Changes**
> *   The structure of `config.yaml` has changed (REV F17).
> *   The `system_voltage_v` and capacity settings have been moved to the new `battery:` section.
> *   **Auto-Migration:** Darkstar will attempt to automatically migrate your config file on startup (REV F18). Please back up your `config.yaml` before updating.

### ✨ New Features

#### Unified Battery Configuration (REV F17)
*   **Single Source of Truth:** Battery limits (Capacity, Max Amps/Watts) are now centralized in the new `battery:` section.
*   **Auto-Calculation:** The planner now automatically converts between Amps and Watts based on your system voltage, removing the need for duplicate manual entry.

#### Conditional Settings Polish (REV F15)
*   **Smart Visibility:** Extended the conditional logic to all parameter sections. Settings for Battery Economics, S-Index, and Water Heating Deferral are now completely hidden if the respective hardware is disabled in the System Profile.

#### Developer Experience (REV DX3)
*   **Darkstar Dev Add-on:** A new development-focused Home Assistant add-on is available for contributors, featuring faster build times (amd64 only) and tracking the `dev` branch.

### 🐛 Fixes & Improvements

*   **REV F12: Scheduler Fast Start:** The planner now runs 10 seconds after startup instead of waiting for the full hour interval.
*   **REV F18: Config Soft Merge:** Start-up now automatically fills in missing configuration keys from `config.default.yaml` without overwriting your custom settings.
*   **REV E3 Safety Patch:** Added a hard safety limit (500A) to the Watt-control logic to prevent potential integer overflow issues (9600W -> 9600A interpretation bug).

---

## [v2.4.23-beta] - Profile Foundations & Dual Sensors - 2026-01-16

### Core Features
- **Inverter Profile Foundation (REV E5)**: Established a modular profile system to support brand-specific presets. This initial release focuses on the underlying infrastructure (e.g., brand-specific visibility for SoC targets) and currently supports Generic and Deye/SunSynk profiles. *Note: Full integration for additional brands like Fronius and Victron is planned for future updates.*
- **Dual Grid Power Sensors (REV UI5)**: Added support for split import/export grid sensors. Users with separate physical sensors for grid flow can now map them individually for more accurate power flow visualization.
- **Watt-Based Inverter Control (REV E3)**: Added support for inverters controlled via Watts instead of Amperes (e.g., Fronius). The system now automatically adapts its control logic based on the selected `control_unit`.

### Improvements & Fixes
- **Relaxed Validation (REV F16)**: Disabling components like batteries or solar in the System Profile now correctly hides and relaxes validation for their dependent sensors, preventing "required field" errors for inactive hardware.
- **Test Suite Alignment**: Synchronized the automated test suite with the updated `ActionDispatcher` API, ensuring improved stability and CI reliability.

---


## [v2.4.22-beta] - Config Stability & Settings Reorganization - 2026-01-15

### Core Features
- **Settings Reorganization (REV F14)**: Major overhaul of the Settings UI. Home Assistant entities are now logically grouped into "Input Sensors" and "Control Entities", making it easier to distinguish between what Darkstar reads and what it controls.
- **Executor Overrides (REV F17)**: Exposed new battery and PV override thresholds in the UI. Added automatic configuration migration to ensure existing installations receive these new parameters without manual editing.

### Critical Fixes
- **Config Corruption**: Resolved a long-standing issue where saving settings could strip comments from `config.yaml` or corrupt newline formatting. The system now exclusively uses `ruamel.yaml` for all config operations.
- **Executor Stability**: Fixed a backend crash that occurred when the execution engine encountered "None" or unconfigured entity IDs.

### UI/UX
- **Clutter Reduction**: Removed the legacy "Live System" diagnostic card from the Executor tab.
- **History Fix**: Fixed a bug where `water_power` sensors were not correctly captured in the historical energy charts.

---


## [v2.4.21-beta] - Runtime Socket Diagnostics - 2026-01-15

### Core Features
- **Runtime Debugging (REV F11)**: Added support for runtime Socket.IO configuration overrides via URL query parameters (`?socket_path=...` and `?socket_transports=...`). This allows debugging connectivity issues in complex Ingress environments without redeploying the application.

### Observability
- **Deep Packet Logging**: Instrumented the Socket.IO Manager to log low-level packet creation and reception, providing visibility into the handshake process during connection stalls.

---

## [v2.4.20-beta] - HA Ingress Stability & Quality - 2026-01-15

### Critical Fixes
- **HA Ingress Stability (REV F11)**: Implemented the Socket.IO Manager pattern for explicit namespace handling. This resolves persistent connection stalls in Home Assistant Add-on environments behind Ingress proxies, ensuring reliable live metrics flow.

### Internal
- **Debugging & Handover**: Added a structured Socket.IO debugging handover prompt to accelerate future troubleshooting of proxy-related issues.

---

## [v2.4.19-beta] - HA Ingress Refinement & Diagnostics - 2026-01-15

### Critical Fixes
- **HA Ingress (Round 3)**: Further refined the Socket.IO path handling for Home Assistant Ingress. Added a mandatory trailing slash to the path and improved URL resolution to ensure reliable connectivity across different HA network configurations.

### Observability
- **Expanded Socket Diagnostics**: Added comprehensive packet-level logging for the Socket.IO client to aid in troubleshooting persistent connection issues in complex proxy environments.

---

## [v2.4.18-beta] - UI Persistence & Scheduler Stability - 2026-01-15

### Critical Fixes
- **HA Ingress (Round 2)**: Fixed a regression in the WebSocket connection logic where the Socket.IO `path` was incorrectly calculated. Live metrics should now reliably flow through the Home Assistant Ingress proxy.
- **Scheduler Reliability (REV F12)**: Investigated and addressed a "Delayed Start" issue where the background scheduler would wait indefinitely for its first cycle. The scheduler now triggers an immediate optimization run on startup if no previous run is detected.

---

## [v2.4.17-beta] - HA Add-on Connectivity & Observability (REV F11) - 2026-01-15

### Critical Fixes (REV F11)
- **HA Ingress Connection**: Fixed a critical bug where the WebSocket client failed to connect in Home Assistant Add-on environments. The client now correctly handles the Ingress path, resolving the "blank dashboard" and "missing live metrics" issues.
- **Data Sanitization**: Implemented "Poison Pill" protection for sensor data. The system now safely handles `NaN` and `Inf` values from HA sensors (replacing them with 0.0) to prevent JSON serialization crashes that could take down the backend.

### Observability
- **New Diagnostic Endpoints**:
    - `/api/ha-socket`: Real-time diagnostics for the HA WebSocket connection (message counts, errors, emission stats).
    - `/api/scheduler-debug`: Status of the background scheduler.
    - `/api/executor-debug`: detailed state of the execution engine.
- **Enhanced Logging**: Added deep diagnostic (`DIAG`) logging option to trace WebSocket packet flow for easier debugging of connectivity issues.

---

## [v2.4.16-beta] - Observability & Reliability - 2026-01-15

### Core Improvements
- **Production Observability**: Added `/api/ha-socket` endpoint to expose runtime statistics (messages received, errors, emission counts) for "black box" diagnosis of the HA connection.
- **Robust Data Sanitization**: Implemented "poison pill" protection in the WebSocket client. `NaN` and `Inf` sensor values are now safe-guarded to 0.0, preventing JSON serialization crashes.
- **Transport Safety**: Added error trapping to the internal Event Bus to catch and log previously silent emission failures.

### Fixes
- **HA Client**: Added deep diagnostic (`DIAG`) logging to trace packet flow during connection issues.

---

## [v2.4.15-beta] - Regression Fix & Logging - 2026-01-15

**Fixes**
*   **Executor Engine**: Fixed a regression where the list of executed actions was not being correctly populated in the execution result.
*   **Logging Refinement**: Enhanced Home Assistant WebSocket logging to respect the `LOG_LEVEL` environment variable.
*   **Historical Data Integrity**: Fixed a critical bug where historical battery charge/discharge actions were inverted in the 48h chart view. The recorder now strictly respects standard inverter sign conventions (+ discharge, - charge).

---

## [v2.4.14-beta] - Stability & Performance Plan - 2026-01-15

**Improvements**
*   **Performance Plan (REV PERF1)**: Outlined a comprehensive roadmap to optimize the Kepler MILP solver, targeting a reduction in solving time from 22s to <5s.
*   **Developer Experience**: Migrated personal git ignore rules to `.git/info/exclude` to keep the repo clean and prevent accidental commits of local config overrides.
*   **Documentation Hygiene**: Archived completed tasks (REVs F9, H3, H4) to `CHANGELOG_PLAN.md`, keeping the active plan focused.

**Fixes**
*   **Live Dashboard**: Fixed a critical bug where the Home Assistant WebSocket connection would crash or fail silently on `None` entity IDs, restoring real-time updates.
*   **Diagnostic API**: Fixed the `/api/ha-socket` endpoint to correctly report connection status.
*   **Linting**: Resolved unused imports and formatting issues in the ML pipeline.

---

## [v2.4.13-beta] - Performance & UI Polish - 2026-01-14

### Performance
- **Planner Speedup:** Fixed a critical "524 Timeout" issue by optimizing database initialization and disabling legacy debug logging.
- **Database Tools:** Added `scripts/optimize_db.py` to safe-trim oversized databases (reducing 2GB+ files to <200MB) and `scripts/profile_planner.py` for performance analysis.
- **Fix:** `training_episodes` table is no longer populated by default, preventing indefinite database growth.

### Fixes
- **HA Add-on:** Fixed a critical build issue where the Add-on served stale frontend assets, causing duplicate settings fields and other UI glitches.
- **HA Add-on:** Fixed a blank dashboard issue by correctly configuring the frontend router to handle the Home Assistant Ingress subpath.
- **UI:** Moved "HA Add-on User" banner to correct section in Settings.
- **UI:** Added warning tooltip to HA URL setting for add-on users.

---

## [v2.4.12-beta] - Executor Resilience & History Fixes - 2026-01-14

**Core Features**
*   **Executor Health Monitoring (REV E2)**: Added new health endpoint and Dashboard integration. Dashboard now shows warnings if the Executor encounters errors or if critical entities are unconfigured.
*   **Settings Validation**: The Settings UI now actively validates configuration before saving, preventing invalid states (e.g., enabling Executor without a battery sensor).
*   **Historical Accuracy (REV H4)**: Fixed persistence for historical planned actions. The "48h" chart view now correctly displays past data (SoC targets, water heating) from the database instead of relying on ephemeral files.

**Bug Fixes**
*   **Entity Configuration**: Fixed a crash where empty string entity IDs (from YAML) caused 404 errors in the Executor.
*   **UI Polish**: Removed duplicate input field rendering in Settings.

---

## [v2.4.11-beta] - Historical Charts & Security Polish - 2026-01-14


**Core Fixes**
*   **Historical Charts Restored (REV H3)**: Fixed missing planned actions in the chart history view. The API now correctly queries the `slot_plans` table to overlay charge/discharge bars and SoC targets for past time slots.
*   **Security Patch (REV F9)**: Fixed a critical path traversal vulnerability in the SPA fallback handler to prevent unauthorized file access.

**UI & Cleanups**
*   **Help System Refinement**: Simplified the help system to rely on tooltips (Single Source of Truth) and removed redundant inline helper text.
*   **"Not Implemented" Badges**: Added visual warning badges for non-functional toggles (e.g., Export Enable) to set clear user expectations.
*   **Code Hygiene**: Removed typo "calculationsWfz" and cleaned up TODO markers from user-facing text.
*   **Startup & Config Hardening**: Upgraded `run.sh` to preserve comments in `config.yaml` using `ruamel.yaml` and improved logic for manual overrides.

---

## [v2.4.10-beta] - History Fix & Config Cleanup - 2026-01-13

**Critical Bug Fix**
*   **Planned Actions History**: Fixed a bug where the chart's planned actions history would briefly appear then disappear on production deployments (Docker/HA add-on). Root cause was a race condition between schedule and history data fetching, plus the WebSocket handler not refreshing history data.

**Config & UI Cleanup**
*   **Legacy Field Removal**: Removed deprecated `charging_strategy` section from config and its associated UI fields (strategy selector, price smoothing thresholds).
*   **Orphaned Help Text**: Cleaned up orphaned config help entries for removed fields.

---

## [v2.4.9-beta] - Settings Refinement & Diagnostic Hardening - 2026-01-12

**Diagnostic & Troubleshooting**
*   **Production Diagnostic Suite**: Implemented `[SETTINGS_DEBUG]` tracing in the Settings UI to resolve environment-specific validation bugs.
*   **Debug Mode Toggle**: Added a master "Debug Mode" toggle in Advanced Experimental Features for real-time console tracing.
*   **Module Load Validation**: Automatic verification of field type definitions at runtime to prevent configuration corruption.

**Settings & Configuration**
*   **Config Sync**: Fully synchronized the Settings UI with `config.default.yaml`, exposing previously hidden parameters for Water Heating start penalties and gap tolerances.
*   **Today's Stats Integration**: Added a new "Today's Energy Sensors" section for mapping daily battery, PV, and grid totals directly to the Dashboard.
*   **Subscription Fees**: New setting for `Monthly subscription fee (SEK)` to improve long-term financial modeling.
*   **Vacation Mode**: Added formal configuration for Water Heater Vacation Mode, including anti-legionella safety cycles.
*   **Notification Rename**: Standardized notification naming (`on_export_start`, `on_water_heat_start`) to better reflect system states.
*   **Scheduler Toggle**: Added a master "Enable Background Scheduler" toggle for manual control over optimization cycles.

**Legacy Cleanup**
*   **Arbitrage Audit**: Identified and marked legacy arbitrage fields for investigation and potential removal.
*   **Consistency Fixes**: Fixed several naming discrepancies between the frontend form and backend config keys.

---

## [v2.4.8-beta] - Production-Grade Settings & Power Inversion - 2026-01-12

**Core Improvements**
*   **Robust Entity Validation**: Implemented type-aware validation in the Settings UI. Entering Home Assistant entity IDs (like `sensor.battery_soc`) no longer triggers "Must be a number" errors.
*   **Expanded Entity Filtering**: Updated Home Assistant discovery to include `select.`, `input_select.`, and `number.` domains. You can now correctly select work mode and other control entities in the dropdowns.
*   **Inline Power Inversion**: Added a sleek **± (Invert)** button directly next to `Grid Power` and `Battery Power` entity selectors. This allows for instant correction of inverted sensor readings.

**System & UX**
*   **System Inversion Support**: Both the instantaneous status API and the real-time WebSocket dashboard now respect the grid/battery power inversion flags.
*   **Persistence Layer Hardening**: Automatic retrieval and saving of "companion keys" ensures inversion settings persist even after UI reloads.
*   **CI & Linting**: Zero-error release prep with full Ruff and ESLint verification across the entire stack.

---

## [v2.4.7-beta] - Onboarding Documentation & UI Improvements - 2026-01-12

**Documentation & Guidance**
*   **New User Manual**: Launched `docs/USER_MANUAL.md`—a 48-hour guide to mastering Darkstar's UI, risk strategies, and troubleshooting.
*   **Refactored Setup Guide**: Rewrote `docs/SETUP_GUIDE.md` to be UI-first, including a **Hardware Cheat Sheet** for Solis/Deye/Huawei inverters.
*   **Safety Hardening**: Added critical "Watts vs kW" validation warnings to prevent common configuration errors.

**UI & Experience**
*   **Terminology Alignment**: Renamed "**Market Strategy**" to "**Risk Appetite**" across the entire UI and documentation for better conceptual clarity.
*   **Quick Actions Upgrade**: Refactored the Executor panel with real-time status banners and SoC targeting for force-charging.
*   **Settings Expansion**: Exposed previously "hidden" `config.yaml` sectors in the UI, including Water Heater temperature floors, PV confidence margins, and battery cycle costs.

**System Hardening**
*   **HA Status**: Improved Home Assistant connection indicators in the Sidebar (Green/Red/Grey states).
*   **Shadow Mode**: Formalized "Shadow Mode" documentation to help new users test safely before going live.
