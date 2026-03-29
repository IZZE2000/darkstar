"""Regression guard test to catch unsafe timezone-aware calls in production code.

This test ensures that no bare pd.date_range() or .tz_localize() calls with
non-UTC timezones are introduced into the codebase.
"""

import re
from pathlib import Path

import pytest


def find_unsafe_tz_calls():
    """Scan production code for unsafe timezone-aware calls.

    Returns:
        list: List of tuples (file_path, line_number, line_content) for each violation.
    """
    violations = []

    # Directories to scan
    scan_dirs = ["ml", "planner", "backend", "executor"]

    # Files to exclude
    exclude_files = {"time_utils.py"}  # The utility file itself is allowed to use these calls

    # Get project root
    project_root = Path(__file__).parent.parent.parent

    for dir_name in scan_dirs:
        dir_path = project_root / dir_name
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            # Skip test files and excluded files
            if "test_" in py_file.name or py_file.name in exclude_files:
                continue

            try:
                content = py_file.read_text()
                lines = content.split("\n")

                for line_num, line in enumerate(lines, 1):
                    # Check for pd.date_range calls with tz= parameter that's not UTC
                    if "pd.date_range(" in line and "tz=" in line:
                        # Extract the tz value
                        match = re.search(r"tz=([^,)]+)", line)
                        if match:
                            tz_value = match.group(1).strip()
                            # Allow 'UTC' and '"UTC"' but flag others
                            if tz_value not in ('"UTC"', "'UTC'", "UTC"):
                                violations.append(
                                    (
                                        str(py_file.relative_to(project_root)),
                                        line_num,
                                        line.strip(),
                                        f"pd.date_range with tz={tz_value}",
                                    )
                                )

                    # Check for .tz_localize() calls with non-UTC argument
                    if ".tz_localize(" in line:
                        # Extract what's being passed to tz_localize
                        match = re.search(r"\.tz_localize\(([^)]+)\)", line)
                        if match:
                            tz_arg = match.group(1).strip()
                            # Allow 'UTC' and '"UTC"' but flag others
                            if tz_arg not in ('"UTC"', "'UTC'", "UTC"):
                                violations.append(
                                    (
                                        str(py_file.relative_to(project_root)),
                                        line_num,
                                        line.strip(),
                                        f".tz_localize({tz_arg})",
                                    )
                                )
            except Exception as e:
                violations.append(
                    (
                        str(py_file.relative_to(project_root)),
                        0,
                        f"Error reading file: {e}",
                        "File read error",
                    )
                )

    return violations


def test_no_bare_unsafe_tz_calls():
    """Ensure no bare unsafe timezone-aware calls exist in production code.

    This test scans all Python files in ml/, planner/, backend/, and executor/
    for pd.date_range() calls with non-UTC tz= parameter and .tz_localize()
    calls with non-UTC arguments. Such calls should use the DST-safe utilities
    from utils.time_utils instead.
    """
    violations = find_unsafe_tz_calls()

    if violations:
        # Format a nice error message
        error_lines = ["\nFound unsafe timezone-aware calls in production code:", ""]

        for file_path, line_num, line_content, violation_type in violations:
            error_lines.append(f"  {file_path}:{line_num}")
            error_lines.append(f"    {violation_type}")
            error_lines.append(f"    Line: {line_content[:80]}...")
            error_lines.append("")

        error_lines.append("These calls should use DST-safe utilities from utils.time_utils:")
        error_lines.append(
            "  - Use dst_safe_date_range() instead of pd.date_range(..., tz=local_tz)"
        )
        error_lines.append("  - Use dst_safe_localize() instead of .tz_localize(local_tz)")

        pytest.fail("\n".join(error_lines))
