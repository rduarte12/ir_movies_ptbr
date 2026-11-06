"""Pipeline de coleta: filtros, checkpoint e snapshot."""

from ir_movies.collect.filters import evaluate
from ir_movies.collect.pipeline import CollectionResult, load_checkpoint, run
from ir_movies.collect.snapshot import validate_snapshot, write_snapshot

__all__ = [
    "CollectionResult",
    "evaluate",
    "load_checkpoint",
    "run",
    "validate_snapshot",
    "write_snapshot",
]
