"""Carregador do snapshot: parquet -> ``Movie`` + textos indexados (D-034, D-090).

O parquet é localizado pelo ``snapshot_id`` de ``snapshot_meta.json``; nenhum nome de
arquivo fica embutido no código, então uma recoleta futura não quebra nada.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ir_movies.config import PROJECT_ROOT
from ir_movies.query.types import Movie

__all__ = [
    "DEFAULT_DATA_DIR",
    "LoadedSnapshot",
    "document_text",
    "load_snapshot",
    "resolve_snapshot_paths",
]

DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
META_FILENAME = "snapshot_meta.json"
PARQUET_TEMPLATE = "movies_ptbr_{snapshot_id}.parquet"


def document_text(movie: Movie) -> str:
    """Texto indexado de um filme: título + tagline + sinopse + gêneros (D-013).

    Mesma convenção de ``tests/fakes.py``: concatenação por um espaço, sem peso por
    campo. Keywords e elenco ficam de fora na v1.
    """
    return " ".join([movie.title, movie.tagline, movie.overview, " ".join(movie.genres)])


@dataclass(frozen=True)
class LoadedSnapshot:
    """Acervo carregado: filmes e, na mesma ordem, os textos que vão ao índice.

    A posição *i* de ``movies`` e de ``texts`` é o ``doc_id`` *i* do índice.
    """

    snapshot_id: str
    movies: list[Movie]
    texts: list[str]

    @classmethod
    def from_movies(cls, snapshot_id: str, movies: list[Movie]) -> LoadedSnapshot:
        """Monta o acervo a partir de filmes já normalizados (útil em testes)."""
        return cls(snapshot_id, list(movies), [document_text(m) for m in movies])


def resolve_snapshot_paths(data_dir: str | Path | None = None) -> tuple[str, Path]:
    """Devolve ``(snapshot_id, caminho_do_parquet)`` conforme o meta do diretório.

    Levanta ``FileNotFoundError`` (com o caminho procurado) se faltar o meta ou o parquet.
    """
    data_dir = _resolve_dir(data_dir)
    meta_path = data_dir / META_FILENAME
    if not meta_path.is_file():
        raise FileNotFoundError(f"Metadados do snapshot não encontrados: {meta_path}")
    with open(meta_path, encoding="utf-8") as f:
        snapshot_id = str(json.load(f)["snapshot_id"])
    parquet_path = data_dir / PARQUET_TEMPLATE.format(snapshot_id=snapshot_id)
    if not parquet_path.is_file():
        raise FileNotFoundError(
            f"Parquet do snapshot {snapshot_id} não encontrado: {parquet_path}"
        )
    return snapshot_id, parquet_path


def load_snapshot(data_dir: str | Path | None = None) -> LoadedSnapshot:
    """Lê o snapshot de *data_dir* (padrão: ``data/`` na raiz do projeto)."""
    snapshot_id, parquet_path = resolve_snapshot_paths(data_dir)
    df = pd.read_parquet(parquet_path)
    movies = [_row_to_movie(row) for row in df.to_dict(orient="records")]
    return LoadedSnapshot.from_movies(snapshot_id, movies)


def _resolve_dir(data_dir: str | Path | None) -> Path:
    if data_dir is None:
        return DEFAULT_DATA_DIR
    path = Path(data_dir)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _is_missing(value: object) -> bool:
    """Nulo do pandas (None, NaN, NA) ou string vazia."""
    return value is None or bool(pd.isna(value)) or value == ""


def _text(value: object) -> str:
    return "" if _is_missing(value) else str(value)


def _text_list(value: object) -> list[str]:
    return [] if value is None else [str(v) for v in value]


def _row_to_movie(row: dict) -> Movie:
    """Converte uma linha do parquet em ``Movie`` com as normalizações de D-090."""
    runtime = row.get("runtime")
    runtime = None if _is_missing(runtime) or int(runtime) == 0 else int(runtime)
    poster = row.get("poster_path")
    return Movie(
        id=int(row["id"]),
        title=_text(row.get("title")),
        original_title=_text(row.get("original_title")),
        tagline=_text(row.get("tagline")),
        overview=_text(row.get("overview")),
        genres=_text_list(row.get("genres")),
        cast_top5=_text_list(row.get("cast_top5")),
        director=_text(row.get("director")),
        release_date=_text(row.get("release_date")),
        runtime=runtime,
        vote_average=float(row.get("vote_average") or 0.0),
        vote_count=int(row.get("vote_count") or 0),
        poster_path=None if _is_missing(poster) else str(poster),
    )
