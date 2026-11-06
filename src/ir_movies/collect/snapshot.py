"""Escrita do snapshot parquet e snapshot_meta.json (D-016, D-025)."""

from __future__ import annotations

import json
import logging
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import median

import pandas as pd

logger = logging.getLogger(__name__)


def _extract_row(raw: dict) -> dict:
    """Extrai as colunas do esquema de architecture.md a partir do JSON bruto."""
    genres = [g["name"] for g in raw.get("genres") or []]

    kw_container = raw.get("keywords") or {}
    keywords = [k["name"] for k in kw_container.get("keywords") or []]

    credits = raw.get("credits") or {}
    cast = [c["name"] for c in (credits.get("cast") or [])[:5]]
    director = ""
    for crew in credits.get("crew") or []:
        if crew.get("job") == "Director":
            director = crew.get("name", "")
            break

    return {
        "id": raw["id"],
        "title": raw.get("title", ""),
        "original_title": raw.get("original_title", ""),
        "tagline": raw.get("tagline") or "",
        "overview": raw.get("overview", ""),
        "genres": genres,
        "keywords": keywords,
        "cast_top5": cast,
        "director": director,
        "release_date": raw.get("release_date") or "",
        "runtime": raw.get("runtime"),
        "vote_average": raw.get("vote_average", 0.0),
        "vote_count": raw.get("vote_count", 0),
        "popularity": raw.get("popularity", 0.0),
        "poster_path": raw.get("poster_path"),
    }


def _git_hash() -> str:
    """Retorna o hash curto do HEAD, ou 'unknown' se não estiver em um repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return "unknown"


def _build_meta(
    rows: list[dict],
    rejection_counts: Counter,
    n_candidates: int,
    cfg: dict,
) -> dict:
    """Monta o dicionário de metadados do snapshot."""
    now = datetime.now(UTC)
    overview_lengths = [len(r["overview"].split()) for r in rows]

    return {
        "snapshot_id": now.strftime("%Y%m%d"),
        "created_utc": now.isoformat(),
        "endpoints": ["GET /movie/{id}?language=pt-BR&append_to_response=credits,keywords"],
        "filters": {
            "min_overview_words": cfg.get("snapshot", {}).get("min_overview_words", 5),
            "min_vote_count": cfg.get("snapshot", {}).get("min_vote_count", 2),
            "exclude_adult": cfg.get("snapshot", {}).get("exclude_adult", True),
        },
        "candidates_tested": n_candidates,
        "accepted": len(rows),
        "rejections_by_reason": dict(rejection_counts),
        "overview_word_count": {
            "min": min(overview_lengths) if overview_lengths else 0,
            "median": int(median(overview_lengths)) if overview_lengths else 0,
            "max": max(overview_lengths) if overview_lengths else 0,
        },
        "git_hash": _git_hash(),
        "code_version": "sprint-02",
    }


def validate_snapshot(df: pd.DataFrame, cfg: dict) -> list[str]:
    """Executa as validações de D-025. Retorna lista de erros (vazia = ok)."""
    errors: list[str] = []
    snap_cfg = cfg.get("snapshot", {})
    min_words = snap_cfg.get("min_overview_words", 5)
    min_votes = snap_cfg.get("min_vote_count", 2)

    if df["id"].duplicated().any():
        n_dup = df["id"].duplicated().sum()
        errors.append(f"{n_dup} IDs duplicados")

    required_cols = ["id", "title", "overview"]
    for col in required_cols:
        n_null = df[col].isna().sum()
        if n_null > 0:
            errors.append(f"{n_null} nulos na coluna obrigatória '{col}'")

    short = df["overview"].apply(lambda x: len(str(x).split()) < min_words)
    if short.any():
        errors.append(f"{short.sum()} sinopses com < {min_words} palavras")

    low_votes = df["vote_count"] < min_votes
    if low_votes.any():
        errors.append(f"{low_votes.sum()} filmes com vote_count < {min_votes}")

    return errors


def write_snapshot(
    movies_raw: list[dict],
    cfg: dict,
    rejection_counts: Counter,
    n_candidates: int,
    dest_dir: str | Path | None = None,
) -> tuple[Path, Path]:
    """Extrai colunas, valida e escreve parquet + snapshot_meta.json.

    Retorna ``(parquet_path, meta_path)``.
    Levanta ``ValueError`` se as validações de D-025 falharem.
    """
    if dest_dir is None:
        from ir_movies.config import PROJECT_ROOT

        dest_dir = PROJECT_ROOT / "data"
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    rows = [_extract_row(raw) for raw in movies_raw]
    df = pd.DataFrame(rows)

    validation_errors = validate_snapshot(df, cfg)
    if validation_errors:
        raise ValueError(
            "Validações do snapshot falharam:\n" + "\n".join(f"  - {e}" for e in validation_errors)
        )

    meta = _build_meta(rows, rejection_counts, n_candidates, cfg)
    snapshot_id = meta["snapshot_id"]

    parquet_path = dest_dir / f"movies_ptbr_{snapshot_id}.parquet"
    df.to_parquet(parquet_path, index=False, engine="pyarrow")
    meta["file_size_bytes"] = parquet_path.stat().st_size
    logger.info(
        "Parquet escrito: %s (%d linhas, %d bytes)",
        parquet_path, len(df), meta["file_size_bytes"],
    )

    meta_path = dest_dir / "snapshot_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    logger.info("Meta escrito: %s", meta_path)

    return parquet_path, meta_path
