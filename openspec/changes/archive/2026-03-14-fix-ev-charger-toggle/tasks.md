## 1. Fix EV State Cleanup on Config Reload

- [x] 1.1 In `backend/ha_socket.py` `_get_monitored_entities()`, add an `else` branch to the `if system.get("has_ev_charger", False)` check that clears `self.ev_charger_configs = []` and removes `ev_chargers` from `self.latest_values`

## 2. Test

- [x] 2.1 Add a test that verifies `reload_monitored_entities()` clears EV state when `has_ev_charger` changes from true to false
- [x] 2.2 Add a test that verifies EV state is rebuilt when `has_ev_charger` changes from false to true
- [x] 2.3 Run existing tests to ensure no regressions
