## 1. Implementation

- [x] 1.1 Add useEffect in Settings component to listen for `config-changed` events
- [x] 1.2 In event handler, re-fetch config and update `systemFlags` state
- [x] 1.3 Add cleanup function to remove event listener on unmount

## 2. Verification

- [x] 2.1 Test toggling has_solar - Solar tab should appear immediately after save
- [x] 2.2 Test toggling has_battery - Battery tab should appear immediately after save
- [x] 2.3 Test toggling off - tabs should disappear immediately after save
- [x] 2.4 Run lint checks
