#!/usr/bin/env python3
"""
Water Heating Solver Benchmark (Ultimate)
=========================================

Comparitive benchmark for water heating optimization.
Features:
- ASCII Gantt Chart Visualization
- Quality Metrics (Gap, Block, Sawtooth)
- Markdown Report Generation with Phase tagging

Usage:
    python scripts/benchmark_water.py --phase "PHASE 1" --reset
"""

import argparse
import contextlib
import logging
import math
import os
import platform
import random
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psutil
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.resolve()))

from planner.solver.kepler import KeplerSolver
from planner.solver.types import (
    KeplerConfig,
    KeplerInput,
    KeplerInputSlot,
    KeplerResult,
)


# Setup capturing of performance logs
class PerfCaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.last_metrics = {}

    def emit(self, record):
        msg = record.getMessage()
        match = re.search(r"Vars: (\d+), Const: (\d+)", msg)
        if match:
            self.last_metrics = {"vars": int(match.group(1)), "consts": int(match.group(2))}


perf_handler = PerfCaptureHandler()
perf_logger = logging.getLogger("darkstar.performance")
perf_logger.setLevel(logging.INFO)
perf_logger.addHandler(perf_handler)

logging.basicConfig(level=logging.ERROR, format="%(message)s")
logging.getLogger("planner").setLevel(logging.CRITICAL)


def draw_sparkline(data: list[float], height: int = 1) -> str:
    """Generates a sparkline string from a list of values."""
    if not data:
        return ""

    min_val = min(data)
    max_val = max(data)
    rng = max_val - min_val
    if rng == 0:
        return "█" * len(data)

    # Levels:  ▂▃▄▅▆▇█
    levels = [" ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

    res = ""
    for x in data:
        normalized = (x - min_val) / rng
        idx = int(normalized * (len(levels) - 1))
        res += levels[idx]

    return res


def get_sys_info() -> dict[str, str]:
    try:
        cpu_info = f"{platform.processor()} ({psutil.cpu_count(logical=False)} Cores)"
        if platform.system() == "Linux":
            with Path("/proc/cpuinfo").open() as f:
                for line in f:
                    if "model name" in line:
                        cpu_info = line.split(":")[1].strip()
                        break
        mem = psutil.virtual_memory()
        return {
            "CPU": cpu_info,
            "RAM": f"{mem.total / (1024**3):.1f} GB",
            "Arch": f"{platform.machine()} ({platform.system()})",
            "Python": sys.version.split()[0],
        }
    except Exception:
        return {"Error": "Hardware info not available"}


console = Console()


def generate_scenario(sc_config: dict[str, Any]) -> dict[str, Any]:
    name = sc_config["name"]
    slots = sc_config["slots"]
    water_enabled = sc_config.get("water", True)
    spacing_enabled = sc_config.get("spacing", False)
    profile = sc_config.get("profile", "default")

    # Water heating params
    comfort_level = sc_config.get("comfort_level", 3)
    min_kwh = sc_config.get("min_kwh", 8.0)
    max_gap = sc_config.get("max_gap", 12.0)
    min_spacing = sc_config.get("min_spacing", 4.0)
    heating_power = sc_config.get("heating_power", 3.0)

    start = datetime(2025, 1, 1, 0, 0)
    input_slots = []
    rng = random.Random(42)

    for i in range(slots):
        s = start + timedelta(minutes=15 * i)
        e = s + timedelta(minutes=15)
        hour = s.hour

        # Price Profiles
        if profile == "cheap_prices":
            import_price = 0.05 + rng.random() * 0.1  # Virtually free
        elif profile == "expensive_prices":
            import_price = 2.0 + rng.random() * 3.0  # Very expensive
        elif profile == "random_spikes":
            # Spiky: 10% chance of 5 SEK, else 0.5
            import_price = 5.0 if rng.random() < 0.1 else 0.5
        elif profile == "day_night_mirrored":
            # Day 1: Low Night (0-6), High Day (6-24)
            # Day 2: High Night (0-6), Low Day (6-24) (Mirrored)
            # Used to test spacing logic when price incentives flip
            day_idx = i // 96  # 0 or 1
            is_night = hour < 6
            import_price = (
                (0.5 if is_night else 2.0) if day_idx == 0 else (2.0 if is_night else 0.5)
            )
        else:  # Default
            # Sine wave price (0.5 to 1.5)
            import_price = 1.0 + 0.5 * math.sin(i / 10)

        export_price = import_price * 0.8
        load = 0.5 + (2.0 if 17 <= hour <= 21 else 0.0)

        input_slots.append(
            KeplerInputSlot(
                start_time=s,
                end_time=e,
                load_kwh=load / 4,
                pv_kwh=0.0,
                import_price_sek_kwh=import_price,
                export_price_sek_kwh=export_price,
            )
        )

    input_data = KeplerInput(slots=input_slots, initial_soc_kwh=5.0)

    # Simplified Comfort Penalty Map (matches adapter.py roughly)
    comfort_map = {1: 0.05, 2: 0.20, 3: 0.50, 4: 1.00, 5: 3.00}
    comfort_penalty = comfort_map.get(comfort_level, 0.50)

    config = KeplerConfig(
        capacity_kwh=10.0,
        max_charge_power_kw=5.0,
        max_discharge_power_kw=5.0,
        charge_efficiency=0.95,
        discharge_efficiency=0.95,
        min_soc_percent=10.0,
        max_soc_percent=90.0,
        wear_cost_sek_per_kwh=0.05,
        water_heating_power_kw=heating_power if water_enabled else 0.0,
        water_heating_min_kwh=min_kwh if water_enabled else 0.0,
        water_heating_max_gap_hours=max_gap if water_enabled else 0.0,
        water_comfort_penalty_sek=comfort_penalty if water_enabled else 0.0,
        water_min_spacing_hours=min_spacing if spacing_enabled else 0.0,
        water_switch_penalty_sek=0.5 if spacing_enabled else 0.0,
        enable_export=True,
    )

    return {"name": name + f" [{profile}]", "input": input_data, "config": config, "slots": slots}


def analyze_quality(result: KeplerResult, total_slots: int) -> dict[str, Any]:
    if not result.is_optimal:
        return {"max_gap": -1, "avg_block": -1, "sawtooth": -1, "ascii": "FAIL", "prices": []}

    # Extract binary schedule (1 = heating, 0 = off)
    # Note: result.slots[t].water_heat_kw > 0
    schedule = [1 if s.water_heat_kw > 0.1 else 0 for s in result.slots]

    # ASCII Gantt
    # Compress 192 slots -> 48 chars (1 char = 1 hour = 4 slots)
    ascii_str = ""
    for h in range(0, len(schedule), 4):
        chunk = schedule[h : h + 4]
        # If any slot in the hour is ON, mark as '█' (Full block) or '▄' (Partial)?
        # For readability, '█' if > 50% on, '░' if partial, '_' if off
        s_sum = sum(chunk)
        if s_sum == 4:
            ascii_str += "█"
        elif s_sum > 0:
            ascii_str += "▒"
        else:
            ascii_str += "_"

    # Metrics
    max_gap_slots = 0
    current_gap = 0

    blocks = []
    current_block = 0
    sawtooth_count = 0
    last_val = 0

    for val in schedule:
        if val == 0:
            current_gap += 1
            if current_block > 0:
                blocks.append(current_block)
                current_block = 0
        else:
            max_gap_slots = max(max_gap_slots, current_gap)
            current_gap = 0
            current_block += 1

        if val != last_val:
            sawtooth_count += 1
        last_val = val

    if current_block > 0:
        blocks.append(current_block)

    # Edge case: ended with gap
    max_gap_slots = max(max_gap_slots, current_gap)

    avg_block_slots = sum(blocks) / len(blocks) if blocks else 0

    return {
        "max_gap": max_gap_slots / 4.0,  # Hours
        "avg_block": avg_block_slots / 4.0,  # Hours
        "sawtooth": sawtooth_count / 2,  # Approx number of cycles
        "ascii": ascii_str,
        "prices": [s.import_price_sek_kwh for s in result.slots] if result.is_optimal else [],
    }


def save_markdown_report(
    results: list[dict[str, Any]], sys_info: dict[str, str], phase: str, reset: bool
):
    report_dir = Path(__file__).parent.parent / "docs" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "BENCHMARK_WATER_REPORT.md"

    mode = "w" if reset else "a"

    # Header if new/reset
    lines = []
    if reset or not report_path.exists():
        lines.append("# Water Heating Optimization Benchmark Report")
        lines.append("Comparison of water heating MILP complexity and solve times.\n")

    # Run Section
    lines.append(f"## Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ({phase})")
    if reset:
        lines.append("### System Context")
        lines.append(f"- **CPU**: {sys_info['CPU']}")
        lines.append(f"- **RAM**: {sys_info['RAM']}")
        lines.append(f"- **OS**: {sys_info['Arch']}")
        lines.append(f"- **Python**: {sys_info['Python']}\n")

    lines.append("### Results")
    # Compact Table
    lines.append("| Scenario | Time | Cost | Status | Max Gap | Avg Block | Sawtooth |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

    for r in results:
        t_str = f"{r['t']:.3f}s" if r["t"] > 0 else "FAIL"
        status = "✅" if r["t"] > 0 else "❌"
        q = r["quality"]

        lines.append(
            f"| {r['name']} | {t_str} | {r['cost']:.1f} | {status} | {q['max_gap']:.1f}h | {q['avg_block']:.1f}h | {q['sawtooth']:.0f} |"
        )

    # ASCII Visuals Section
    lines.append("\n### Visual Schedule (48h)")
    lines.append("`█` = Full Hour Heat, `▒` = Partial, `_` = Off")
    lines.append("`▂▃▅█` = Price Intensity (Low to High)")
    lines.append("```text")
    for r in results:
        q = r["quality"]
        # Compress prices to hourly average for sparkline (192 -> 48)
        hourly_prices = []
        if q["prices"]:
            for i in range(0, len(q["prices"]), 4):
                chunk = q["prices"][i : i + 4]
                hourly_prices.append(sum(chunk) / len(chunk))

        spark = draw_sparkline(hourly_prices)

        lines.append(f"{r['name']:<40} [{q['ascii']}]")
        lines.append(f"{' ':<40} [{spark}]")
        lines.append("")  # Empty line for spacing
    lines.append("```")
    lines.append("\n---\n")

    with report_path.open(mode) as f:
        f.write("\n".join(lines) + "\n")


def run_benchmark():
    parser = argparse.ArgumentParser(description="Water Heating Benchmark")
    parser.add_argument("--phase", type=str, default="UNKNOWN", help="Phase tag for report")
    parser.add_argument("--reset", action="store_true", help="Clear report file")
    args = parser.parse_args()

    sys_info = get_sys_info()

    console.print(
        Panel(
            f"[bold cyan]CPU:[/] {sys_info['CPU']}\n[bold cyan]Phase:[/] {args.phase}",
            title="[bold blue]ULTIMATE WATER BENCHMARK[/]",
            expand=False,
        )
    )

    yaml_path = Path(__file__).parent / "benchmarks_water.yaml"
    with yaml_path.open() as f:
        bench_data = yaml.safe_load(f)

    scenarios = [generate_scenario(s) for s in bench_data["benchmarks"]]

    py_solver = KeplerSolver()
    progress_results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=20),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[green]Simulating...", total=len(scenarios))

        for sc in scenarios:
            progress.update(task, description=f"[bold blue]Solving:[/] {sc['name']}")

            t_solve = -1.0
            metrics = {"vars": 0, "consts": 0}
            result = None

            try:
                start_time = time.time()
                with contextlib.redirect_stdout(None):
                    result = py_solver.solve(sc["input"], sc["config"])
                t_solve = time.time() - start_time
                metrics = perf_handler.last_metrics
            except Exception as e:
                console.print(f"[red]Error solving {sc['name']}: {e}[/]")

            # Quality Analysis
            quality = (
                analyze_quality(result, sc["slots"])
                if result
                else {"max_gap": -1, "avg_block": -1, "sawtooth": -1, "ascii": "FAIL"}
            )

            # Rich Table Output (Mini)
            t_color = "green" if t_solve < 1.0 else "red"
            console.print(
                f"  [cyan]{sc['name']:<35}[/] [{t_color}]{t_solve:.3f}s[/] | Gap: {quality['max_gap']:.1f}h | Block: {quality['avg_block']:.1f}h"
            )
            # Draw ASCII to console (Blue blocks)
            console.print(f"  [bold blue]{quality['ascii']}[/]")

            # Draw Sparkline below
            if quality.get("prices"):
                # Compress prices to hourly average for sparkline
                hourly_prices = []
                for i in range(0, len(quality["prices"]), 4):
                    chunk = quality["prices"][i : i + 4]
                    hourly_prices.append(sum(chunk) / len(chunk))
                spark = draw_sparkline(hourly_prices)
                console.print(f"  [dim]{spark}[/]\n")
            else:
                console.print("\n")

            progress_results.append(
                {
                    "name": sc["name"],
                    "t": t_solve,
                    "cost": result.total_cost_sek if result else 0.0,
                    "vars": metrics.get("vars", 0),
                    "consts": metrics.get("consts", 0),
                    "quality": quality,
                }
            )
            progress.advance(task)

    save_markdown_report(progress_results, sys_info, args.phase, args.reset)
    console.print("[green]Report saved to docs/reports/BENCHMARK_WATER_REPORT.md[/]")


def get_process_memory() -> float:
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


if __name__ == "__main__":
    run_benchmark()
