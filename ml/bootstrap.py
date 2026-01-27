import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def ensure_active_models():
    """
    Implements 'Seed & Drift' strategy for ML models.

    1. Checks if runtime models exist in `data/ml/models/`.
    2. If EMPTY: Copies from `ml/models/defaults/` (Seeding).
    3. If EXISTS: Does nothing (Drift/Training preserved).
    4. ALWAYS: Copies defaults to `data/ml/models/defaults/` for reference/reset.
    """
    # Use relative paths anchored to this file for robustness across Docker/Local
    base_dir = Path(__file__).parent.parent  # Project root
    defaults_dir = base_dir / "ml" / "models" / "defaults"
    runtime_dir = base_dir / "data" / "ml" / "models"
    runtime_defaults_dir = runtime_dir / "defaults"

    logger.info(f"Model Bootstrap: Checking {runtime_dir}")

    # Safety check: Defaults must exist
    if not defaults_dir.exists():
        logger.error(f"CRITICAL: Default models missing at {defaults_dir}")
        return

    # Ensure runtime directory exists
    runtime_dir.mkdir(parents=True, exist_ok=True)

    # 1. Seed if empty
    # Filter for .lgb files to avoid counting directories or temp files
    existing_models = list(runtime_dir.glob("*.lgb"))

    if not existing_models:
        logger.info("⚠️ No active models found. Seeding from defaults...")
        for model_file in defaults_dir.glob("*.lgb"):
            shutil.copy2(model_file, runtime_dir / model_file.name)
        logger.info("✅ Seeding complete.")
    else:
        logger.info(f"✅ Active models found ({len(existing_models)} files). Skipping seed.")

    # 2. Always update the "Factory Reset" image in data/
    # This allows users to see what the defaults are without digging into source code
    if runtime_defaults_dir.exists():
        shutil.rmtree(runtime_defaults_dir)
    shutil.copytree(defaults_dir, runtime_defaults_dir)
    logger.info("Updated runtime defaults backup.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ensure_active_models()
