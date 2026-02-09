# 📘 Darkstar User Manual

Welcome to **Darkstar**, your AI-powered energy manager.

Unlike traditional "if-this-then-that" automations, Darkstar doesn't follow rigid rules. Instead, it **plans**. It looks 48 hours into the future, considers weather, prices, and your battery's health, and calculates the mathematically optimal path to save you money.

---

## 🚀 1. The Dashboard Explained

The Dashboard is your "Mission Control". Here's how to read it.

### The Horizon Chart
This chart visualizes the 48-hour plan.
*   **Gold Area (☀️)**: Solar Production Forecast.
*   **Cyan Bars (🏠)**: Your Home's Forecasted Load.
*   **Grey Line (📉)**: Electricity Price (Spot + Tax).
*   **Cyan Line (🔋)**: Battery State of Charge (SoC).
    *   **Solid Line**: The *Plan* (what should happen).
    *   **Dotted Line**: The *Actual* (what is happening).
*   **Vertical "NOW" Line**: Everything to the **left** is history. Everything to the **right** is the future plan.

### Visual Color Code
*   **🟢 Green**: **Export**. You are selling energy to the grid.
*   **🔴 Orange**: **Grid Charge**. You are buying energy to charge the battery (usually because it's cheap!).
*   **🌸 Pink**: **Discharge**. You are using battery power to avoid expensive grid prices.
*   **🔵 Blue**: **Water Heating**. Darkstar is heating your hot water tank.

### status Dot (Sidebar)
Look at the small dot at the bottom of the Sidebar (left menu).
*   **🟢 Green**: **Online**. Connected to Home Assistant.
*   **🔴 Red**: **Offline**. Connection lost. Check your HA configuration.
*   **⚫ Grey**: **Connecting**. Waiting for analyzing to complete.

---

## 🧠 2. Deep Dive: Strategy & Risk

Darkstar isn't magic; it's math. You control the math with **Risk Appetite**.

### What is "Risk Appetite"?
Weather forecasts are never 100% perfect. "Risk Appetite" tells Darkstar how much to trust the forecast.

| Level | Name             | Philosophy                     | Safety Buffer                                                                            |
| :---- | :--------------- | :----------------------------- | :--------------------------------------------------------------------------------------- |
| **1** | **Safety**       | *"I never want to run empty."* | **+35%** added to minimum battery target.                                                |
| **2** | **Conservative** | *"Better safe than sorry."*    | **+20%** added buffer.                                                                   |
| **3** | **Neutral**      | *"Trust the math."*            | **+10%** standard buffer.                                                                |
| **4** | **Aggressive**   | *"I want maximum savings."*    | **+3%** minimal buffer.                                                                  |
| **5** | **Gambler**      | *"Live dangerously."*          | **-7%**. Intentionally targets *below* minimum, betting on a replan/extra PV/Lower load. |

**Example**:
If your `Min SoC` is 10%, and you choose **Level 1 (Safety)**, Darkstar will aim to keep your battery at **45%** (10% + 35%) before the sun comes up, just in case the forecast is wrong.
If you choose **Level 5 (Gambler)**, it might let you drop to **3%**, betting that the sun *will* shine.

### The "S-Index" (Strategic Index)
You'll see an "S-Index" score on the dashboard. This measures **volatility**.
*   **1.0**: Normal day.
*   **> 1.0**: High uncertainty (variable clouds, price spikes). Darkstar will be more conservative.
*   **< 1.0**: Stable, predictable day.

---

## 🎮 3. Operations & Controls

### Quick Actions (Executor Tab)
*   **Dynamic Monitoring**: All logs and charts in the Executor tab automatically respect your hardware's native units (**Amperes** or **Watts**).
*   **Force Charge**: Immediately charges the battery to 100% (or your set limit) at max power. Useful if a storm is coming.
*   **Pause Plan**: Stops all automated control. Your battery will sit idle.
*   **Water Boost**: Triggers the water heater immediately, ignoring price. Useful if you need a hot bath *now*.

### Water Heating Comfort
In **Dashboard -> Water Comfort**, you can set the Water Heater "Comfort Level" (1-5).

The comfort level controls **two key parameters**:
1. **Window Size** - How long each heating session can be
2. **Penalties** - How strictly the system enforces these windows

**Comfort Levels:**
- **Level 1 (Economy)**: Large windows (4h+) = bulk heating in cheapest periods. May have lukewarm water between sessions.
- **Level 2 (Balanced)**: Moderate windows (2.7h) = good mix of savings and comfort.
- **Level 3 (Neutral)**: Baseline windows (2.1h) = slight preference for spacing.
- **Level 4 (Priority)**: Small windows (1.3h) = more frequent heating throughout the day.
- **Level 5 (Maximum)**: Tiny windows (0.7h) = very frequent heating = most stable temperature.

**Bulk Mode Override:**
Set `enable_top_ups: false` in config to force single-block bulk heating regardless of comfort level. This preserves reliability penalties but allows one large heating session per day.

### Shadow Mode
In **Settings -> Advanced**, you can enable **Shadow Mode**.
*   **ON**: Darkstar calculates the plan but **DOES NOT** send commands to your inverter. It just watches. Great for testing.
*   **OFF**: Darkstar has full control.

---

## 🔋 4. Smart EV Charging Strategy

Darkstar treats your Electric Vehicle as a "Deferrable Load." This means it understands the car needs a certain amount of energy but can wait for the most optimal time to get it.

### How it Works
1.  **Plug-in Detection**: When you plug in your car, Darkstar detects the change and immediately triggers a **Re-plan**. It calculates how much energy you need to reach your `Min Target SoC`.
2.  **Source Isolation**: Darkstar ensures your house battery is **protected**. It will only charge the car using Solar Surplus or cheap Grid power. It will *not* discharge your house battery into the EV.
3.  **The Priority System**: Darkstar uses dynamic pricing "penalties" based on your car's SoC:
    *   🔴 **Emergency (<20%)**: Charges immediately at any price.
    *   🟡 **High Priority (20-40%)**: Prioritizes charging in the next available cheap windows.
    *   🟢 **Normal (>40%)**: Only charges when prices are at their absolute lowest.

### Dashboard Indicators
*   **Gold Bars**: EV charging power is shown on the Dashboard and Horizon chart.
*   **EV SoC**: Your car's current charge level is displayed in the Charging Status card.

---

## ⚠️ 5. Troubleshooting

### "Why isn't it charging?"
1.  **Check Risk Appetite**: If you are on "Level 5 (Gambler)", it might be waiting for an even cheaper price later.
2.  **Check Prices**: Is the price actually low? Darkstar factors in "Cycle Cost". If (Price difference < Cycle Cost), it won't cycle the battery.
3.  **Check Constraints**: Is the battery already full? Is the inverter maxed out?

### "My battery is draining into the grid!"
*   Check your **Home Assistant export settings**. Darkstar usually sets "Self-Use" or "Zero Export", but if your inverter is in "Selling First" mode manually, it will dump energy.

### "The plan keeps changing!"
*   This is normal. Darkstar replans every time new data comes in (weather updates, new prices). It's constantly course-correcting, like a GPS avoiding traffic.

---

## 📚 6. FAQ

### "Executor not setting entity" - How to check history logs

Some inverter profiles (like Sungrow) require setting **multiple entities** to achieve a specific mode. For example, "Charge from Grid" might require:
- Setting the work mode to "Forced Charge"
- Setting an EMS mode switch to "Forced Mode"
- Setting a forced charge/discharge command to "Charge"
- Setting an export power limit to 0

**How to verify what the executor is doing:**

1. **Go to the Executor tab** in the Darkstar dashboard
2. **Find the execution record** for the time when the mode should have changed
3. **Expand the record** (click on it) to see detailed action results
4. **Look for composite mode actions** - these are shown as sub-items of the main mode change
5. **Check each entity change**:
   - ✅ **Green check**: Entity was set successfully
   - ❌ **Red X**: Entity set failed (shows error message)

**Common issues:**
- **Wrong entity ID**: The entity doesn't exist in Home Assistant
- **Permission denied**: Darkstar's Home Assistant token doesn't have write access
- **Invalid value**: The value you're trying to set isn't accepted by the inverter
- **Read-only entity**: Some integrations expose entities as read-only

**What to do:**
1. Check the Executor history for specific error messages
2. Verify entity IDs match your Home Assistant setup
3. Check inverter profile configuration in Settings
4. Test the entity manually in Home Assistant Developer Tools to confirm it's writable
