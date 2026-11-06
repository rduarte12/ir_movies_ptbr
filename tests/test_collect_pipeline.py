"""Testes para ir_movies.collect.pipeline (sem rede, usando mock do TmdbClient)."""

import json
from collections import Counter
from pathlib import Path
from unittest.mock import MagicMock, patch

from ir_movies.collect.pipeline import _flush_checkpoint, load_checkpoint, run
from ir_movies.tmdb.client import TmdbApiError

FIXTURES_DIR = Path(__file__).parent / "fixtures"

_CFG = {
    "snapshot": {
        "target_size": 3,
        "min_overview_words": 5,
        "min_vote_count": 2,
        "exclude_adult": True,
        "checkpoint_interval": 2,
    },
    "tmdb": {
        "language": "pt-BR",
        "retry": {"max_attempts": 1, "backoff_factor": 0.01},
        "rate_limit_rps": 1000,
    },
}


def _load_fixture_278() -> dict:
    with open(FIXTURES_DIR / "movie_278.json", encoding="utf-8") as f:
        return json.load(f)


def _make_movie(
    movie_id: int,
    overview: str = "Uma sinopse longa o suficiente para passar",
    vote_count: int = 10,
) -> dict:
    """Cria um filme falso que passa nos filtros."""
    base = _load_fixture_278()
    base["id"] = movie_id
    base["overview"] = overview
    base["vote_count"] = vote_count
    return base


class TestLoadCheckpoint:
    def test_empty_checkpoint(self, tmp_path):
        ids, movies, counts = load_checkpoint(tmp_path)
        assert ids == set()
        assert movies == []
        assert counts == Counter()

    def test_loads_existing_checkpoint(self, tmp_path):
        progress = [
            {"id": 1, "status": "accepted", "reason": None},
            {"id": 2, "status": "rejected", "reason": "low_votes"},
            {"id": 3, "status": "error", "reason": "timeout"},
        ]
        with open(tmp_path / "progress.jsonl", "w", encoding="utf-8") as f:
            for entry in progress:
                f.write(json.dumps(entry) + "\n")

        movie = _make_movie(1)
        with open(tmp_path / "accepted_movies.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps(movie) + "\n")

        ids, movies, counts = load_checkpoint(tmp_path)
        assert ids == {1, 2, 3}
        assert len(movies) == 1
        assert movies[0]["id"] == 1
        assert counts["low_votes"] == 1


class TestFlushCheckpoint:
    def test_appends_to_files(self, tmp_path):
        movie = _make_movie(1)
        progress = [{"id": 1, "status": "accepted", "reason": None}]

        _flush_checkpoint(tmp_path, progress, [movie])
        _flush_checkpoint(tmp_path, [{"id": 2, "status": "rejected", "reason": "low_votes"}], [])

        with open(tmp_path / "progress.jsonl", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        assert len(lines) == 2

        with open(tmp_path / "accepted_movies.jsonl", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        assert len(lines) == 1


class TestRunPipeline:
    def _run_with_mock(
        self, candidates, movies_by_id, cfg=None, checkpoint_dir=None, data_dir=None,
    ):
        """Executa o pipeline com um TmdbClient mockado."""
        cfg = cfg or _CFG

        def mock_get_movie(movie_id):
            if movie_id in movies_by_id:
                return movies_by_id[movie_id]
            raise TmdbApiError(404, movie_id, "Not found")

        with patch("ir_movies.collect.pipeline.TmdbClient") as MockClient:
            instance = MagicMock()
            instance.get_movie.side_effect = mock_get_movie
            instance.__enter__ = MagicMock(return_value=instance)
            instance.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = instance

            return run(
                cfg,
                token="fake",
                candidates=candidates,
                checkpoint_dir=checkpoint_dir,
                data_dir=data_dir,
            )

    def test_collects_up_to_target_size(self, tmp_path):
        movies = {i: _make_movie(i) for i in range(1, 6)}
        candidates = [(i, 100 - i) for i in range(1, 6)]

        result = self._run_with_mock(
            candidates, movies,
            checkpoint_dir=tmp_path / "ckpt",
            data_dir=tmp_path / "data",
        )

        assert result.accepted == 3  # target_size = 3
        assert result.parquet_path is not None
        assert result.parquet_path.exists()

    def test_counts_rejections(self, tmp_path):
        movies = {}
        for i in range(1, 5):
            m = _make_movie(i)
            if i == 2:
                m["overview"] = ""
            if i == 3:
                m["vote_count"] = 0
            movies[i] = m

        cfg = {**_CFG, "snapshot": {**_CFG["snapshot"], "target_size": 10}}
        candidates = [(i, 100 - i) for i in range(1, 5)]

        result = self._run_with_mock(
            candidates, movies,
            cfg=cfg,
            checkpoint_dir=tmp_path / "ckpt",
            data_dir=tmp_path / "data",
        )

        assert result.accepted == 2  # id 1 e 4
        assert result.rejected == 2  # id 2 (no_overview) e 3 (low_votes)
        assert result.rejection_counts["no_overview"] == 1
        assert result.rejection_counts["low_votes"] == 1

    def test_handles_api_errors(self, tmp_path):
        movies = {1: _make_movie(1), 3: _make_movie(3)}  # id 2 vai dar 404
        candidates = [(1, 100), (2, 99), (3, 98)]
        cfg = {**_CFG, "snapshot": {**_CFG["snapshot"], "target_size": 10}}

        result = self._run_with_mock(
            candidates, movies,
            cfg=cfg,
            checkpoint_dir=tmp_path / "ckpt",
            data_dir=tmp_path / "data",
        )

        assert result.accepted == 2
        assert result.errors == 1

    def test_resume_from_checkpoint(self, tmp_path):
        """Simula interrupção: roda com 2 candidatos, depois retoma com mais."""
        ckpt_dir = tmp_path / "ckpt"
        data_dir = tmp_path / "data"

        # Primeira execução: 2 filmes aceitos (target=3, não atinge)
        movies_phase1 = {1: _make_movie(1), 2: _make_movie(2)}
        candidates_phase1 = [(1, 100), (2, 99)]
        cfg = {**_CFG, "snapshot": {**_CFG["snapshot"], "target_size": 3}}

        result1 = self._run_with_mock(
            candidates_phase1, movies_phase1,
            cfg=cfg, checkpoint_dir=ckpt_dir, data_dir=data_dir,
        )
        assert result1.accepted == 2

        # Segunda execução (retomada): mesmos candidatos + novos
        movies_phase2 = {
            1: _make_movie(1), 2: _make_movie(2),
            3: _make_movie(3), 4: _make_movie(4),
        }
        candidates_all = [(1, 100), (2, 99), (3, 98), (4, 97)]

        result2 = self._run_with_mock(
            candidates_all, movies_phase2,
            cfg=cfg, checkpoint_dir=ckpt_dir, data_dir=data_dir,
        )

        assert result2.accepted == 3  # 2 do checkpoint + 1 novo
        assert result2.parquet_path is not None

    def test_fetches_target_size_then_filters(self, tmp_path):
        """Busca exatamente target_size candidatos e filtra depois."""
        movies = {}
        for i in range(1, 6):
            m = _make_movie(i)
            if i == 2:
                m["overview"] = ""  # será rejeitado
            movies[i] = m

        candidates = [(i, 100 - i) for i in range(1, 6)]
        cfg = {**_CFG, "snapshot": {**_CFG["snapshot"], "target_size": 3}}

        result = self._run_with_mock(
            candidates, movies,
            cfg=cfg,
            checkpoint_dir=tmp_path / "ckpt",
            data_dir=tmp_path / "data",
        )

        # target_size=3 → busca ids 1,2,3; id 2 rejeitado → 2 aceitos (não 3)
        assert result.accepted == 2
        assert result.rejected == 1

    def test_writes_meta_json(self, tmp_path):
        movies = {1: _make_movie(1)}
        candidates = [(1, 100)]
        cfg = {**_CFG, "snapshot": {**_CFG["snapshot"], "target_size": 1}}

        result = self._run_with_mock(
            candidates, movies,
            cfg=cfg,
            checkpoint_dir=tmp_path / "ckpt",
            data_dir=tmp_path / "data",
        )

        assert result.meta_path is not None
        with open(result.meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        assert meta["accepted"] == 1
        assert "snapshot_id" in meta
