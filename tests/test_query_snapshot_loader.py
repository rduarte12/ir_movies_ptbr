"""Testes do carregador do snapshot (D-034, D-090)."""

import json

import pandas as pd
import pytest

from ir_movies.query.snapshot_loader import (
    DEFAULT_DATA_DIR,
    LoadedSnapshot,
    document_text,
    load_snapshot,
    resolve_snapshot_paths,
)
from ir_movies.query.types import Movie
from tests.fakes import FakeSearchService
from tests.fakes import document_text as fake_document_text


def _row(**overrides):
    base = {
        "id": 1,
        "title": "Título",
        "original_title": "Original",
        "tagline": "Frase",
        "overview": "Uma sinopse com várias palavras",
        "genres": ["Drama", "Ação"],
        "keywords": ["x"],
        "cast_top5": ["A", "B"],
        "director": "Diretora",
        "release_date": "2001-02-03",
        "runtime": 100,
        "vote_average": 7.5,
        "vote_count": 10,
        "popularity": 1.0,
        "poster_path": "/p.jpg",
    }
    base.update(overrides)
    return base


def _write_snapshot(data_dir, snapshot_id, rows):
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "snapshot_meta.json").write_text(
        json.dumps({"snapshot_id": snapshot_id}), encoding="utf-8"
    )
    pd.DataFrame(rows).to_parquet(data_dir / f"movies_ptbr_{snapshot_id}.parquet")


class TestResolution:
    def test_picks_parquet_named_by_meta_not_by_glob(self, tmp_path):
        """Três parquets lado a lado: vale o que o meta aponta."""
        _write_snapshot(tmp_path, "20300101", [_row(id=1), _row(id=2)])
        pd.DataFrame([_row(id=99)]).to_parquet(tmp_path / "movies_ptbr_19990101.parquet")
        pd.DataFrame([_row(id=98)]).to_parquet(tmp_path / "movies_ptbr_30000101.parquet")

        snap = load_snapshot(tmp_path)

        assert snap.snapshot_id == "20300101"
        assert [m.id for m in snap.movies] == [1, 2]

    def test_resolve_returns_id_and_path(self, tmp_path):
        _write_snapshot(tmp_path, "20300101", [_row()])
        snapshot_id, path = resolve_snapshot_paths(tmp_path)
        assert snapshot_id == "20300101"
        assert path == tmp_path / "movies_ptbr_20300101.parquet"

    def test_missing_meta_raises_with_path(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="snapshot_meta.json"):
            load_snapshot(tmp_path)

    def test_missing_parquet_raises_with_path(self, tmp_path):
        (tmp_path / "snapshot_meta.json").write_text(
            json.dumps({"snapshot_id": "20300101"}), encoding="utf-8"
        )
        with pytest.raises(FileNotFoundError, match="movies_ptbr_20300101"):
            load_snapshot(tmp_path)


class TestNormalization:
    @pytest.fixture
    def movies(self, tmp_path):
        rows = [
            _row(id=1),
            _row(id=2, runtime=0, poster_path=None, tagline=None, director=None),
            _row(id=3, runtime=None, poster_path="", release_date=None),
        ]
        _write_snapshot(tmp_path, "20300101", rows)
        return {m.id: m for m in load_snapshot(tmp_path).movies}

    def test_complete_row_is_untouched(self, movies):
        m = movies[1]
        assert m.runtime == 100
        assert m.poster_path == "/p.jpg"
        assert m.tagline == "Frase"
        assert m.director == "Diretora"
        assert m.release_date == "2001-02-03"
        assert m.year == "2001"

    def test_zero_runtime_becomes_none(self, movies):
        assert movies[2].runtime is None

    def test_null_runtime_becomes_none(self, movies):
        assert movies[3].runtime is None

    def test_null_and_empty_poster_become_none(self, movies):
        assert movies[2].poster_path is None
        assert movies[3].poster_path is None

    def test_null_text_fields_become_empty_string(self, movies):
        assert movies[2].tagline == ""
        assert movies[2].director == ""
        assert movies[3].release_date == ""
        assert movies[3].year == ""

    def test_lists_are_plain_lists_of_str(self, movies):
        m = movies[1]
        assert type(m.genres) is list and m.genres == ["Drama", "Ação"]
        assert type(m.cast_top5) is list and m.cast_top5 == ["A", "B"]
        assert all(type(g) is str for g in m.genres)

    def test_scalar_types(self, movies):
        m = movies[1]
        assert type(m.id) is int
        assert type(m.runtime) is int
        assert type(m.vote_count) is int
        assert type(m.vote_average) is float


class TestDocumentText:
    def test_concatenation_order(self):
        movie = Movie(
            id=1,
            title="T",
            original_title="O",
            tagline="G",
            overview="S",
            genres=["A", "B"],
            cast_top5=["Fulano"],
            director="Dir",
            release_date="2000-01-01",
            runtime=None,
            vote_average=0.0,
            vote_count=0,
            poster_path=None,
        )
        assert document_text(movie) == "T G S A B"

    def test_matches_the_reference_implementation(self):
        """Serviço real e serviço falso precisam indexar o mesmo texto (D-013)."""
        fake = FakeSearchService.from_toy()
        for movie_id in range(1, 6):
            movie = fake.get_movie(movie_id)
            assert document_text(movie) == fake_document_text(movie)

    def test_from_movies_keeps_order_and_texts(self):
        fake = FakeSearchService.from_toy()
        movies = [fake.get_movie(i) for i in range(1, 6)]
        snap = LoadedSnapshot.from_movies("toy", movies)
        assert snap.texts == [document_text(m) for m in movies]
        assert len(snap.texts) == len(snap.movies) == 5


class TestRealSnapshot:
    def test_loads_all_accepted_movies(self):
        with open(DEFAULT_DATA_DIR / "snapshot_meta.json", encoding="utf-8") as f:
            meta = json.load(f)
        snap = load_snapshot()
        assert snap.snapshot_id == meta["snapshot_id"]
        assert len(snap.movies) == len(snap.texts) == meta["accepted"]

    def test_real_snapshot_obeys_normalization(self):
        snap = load_snapshot()
        assert all(m.runtime is None or m.runtime > 0 for m in snap.movies)
        assert all(m.poster_path is None or m.poster_path.startswith("/") for m in snap.movies)
        assert any(m.runtime is None for m in snap.movies)
        assert any(m.poster_path is None for m in snap.movies)
        assert len({m.id for m in snap.movies}) == len(snap.movies)
