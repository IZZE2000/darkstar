"""
Unified training orchestrator for Darkstar ML models.
"""

import logging
import shutil
import time
from datetime import datetime
from pathlib import Path

from ml.corrector import _determine_graduation_level, _get_engine, train as train_corrector
from ml.train import train_models

logger = logging.getLogger(__name__)

MODELS_DIR = Path("ml/models")
BACKUP_DIR = MODELS_DIR / "backup"
LOCK_FILE = MODELS_DIR / ".training.lock"


def _acquire_lock() -> bool:
    """Try to acquire the training lock. Return True if successful."""
    if LOCK_FILE.exists():
        # Check if lock is stale (older than 1 hour)
        if time.time() - LOCK_FILE.stat().st_mtime > 3600:
            logger.warning("Stale lock file found, removing it.")
            LOCK_FILE.unlink()
        else:
            return False

    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOCK_FILE.touch()
    return True


def _release_lock():
    """Release the training lock."""
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()


def _backup_models():
    """Backup existing models and rotate backups (keep last 2)."""
    if not MODELS_DIR.exists():
        return

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # Identify current models (.lgb files)
    model_files = list(MODELS_DIR.glob("*.lgb"))
    if not model_files:
        return

    # Create new backup timestamped directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_backup = BACKUP_DIR / f"backup_{timestamp}"
    current_backup.mkdir()

    for f in model_files:
        shutil.copy2(f, current_backup / f.name)

    logger.info(f"Created model backup in {current_backup}")

    # Rotate backups: keep only the last 2 folders
    backups = sorted([d for d in BACKUP_DIR.iterdir() if d.is_dir()], key=lambda x: x.name)
    while len(backups) > 2:
        oldest = backups.pop(0)
        shutil.rmtree(oldest)
        logger.info(f"Removed old backup: {oldest}")


def _restore_latest_backup() -> bool:
    """Restore models from the latest backup."""
    if not BACKUP_DIR.exists():
        return False

    backups = sorted([d for d in BACKUP_DIR.iterdir() if d.is_dir()], key=lambda x: x.name)
    if not backups:
        return False

    latest = backups[-1]
    logger.info(f"Restoring models from backup: {latest}")
    for f in latest.glob("*.lgb"):
        shutil.copy2(f, MODELS_DIR / f.name)
    return True


def train_all_models(days_back: int = 90, min_samples: int = 100) -> dict:
    """
    Train all ML models (AURORA main + Antares Corrector) with safety features.

    Returns a status dict:
    {
        "status": "success" | "busy" | "error",
        "trained_models": list[str],
        "corrector_status": dict,
        "duration_seconds": float,
        "error": str (optional)
    }
    """
    start_time = time.time()

    if not _acquire_lock():
        return {
            "status": "busy",
            "trained_models": [],
            "duration_seconds": 0,
            "error": "Training already in progress or lock file exists.",
        }

    results = {
        "status": "success",
        "trained_models": [],
        "corrector_status": {"status": "skipped", "reason": "not reached"},
        "duration_seconds": 0,
    }

    try:
        # 1. Backup
        _backup_models()

        # 2. Train Main Models (AURORA)
        logger.info("Starting Main Model training...")
        train_models(days_back=days_back, min_samples=min_samples)

        # Check if main models were actually created/updated
        main_models = list(MODELS_DIR.glob("*model*.lgb"))
        results["trained_models"] = [f.name for f in main_models]

        if not main_models:
            logger.warning("Main model training did not produce any models.")

        # 3. Train Corrector Models (if graduate)
        engine = _get_engine()
        level = _determine_graduation_level(engine)
        logger.info(f"Current graduation level: {level.label} (days: {level.days_of_data})")

        if level.level >= 2:
            logger.info("Starting Corrector training...")
            corr_res = train_corrector(models_dir=str(MODELS_DIR))
            results["corrector_status"] = corr_res
            if corr_res.get("status") == "trained":
                results["trained_models"].extend(corr_res.get("models_trained", []))
        else:
            results["corrector_status"] = {
                "status": "skipped",
                "reason": f"insufficient data (level: {level.label}, days: {level.days_of_data})",
            }

    except Exception as e:
        logger.exception("Unified training failed unexpectedly.")
        results["status"] = "error"
        results["error"] = str(e)

        # Try to restore if it looks like we broke something
        if not list(MODELS_DIR.glob("*model*.lgb")):
            logger.info("No main models found after failure. Attempting restore from backup...")
            _restore_latest_backup()

    finally:
        _release_lock()
        results["duration_seconds"] = round(time.time() - start_time, 2)
        logger.info(f"Unified training finished: {results}")

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = train_all_models()
    print(res)
