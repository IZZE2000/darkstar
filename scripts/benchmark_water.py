#!/usr/bin/env python3
"""
Water Heating Solver Benchmark
============================

Specific benchmark for water heating optimization performance.
Measures solve times, variable counts, and constraint counts.

Usage:
    python scripts/benchmark_water.py
"""

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
from rich.table import Table

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.resolve()))

from planner.solver.kepler import KeplerSolver
from planner.solver.types import (
    KeplerConfig,
    KeplerInput,
    KeplerInputSlot,
)


# Setup capturing of performance logs
class PerfCaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.last_metrics = {}

    def emit(self, record):
        # Look for: "Kepler Solved: 192 slots in 0.456s (Vars: 746, Const: 600) | Cost: 12.34 SEK"
        msg = record.getMessage()
        match = re.search(r"Vars: (\d+), Const: (\d+)", msg)
        if match:
            self.last_metrics = {"vars": int(match.group(1)), "consts": int(match.group(2))}


perf_handler = PerfCaptureHandler()
perf_logger = logging.getLogger("darkstar.performance")
perf_logger.setLevel(logging.INFO)
perf_logger.addHandler(perf_handler)

# Silence other logs
logging.basicConfig(level=logging.ERROR, format="%(message)s")
logging.getLogger("planner").setLevel(logging.CRITICAL)


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

        # Volatile prices for interesting optimization
        import_price = 1.0 + 0.5 * (math.sin(i / 10) + rng.random())
        export_price = import_price * 0.8

        if profile == "heavy_home":
            load = 2.0 + rng.random() * 5.0
        else:
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

    # Map comfort level to penalty (simplified for now)
    comfort_penalty = 2.0 * comfort_level

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
        water_block_start_penalty_sek=0.5 if spacing_enabled else 0.0,
        enable_export=True,
    )

    return {
        "name": name,
        "input": input_data,
        "config": config,
    }


def get_process_memory() -> float:
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def save_markdown_report(results: list[dict[str, Any]], sys_info: dict[str, str]):
    report_dir = Path(__file__).parent.parent / "docs" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "BENCHMARK_WATER_REPORT.md"

    exists = report_path.exists()

    lines = []
    if not exists:
        lines.append("# Water Heating Optimization Benchmark Report")
        lines.append("Comparison of water heating MILP complexity and solve times.\n")

    lines.append(f"## Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("### System Context")
    lines.append(f"- **CPU**: {sys_info['CPU']}")
    lines.append(f"- **RAM**: {sys_info['RAM']}")
    lines.append(f"- **OS**: {sys_info['Arch']}")
    lines.append(f"- **Python**: {sys_info['Python']}\n")

    lines.append("### Results")
    lines.append("| Scenario | Solve Time | Vars | Consts | Memory (MB) | Status |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")

    for r in results:
        t_str = f"{r['t']:.4f}s" if r["t"] > 0 else "FAIL"
        status = "✅" if r["t"] > 0 else "❌"
        lines.append(
            f"| {r['name']} | {t_str} | {r['vars']} | {r['consts']} | {r['mem']:.1f} | {status} |"
        )

    lines.append("\n---\n")

    mode = "a" if exists else "w"
    with report_path.open(mode) as f:
        f.write("\n".join(lines) + "\n")


def run_benchmark():
    sys_info = get_sys_info()

    console.print(
        Panel(
            f"[bold cyan]CPU:[/] {sys_info['CPU']}\n[bold cyan]RAM:[/] {sys_info['RAM']}\n[bold cyan]Python:[/] {sys_info['Python']}",
            title="[bold blue]WATER HEATING BENCHMARK[/]",
            expand=False,
        )
    )

    yaml_path = Path(__file__).parent / "benchmarks_water.yaml"
    with yaml_path.open() as f:
        bench_data = yaml.safe_load(f)

    scenarios = [generate_scenario(s) for s in bench_data["benchmarks"]]

    table = Table(box=None, header_style="bold blue", show_header=True)
    table.add_column("Scenario", style="cyan", width=30)
    table.add_column("Solve Time", justify="right")
    table.add_column("Vars", justify="right", style="dim")
    table.add_column("Consts", justify="right", style="dim")
    table.add_column("Memory (MB)", justify="right", style="dim")
    table.add_column("Status", justify="center")

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
        task = progress.add_task("[green]Solvin' water...", total=len(scenarios))

        for sc in scenarios:
            progress.update(task, description=f"[bold blue]Solving:[/] {sc['name']}")

            t_solve, mem_solve = -1.0, 0.0
            metrics = {"vars": 0, "consts": 0}

            try:
                start_mem = get_process_memory()
                start_time = time.time()

                with contextlib.redirect_stdout(None):
                    py_solver.solve(sc["input"], sc["config"])

                t_solve = time.time() - start_time
                mem_solve = max(0.0, get_process_memory() - start_mem)
                metrics = perf_handler.last_metrics
            except Exception as e:
                console.print(f"[red]Error solving {sc['name']}: {e}[/]")

            status_icon = "✅" if t_solve > 0 else "❌"

            # Formatting time with colors
            if t_solve < 0:
                t_str = "[red]FAIL[/]"
            elif t_solve < 0.2:
                t_str = f"[green]{t_solve:.4f}s[/]"
            elif t_solve < 1.0:
                t_str = f"[yellow]{t_solve:.4f}s[/]"
            else:
                t_str = f"[red]{t_solve:.4f}s[/]"

            table.add_row(
                sc["name"],
                t_str,
                str(metrics.get("vars", 0)),
                str(metrics.get("consts", 0)),
                f"{mem_solve:.1f}",
                status_icon,
            )

            progress_results.append(
                {
                    "name": sc["name"],
                    "t": t_solve,
                    "vars": metrics.get("vars", 0),
                    "consts": metrics.get("consts", 0),
                    "mem": mem_solve,
                }
            )

            progress.advance(task)

    console.print(table)
    save_markdown_report(progress_results, sys_info)
    console.print(
        Panel(
            "[bold green]Benchmark Complete.[/]\n[grey]Results added to docs/reports/BENCHMARK_WATER_REPORT.md[/]",
            border_style="green",
        )
    )


if __name__ == "__main__":
    run_benchmark()
