#!/usr/bin/env python3
"""
Manual training script for Aurora Error Correction models.
Allows forcing training even if graduation level is not met.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup simple logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("train_corrector")


def train_manual(force: bool = False, output_dir: str = "ml/models"):
    try:
        from ml.corrector import (
            _determine_graduation_level,
            _get_engine,
            _load_training_frame,
            _train_error_models,
        )
    except ImportError as e:
        logger.error(
            f"Failed to import ml.corrector. Run this from project root or check pythonpath: {e}"
        )
        sys.exit(1)

    print("--- Aurora Error Correction Trainer ---")

    engine = _get_engine()
    level = _determine_graduation_level(engine)

    print("Status:")
    print(f"  Days of Data: {level.days_of_data}")
    print(f"  Level:        {level.level} ({level.label})")
    print("  Required:     2 (graduate)")

    # Check eligibility
    if level.level < 2:
        if not force:
            print("\n[!] Insufficient data for safe training.")
            print("    Use --force to override checks and train anyway.")
            print("    WARNING: Models trained on insufficient data may degrade performance.")
            sys.exit(0)
        else:
            print("\n[!] FORCE MODE ENABLED. Ignoring graduation checks.")
    else:
        print("\n[+] Graduation checks passed.")

    print(f"\nTraining models (Output: {output_dir})...")

    # Load data
    df = _load_training_frame(engine)
    if df.empty:
        logger.error("No training data available (DataFrame is empty). Cannot train.")
        sys.exit(1)

    print(f"  Loaded {len(df)} rows of training data.")

    # Check for target columns
    if "pv_residual" not in df.columns and "load_residual" not in df.columns:
        logger.error("Data missing residual columns. Check forecast/observation data.")
        sys.exit(1)

    # Train
    # Ensure output dir exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    models = _train_error_models(df, models_dir=output_dir)

    if not models:
        print("[-] No models were trained (maybe data was all zero?).")
    else:
        print(f"\n[+] Successfully trained {len(models)} models:")
        for name in models:
            print(f"  - {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Aurora Error Correction models.")
    parser.add_argument(
        "--force", action="store_true", help="Force training even if graduation level is not met"
    )
    parser.add_argument("--dir", type=str, default="ml/models", help="Directory to save models")

    args = parser.parse_args()

    train_manual(force=args.force, output_dir=args.dir)
