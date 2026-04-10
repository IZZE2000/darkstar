"""Diagnostic script for ML system health checks."""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path.cwd()))

from backend.learning import get_learning_engine
from ml.forward import determine_graduation_level  # type: ignore[reportPrivateUsage]


def diagnose():
    try:
        engine = get_learning_engine()
        print(f"DB Path: {engine.db_path}")

        level, label, days = determine_graduation_level(engine)
        print(f"Graduation Level: {level} ({label})")
        print(f"Days of data: {days:.1f}")

        if level < 2:
            print("(!) Not enough data for ML training (Need Level 2).")
            return

        print("\nSystem is ready for ML inference.")
        print("Models will be loaded from: data/models/")

    except Exception as e:
        print(f"Error during diagnosis: {e}")


if __name__ == "__main__":
    diagnose()
