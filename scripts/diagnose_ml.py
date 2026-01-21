import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path.cwd()))

from backend.learning import get_learning_engine
from ml.corrector import (
    _determine_graduation_level,
    _load_training_frame,
    train,
)


def diagnose():
    try:
        engine = get_learning_engine()
        print(f"DB Path: {engine.db_path}")

        level = _determine_graduation_level(engine)
        print(f"Graduation Level: {level.level} ({level.label})")
        print(f"Days of data: {level.days_of_data}")

        if level.level < 2:
            print("(!) Not enough data for ML training (Need Level 2).")
            return

        print("Loading training frame...")
        df = _load_training_frame(engine)
        print(f"DataFrame shape: {df.shape}")

        if df.empty:
            print("(!) DataFrame is empty.")
            return

        print("Columns:", df.columns.tolist())

        if "load_residual" in df.columns:
            residual_sum = df["load_residual"].abs().sum()
            print(f"load_residual abs sum: {residual_sum}")
            if residual_sum == 0:
                print("(!) load_residual is all zeros. Model training will be skipped.")
            else:
                print("(OK) load_residual has data.")
        else:
            print("(!) load_residual column MISSING.")

        if "pv_residual" in df.columns:
            residual_sum = df["pv_residual"].abs().sum()
            print(f"pv_residual abs sum: {residual_sum}")
        else:
            print("(!) pv_residual column MISSING.")

        # Try dry-run training
        print("\nAttempting dry-run training...")
        res = train(models_dir="ml/models")
        print("Train result:", res)

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    diagnose()
