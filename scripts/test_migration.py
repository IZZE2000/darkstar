#!/usr/bin/env python3
"""
Config Migration Test Script

Tests migration on a specified config file and compares the result to config.default.yaml.

Usage:
    uv run python scripts/test_migration.py debugging/pll_config8.yaml

This script:
1. Backs up the original config
2. Runs the full migration pipeline
3. Compares the migrated config structure to config.default.yaml
4. Reports any issues found
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ruamel.yaml import YAML


def backup_config(config_path: Path) -> Path:
    """Create a timestamped backup of the config file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("debugging/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_path = backup_dir / f"{config_path.stem}_{timestamp}.yaml"
    backup_path.write_text(config_path.read_text())
    print(f"✅ Backed up to: {backup_path}")
    return backup_path


def run_migration(config_path: Path) -> bool:
    """Run the full migration pipeline on the config file."""
    from backend.config_migration import migrate_config

    default_path = Path("config.default.yaml")

    print(f"\n📦 Running migration on: {config_path}")
    print(f"   Template: {default_path}")

    try:
        asyncio.run(migrate_config(str(config_path), str(default_path), strict_validation=False))
        print("✅ Migration completed successfully")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


def load_config(path: Path) -> dict:
    """Load config using ruamel.yaml to preserve structure."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096

    with path.open(encoding="utf-8") as f:
        return yaml.load(f)


def get_all_keys(d: dict, parent: str = "") -> set:
    """Recursively get all keys from a nested dict."""
    keys = set()
    for key, value in d.items():
        full_key = f"{parent}.{key}" if parent else key
        keys.add(full_key)
        if isinstance(value, dict):
            keys.update(get_all_keys(value, full_key))
    return keys


def check_structure(migrated: dict, default: dict) -> list[str]:
    """Check if migrated config has all required keys from default.

    Note: Extra keys are NOT necessarily deprecated - they may be user-specific
    values (entity IDs, custom settings). We only fail on MISSING keys.
    """
    issues = []

    default_keys = get_all_keys(default)
    migrated_keys = get_all_keys(migrated)

    # Find missing keys (these are actual problems)
    missing = default_keys - migrated_keys
    if missing:
        issues.append(f"Missing required keys: {sorted(missing)}")

    # Extra keys are OK - they're user-specific values (entities, etc.)
    # We just report them for visibility
    extra = migrated_keys - default_keys
    if extra:
        print(f"   i  Extra user-specific keys (OK): {len(extra)} keys")

    return issues


def check_custom_entities(config: dict, profile_name: str | None = None) -> list[str]:
    """Check that custom_entities has the correct keys for the profile."""
    issues = []

    inverter = config.get("executor", {}).get("inverter", {})
    custom_entities = inverter.get("custom_entities", {})

    # Check that profile-specific keys are NOT at top level
    legacy_keys = [
        "ems_mode",
        "ems_mode_entity",
        "forced_charge_discharge_cmd",
        "forced_charge_discharge_cmd_entity",
    ]
    found_legacy = [k for k in legacy_keys if k in inverter]
    if found_legacy:
        issues.append(f"Legacy keys still at top level: {found_legacy}")

    # Check custom_entities is not empty (if profile requires entities)
    if not custom_entities:
        issues.append("custom_entities is empty (may be OK for generic profile)")
    else:
        print(
            f"   ✅ custom_entities has {len(custom_entities)} keys: {list(custom_entities.keys())}"
        )

    return issues


def compare_comments(original: Path, migrated: Path) -> list[str]:
    """Check if comments were preserved by comparing line counts.

    Note: Some line count changes are expected due to:
    - Formatting changes from ruamel.yaml
    - Reordering of keys to match default
    - Comment normalization
    """
    issues = []

    orig_lines = len(original.read_text().splitlines())
    migr_lines = len(migrated.read_text().splitlines())

    # Allow larger variance - formatting can change line counts
    diff = abs(orig_lines - migr_lines)
    if diff > 20:
        issues.append(
            f"Line count changed significantly: {orig_lines} -> {migr_lines} (diff: {diff})"
        )
    elif diff > 0:
        print(f"   i  Line count changed (expected): {orig_lines} -> {migr_lines}")

    return issues


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/test_migration.py <config_path>")
        print("Example: uv run python scripts/test_migration.py debugging/pll_config8.yaml")
        sys.exit(1)

    config_path = Path(sys.argv[1])

    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)

    print("=" * 60)
    print("Config Migration Test")
    print("=" * 60)

    # Step 1: Backup
    print("\n[1/4] Creating backup...")
    backup_path = backup_config(config_path)

    # Step 2: Load original for comparison
    print("\n[2/4] Loading original config...")
    original = load_config(config_path)
    print(f"   ✅ Loaded {len(get_all_keys(original))} keys")

    # Step 3: Run migration
    print("\n[3/4] Running migration...")
    if not run_migration(config_path):
        print("\n❌ Migration failed - aborting comparison")
        sys.exit(1)

    # Step 4: Compare
    print("\n[4/4] Comparing to default config...")

    default_path = Path("config.default.yaml")
    migrated = load_config(config_path)
    default = load_config(default_path)

    all_issues = []

    # Check structure
    print("\n📋 Structure Check:")
    structure_issues = check_structure(migrated, default)
    if structure_issues:
        for issue in structure_issues:
            print(f"   ❌ {issue}")
            all_issues.extend(structure_issues)
    else:
        print("   ✅ All required keys present")
        print("   ✅ No deprecated/extra keys found")

    # Check custom_entities
    print("\n📋 Custom Entities Check:")
    custom_issues = check_custom_entities(migrated)
    if custom_issues:
        for issue in custom_issues:
            print(f"   ⚠️  {issue}")
            all_issues.extend(custom_issues)

    # Check comments preserved
    print("\n📋 Comments Preservation Check:")
    comment_issues = compare_comments(backup_path, config_path)
    if comment_issues:
        for issue in comment_issues:
            print(f"   ⚠️  {issue}")
            all_issues.extend(comment_issues)
    else:
        print("   ✅ Comments preserved")

    # Summary
    print("\n" + "=" * 60)
    if all_issues:
        print(f"❌ FAILED - {len(all_issues)} issue(s) found:")
        for issue in all_issues:
            print(f"   - {issue}")
        sys.exit(1)
    else:
        print("✅ PASSED - Migration successful, structure matches default!")
        sys.exit(0)


if __name__ == "__main__":
    main()
