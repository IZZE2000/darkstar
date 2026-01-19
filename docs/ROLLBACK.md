# Rollback Procedure: ARC11 Async Migration

If critical instability is detected after the ARC11 merge (e.g., event loop starvation, database connection leaks), follow these steps to revert the system to its pre-async state.

## 1. Automated Revert

The transition was tagged at key stages:
- `pre-arc11`: State before major async refactoring.
- `arc11-complete`: Current fully async state.

To revert the codebase:
```bash
git revert -m 1 <arc11-merge-commit-hash>
# Or hard reset to pre-arc11 if no other changes were made
git reset --hard pre-arc11
```

## 2. Database Recovery

ARC11 did not introduce breaking schema changes, but it did unify the `LearningStore`. If you revert the code, the database `planner_learning.db` should remain compatible with the previous hybrid engine.

If schema issues occur:
```bash
# Revert to the last stable migration if applicable
alembic downgrade <revision-before-arc11>
```

## 3. Service Restart

After reverting the code:
1. Re-install dependencies (if any changed): `pip install -r requirements.txt`.
2. Restart the Darkstar service: `systemctl restart darkstar` or `docker compose restart`.
3. Monitor logs for `AttributeError` or `ImproperlyConfigured` errors.

## 4. Verification

Verify the system is back in "Hybrid Mode":
- Check `backend/recorder.py` for synchronous `while True` loop and `time.sleep`.
- Check `backend/learning/store.py` for the existence of `self.Session`.
