from fastapi import Request

from backend.learning.store import LearningStore


def get_learning_store(request: Request) -> LearningStore:
    """Dependency to retrieve the shared Async LearningStore instance."""
    store = getattr(request.app.state, "learning_store", None)
    if store is None:
        raise RuntimeError("LearningStore is not initialized in app.state")
    return store
