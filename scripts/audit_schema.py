#!/usr/bin/env python3
"""
Schema Drift Audit - REV // F40 Phase 4
Compares SQLAlchemy models against latest Alembic migration schema.
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


from backend.learning.models import Base


def get_model_tables():
    """Extract all table definitions from SQLAlchemy models."""
    tables = {}
    for mapper in Base.registry.mappers:
        table = mapper.class_.__table__
        tables[table.name] = {
            "columns": {col.name: str(col.type) for col in table.columns},
            "model": mapper.class_.__name__,
        }
    return tables


def get_db_tables(db_path: str):
    """Extract all table definitions from SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'alembic%'")
    table_names = [row[0] for row in cursor.fetchall()]

    tables = {}
    for table_name in table_names:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = {}
        for row in cursor.fetchall():
            col_name = row[1]
            col_type = row[2]
            columns[col_name] = col_type
        tables[table_name] = {"columns": columns}

    conn.close()
    return tables


def normalize_type(sqlalchemy_type: str) -> str:
    """Normalize SQLAlchemy type to SQLite type for comparison."""
    type_map = {
        "VARCHAR": "TEXT",
        "TEXT": "TEXT",
        "INTEGER": "INTEGER",
        "FLOAT": "REAL",
        "BOOLEAN": "INTEGER",
        "DATETIME": "DATETIME",
    }
    # Extract base type (e.g., "VARCHAR(50)" -> "VARCHAR")
    base_type = sqlalchemy_type.split("(")[0].upper()
    return type_map.get(base_type, base_type)


def audit_schema(db_path: str):
    """Compare models against database schema."""
    print("=" * 80)
    print("SCHEMA DRIFT AUDIT - REV // F40 Phase 4")
    print("=" * 80)
    print()

    model_tables = get_model_tables()
    db_tables = get_db_tables(db_path)

    print(f"📊 Models: {len(model_tables)} tables")
    print(f"💾 Database: {len(db_tables)} tables")
    print()

    drift_found = False

    # Check for missing tables
    missing_tables = set(model_tables.keys()) - set(db_tables.keys())
    if missing_tables:
        drift_found = True
        print("❌ MISSING TABLES IN DATABASE:")
        for table in sorted(missing_tables):
            print(f"   - {table} (model: {model_tables[table]['model']})")
        print()

    # Check for extra tables
    extra_tables = set(db_tables.keys()) - set(model_tables.keys())
    if extra_tables:
        print("⚠️  EXTRA TABLES IN DATABASE (not in models):")
        for table in sorted(extra_tables):
            print(f"   - {table}")
        print()

    # Check columns for each table
    for table_name in sorted(set(model_tables.keys()) & set(db_tables.keys())):
        model_cols = model_tables[table_name]["columns"]
        db_cols = db_tables[table_name]["columns"]

        missing_cols = set(model_cols.keys()) - set(db_cols.keys())
        extra_cols = set(db_cols.keys()) - set(model_cols.keys())

        if missing_cols or extra_cols:
            drift_found = True
            print(f"❌ DRIFT IN TABLE: {table_name}")

            if missing_cols:
                print("   Missing columns in DB:")
                for col in sorted(missing_cols):
                    print(f"      - {col}: {model_cols[col]}")

            if extra_cols:
                print("   Extra columns in DB:")
                for col in sorted(extra_cols):
                    print(f"      - {col}: {db_cols[col]}")

            print()

    if not drift_found:
        print("✅ NO SCHEMA DRIFT DETECTED")
        print("   All models match database schema.")
        print()

    print("=" * 80)
    print(f"AUDIT COMPLETE - Drift Found: {drift_found}")
    print("=" * 80)

    return 1 if drift_found else 0


if __name__ == "__main__":
    db_path = "data/planner_learning.db"
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)

    sys.exit(audit_schema(db_path))
