"""Orquestração da coleta: busca detalhes dos top N candidatos e filtra (D-024, D-026)."""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from ir_movies.collect.filters import evaluate
from ir_movies.collect.snapshot import write_snapshot
from ir_movies.tmdb.client import TmdbApiError, TmdbClient

logger = logging.getLogger(__name__)


@dataclass
class CollectionResult:
    """Resultado final da coleta."""

    accepted: int = 0
    rejected: int = 0
    errors: int = 0
    rejection_counts: Counter = field(default_factory=Counter)
    parquet_path: Path | None = None
    meta_path: Path | None = None


def load_checkpoint(checkpoint_dir: Path) -> tuple[set[int], list[dict], Counter]:
    """Carrega estado do checkpoint.

    Retorna (ids processados, filmes aceitos, contagem de rejeições).
    """
    processed_ids: set[int] = set()
    accepted_movies: list[dict] = []
    rejection_counts: Counter = Counter()

    progress_path = checkpoint_dir / "progress.jsonl"
    if progress_path.exists():
        with open(progress_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                processed_ids.add(entry["id"])
                if entry["status"] == "rejected":
                    rejection_counts[entry["reason"]] += 1

    movies_path = checkpoint_dir / "accepted_movies.jsonl"
    if movies_path.exists():
        with open(movies_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                accepted_movies.append(json.loads(line))

    return processed_ids, accepted_movies, rejection_counts


def _flush_checkpoint(
    checkpoint_dir: Path,
    progress_buffer: list[dict],
    movies_buffer: list[dict],
) -> None:
    """Acrescenta buffers aos arquivos de checkpoint."""
    if progress_buffer:
        with open(checkpoint_dir / "progress.jsonl", "a", encoding="utf-8") as f:
            for entry in progress_buffer:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    if movies_buffer:
        with open(checkpoint_dir / "accepted_movies.jsonl", "a", encoding="utf-8") as f:
            for movie in movies_buffer:
                f.write(json.dumps(movie, ensure_ascii=False) + "\n")


def run(
    cfg: dict,
    token: str,
    candidates: list[tuple[int, float]],
    *,
    checkpoint_dir: str | Path | None = None,
    data_dir: str | Path | None = None,
) -> CollectionResult:
    """Busca detalhes dos primeiros ``target_size`` candidatos e aplica filtros.

    O parquet final contém todos os que passaram nos filtros (≤ target_size).
    Salva checkpoint incremental em *checkpoint_dir*.
    """
    if checkpoint_dir is None:
        from ir_movies.config import PROJECT_ROOT

        checkpoint_dir = PROJECT_ROOT / "data" / "checkpoints"
    if data_dir is None:
        from ir_movies.config import PROJECT_ROOT

        data_dir = PROJECT_ROOT / "data"

    checkpoint_dir = Path(checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    snap_cfg = cfg.get("snapshot", {})
    target_size = snap_cfg.get("target_size", 20000)
    checkpoint_interval = snap_cfg.get("checkpoint_interval", 500)

    to_fetch = candidates[:target_size]
    logger.info("Candidatos a buscar: %d (top %d por popularidade)", len(to_fetch), target_size)

    processed_ids, accepted_movies, rejection_counts = load_checkpoint(checkpoint_dir)
    if processed_ids:
        logger.info(
            "Checkpoint carregado: %d processados, %d aceitos",
            len(processed_ids),
            len(accepted_movies),
        )

    result = CollectionResult(
        accepted=len(accepted_movies),
        rejection_counts=rejection_counts,
    )
    for _reason, count in rejection_counts.items():
        result.rejected += count

    progress_buffer: list[dict] = []
    movies_buffer: list[dict] = []
    candidates_since_flush = 0

    with TmdbClient(token=token, cfg=cfg) as client:
        for i, (movie_id, _pop) in enumerate(to_fetch):
            if movie_id in processed_ids:
                continue

            try:
                raw = client.get_movie(movie_id)
            except TmdbApiError as exc:
                logger.warning("Erro ao buscar movie_id=%d: %s", movie_id, exc)
                progress_buffer.append(
                    {"id": movie_id, "status": "error", "reason": str(exc)[:200]}
                )
                result.errors += 1
                candidates_since_flush += 1
            else:
                accepted, reason = evaluate(raw, cfg)
                if accepted:
                    movies_buffer.append(raw)
                    progress_buffer.append({"id": movie_id, "status": "accepted", "reason": None})
                    result.accepted += 1
                else:
                    progress_buffer.append(
                        {"id": movie_id, "status": "rejected", "reason": reason}
                    )
                    result.rejected += 1
                    result.rejection_counts[reason] += 1
                candidates_since_flush += 1

            if candidates_since_flush >= checkpoint_interval:
                _flush_checkpoint(checkpoint_dir, progress_buffer, movies_buffer)
                progress_buffer.clear()
                movies_buffer.clear()
                candidates_since_flush = 0
                logger.info(
                    "Checkpoint: %d aceitos, %d rejeitados, %d erros (candidato %d/%d)",
                    result.accepted,
                    result.rejected,
                    result.errors,
                    i + 1,
                    len(to_fetch),
                )

    _flush_checkpoint(checkpoint_dir, progress_buffer, movies_buffer)

    n_candidates = result.accepted + result.rejected + result.errors
    logger.info(
        "Coleta concluída: %d aceitos, %d rejeitados, %d erros",
        result.accepted, result.rejected, result.errors,
    )

    final_movies: list[dict] = []
    movies_path = checkpoint_dir / "accepted_movies.jsonl"
    if movies_path.exists():
        with open(movies_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    final_movies.append(json.loads(line))

    if final_movies:
        parquet_path, meta_path = write_snapshot(
            final_movies,
            cfg,
            result.rejection_counts,
            n_candidates,
            dest_dir=data_dir,
        )
        result.parquet_path = parquet_path
        result.meta_path = meta_path

    return result
