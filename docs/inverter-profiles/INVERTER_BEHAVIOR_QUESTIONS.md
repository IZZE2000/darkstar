# Inverter Behavior Questionnaire

**For Beta Users: Help us create your inverter profile**

**Your Name:**
**Inverter Brand/Model:**

---

## 1. Work Mode Control

Does your inverter use:
- [ ] Single select entity for all modes (e.g., "Auto", "Charge from grid", "Export")
- [ ] Multiple switches/entities for different behaviors
- [ ] Other control method (describe):

---

## 2. Charge from Grid

What needs to be set to charge battery from grid?

**Example**:
- Set select to "Charge from grid" + flip switch "Grid charging" to ON + set number "Charge power" (Watts)

**Your setup**:
- Entity types needed (select/switch/number):
- Units (W, kW, A):
- Single entity or multiple entities:

---

## 3. Export to Grid

What needs to be set to export/discharge battery to grid?

**Your setup**:
- Entity types needed:
- Units (W, kW, A):
- Single entity or multiple entities:

---

## 4. Self-Consume / Zero Export

What needs to be set for normal operation (PV charges battery, no grid import/export)?

**Your setup**:
- Entity types needed:
- Is this a single work mode value, or multiple settings:

---

## 5. Grid Consumption

What needs to be set to consume from grid (load powered by grid, not battery)?

**Your setup**:
- Entity types needed:
- Is this different from "charge from grid":

---

## 6. Charge Power Control

How is charge power/current controlled?
- [ ] Watts (number entity)
- [ ] Kilowatts (number entity)
- [ ] Amperes (number entity)
- [ ] Not controllable (inverter decides)
- [ ] Controlled via work mode only

---

## 7. Discharge Power Control

How is discharge power/current controlled?
- [ ] Watts (number entity)
- [ ] Kilowatts (number entity)
- [ ] Amperes (number entity)
- [ ] Not controllable (inverter decides)
- [ ] Controlled via work mode only

---

## 8. SoC Target

Can you set a battery SoC target?
- [ ] Yes (number entity built into inverter)
- [ ] No (must use external helper like input_number)

---

## 9. Combined Actions

Do any actions require setting multiple entities at once?

**Example**: "To charge from grid, must first set mode to 'Manual', then set charge power, then set mode to 'Charge'"

**Your answer**:

---

## 10. Quirks

Any special behaviors or requirements?

**Examples**:
- "Must wait 5 seconds between mode changes"
- "Grid charging controlled by work mode only, no separate switch"
- "Separate charge/discharge power entities"

**Your quirks**:
