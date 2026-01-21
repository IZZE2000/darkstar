"""
Unified training orchestrator for Darkstar ML models.
"""

import asyncio
import logging
import shutil
import time
from datetime import datetime
from pathlib import Path

from backend.core.websockets import ws_manager
from ml.corrector import _determine_graduation_level, _get_engine, train as train_corrector
from ml.train import train_models

logger = logging.getLogger(__name__)

MODELS_DIR = Path("data/ml/models")
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


def _load_config() -> dict:
    """Load config.yaml for training decisions."""
    import yaml

    try:
        with Path("config.yaml").open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Failed to load config: {e}")
        return {}


def get_training_status() -> dict:
    """
    Get current training status and model information.
    """
    is_training = False
    lock_age = None
    lock_exists = LOCK_FILE.exists()
    is_stale = False

    if lock_exists:
        age_seconds = time.time() - LOCK_FILE.stat().st_mtime
        if age_seconds > 3600:
            is_stale = True
            # Do not report as "training" if stale, so UI unlocks
        else:
            is_training = True
        lock_age = age_seconds

    models_info = {}
    if MODELS_DIR.exists():
        for f in MODELS_DIR.glob("*.lgb"):
            models_info[f.name] = {
                "last_modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                "age_seconds": time.time() - f.stat().st_mtime,
                "size_bytes": f.stat().st_size,
            }

    return {
        "is_training": is_training,
        "lock_age_seconds": lock_age,
        "lock_status": {"locked": lock_exists, "stale": is_stale, "lock_age_seconds": lock_age},
        "models": models_info,
    }


async def train_all_models(
    days_back: int = 90, min_samples: int = 100, training_type: str = "automatic"
) -> dict:
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
    engine = _get_engine()
    store = engine.store

    # Notify start
    logger.info(f"[ML-TRAIN] Starting unified training pipeline (Type: {training_type.upper()})")
    await ws_manager.emit(
        "training_progress",
        {
            "type": "training_progress",
            "status": "busy",
            "stage": "starting",
            "message": f"Initializing {training_type} training...",
            "progress": 0.05,
        },
    )

    if not _acquire_lock():
        logger.warning(
            f"[ML-TRAIN] Training skipped: Another instance is running (Type: {training_type})"
        )
        await ws_manager.emit(
            "training_progress",
            {
                "type": "training_progress",
                "status": "error",
                "stage": "idle",
                "message": "Training already in progress",
                "progress": 0.0,
            },
        )
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
        logger.info("[ML-TRAIN] Model backup completed")

        # 2. Train Main Models (AURORA)
        logger.info("[ML-TRAIN] Step 1/2: Training Main Models (AURORA)...")
        await ws_manager.emit(
            "training_progress",
            {
                "type": "training_progress",
                "status": "busy",
                "stage": "training_main_models",
                "message": "Training main Aurora models (this may take a minute)...",
                "progress": 0.2,
            },
        )

        # train_models is heavy and synchronous, offload to thread
        await asyncio.to_thread(train_models, days_back=days_back, min_samples=min_samples)

        # Check if main models were actually created/updated
        main_models = list(MODELS_DIR.glob("*model*.lgb"))
        results["trained_models"] = [f.name for f in main_models]

        if not main_models:
            logger.warning("[ML-TRAIN] Main model training did not produce any models.")
        else:
            logger.info(f"[ML-TRAIN] Main models trained: {len(main_models)} found")

        # 3. Train Corrector Models (if graduate AND enabled)
        level = _determine_graduation_level(engine)
        logger.info(
            f"[ML-TRAIN] Graduation Status: {level.label.upper()} (Data: {level.days_of_data:.1f} days)"
        )

        # ARC11 Fix: Check if error correction is enabled in config
        config = _load_config()
        error_correction_enabled = config.get("learning", {}).get("error_correction_enabled", True)

        if level.level >= 2 and error_correction_enabled:
            logger.info("[ML-TRAIN] Step 2/2: Training Corrector Models...")
            await ws_manager.emit(
                "training_progress",
                {
                    "type": "training_progress",
                    "status": "busy",
                    "stage": "training_corrector",
                    "message": "Training error correction models...",
                    "progress": 0.6,
                },
            )

            # train_corrector is also heavy/sync
            corr_res = await asyncio.to_thread(train_corrector, models_dir=str(MODELS_DIR))
            results["corrector_status"] = corr_res
            if corr_res.get("status") == "trained":
                results["trained_models"].extend(corr_res.get("models_trained", []))
                logger.info(
                    f"[ML-TRAIN] Corrector training successful. Models: {corr_res.get('models_trained', [])}"
                )
            else:
                logger.warning(f"[ML-TRAIN] Corrector training info: {corr_res.get('status')}")

        elif level.level >= 2 and not error_correction_enabled:
            logger.info("[ML-TRAIN] Corrector training SKIPPED: Disabled in config")
            results["corrector_status"] = {"status": "disabled", "reason": "disabled in config"}
        else:
            logger.info(
                f"[ML-TRAIN] Corrector training SKIPPED: Insufficient graduation level (Need >= Graduate, have {level.label})"
            )
            results["corrector_status"] = {
                "status": "skipped",
                "reason": f"insufficient data (level: {level.label}, days: {level.days_of_data})",
            }

        # 4. Cleanup old history (ARC11 Phase 2)
        deleted_runs = await store.cleanup_learning_runs(days_back=30)
        if deleted_runs > 0:
            logger.info(f"Cleaned up {deleted_runs} old training records.")

    except Exception as e:
        logger.exception("Unified training failed unexpectedly.")
        results["status"] = "error"
        results["error"] = str(e)

        await ws_manager.emit(
            "training_progress",
            {
                "type": "training_progress",
                "status": "error",
                "stage": "idle",
                "message": f"Training failed: {e}",
                "progress": 0.0,
            },
        )

        # Try to restore if it looks like we broke something
        if not list(MODELS_DIR.glob("*model*.lgb")):
            logger.info("No main models found after failure. Attempting restore from backup...")
            _restore_latest_backup()

    finally:
        _release_lock()
        duration = round(time.time() - start_time, 2)
        results["duration_seconds"] = duration
        logger.info(f"Unified training finished: {results}")

        # Log unified run result to DB (ARC11 Phase 2)
        try:
            await store.log_learning_run(
                status=results["status"],
                result_metrics={
                    "main_models_count": len(
                        [m for m in results["trained_models"] if "corrector" not in m]
                    ),
                    "corrector_status": results["corrector_status"].get("status"),
                },
                training_type=training_type,
                models_trained=results["trained_models"],
                duration_seconds=int(duration),
                partial_failure=results["status"] == "success" and not results["trained_models"],
                error_message=results.get("error"),
            )
        except Exception as db_err:
            logger.error(f"Failed to log unified training run to DB: {db_err}")

    # Final success event if not error
    if results["status"] == "success":
        await ws_manager.emit(
            "training_progress",
            {
                "type": "training_progress",
                "status": "success",
                "stage": "idle",
                "message": "Training completed successfully",
                "progress": 1.0,
                "result": results,
            },
        )

    return results


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)
    res = asyncio.run(train_all_models())
    print(res)
