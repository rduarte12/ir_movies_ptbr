"""Testes para ir_movies.collect.snapshot."""

import json
from collections import Counter
from pathlib import Path

import pandas as pd
import pytest

from ir_movies.collect.snapshot import _extract_row, validate_snapshot, write_snapshot

FIXTURES_DIR = Path(__file__).parent / "fixtures"

_CFG = {
    "snapshot": {
        "min_overview_words": 5,
        "min_vote_count": 2,
        "exclude_adult": True,
    }
}


def _load_fixture_278() -> dict:
    with open(FIXTURES_DIR / "movie_278.json", encoding="utf-8") as f:
        return json.load(f)


class TestExtractRow:
    def test_extracts_all_columns(self):
        raw = _load_fixture_278()
        row = _extract_row(raw)
        assert row["id"] == 278
        assert row["title"] == "Um Sonho de Liberdade"
        assert row["original_title"] == "The Shawshank Redemption"
        assert "Drama" in row["genres"]
        assert "Crime" in row["genres"]
        assert isinstance(row["keywords"], list)
        assert len(row["cast_top5"]) <= 5
        assert row["director"] != ""
        assert row["vote_count"] >= 2
        assert row["poster_path"] is not None

    def test_handles_missing_credits(self):
        raw = _load_fixture_278()
        del raw["credits"]
        row = _extract_row(raw)
        assert row["cast_top5"] == []
        assert row["director"] == ""

    def test_handles_missing_keywords(self):
        raw = _load_fixture_278()
        del raw["keywords"]
        row = _extract_row(raw)
        assert row["keywords"] == []

    def test_handles_null_poster(self):
        raw = _load_fixture_278()
        raw["poster_path"] = None
        row = _extract_row(raw)
        assert row["poster_path"] is None

    def test_handles_empty_tagline(self):
        raw = _load_fixture_278()
        raw["tagline"] = None
        row = _extract_row(raw)
        assert row["tagline"] == ""


class TestValidateSnapshot:
    def _make_df(self, **overrides):
        raw = _load_fixture_278()
        row = _extract_row(raw)
        row.update(overrides)
        return pd.DataFrame([row])

    def test_valid_snapshot_no_errors(self):
        df = self._make_df()
        errors = validate_snapshot(df, _CFG)
        assert errors == []

    def test_detects_duplicate_ids(self):
        raw = _load_fixture_278()
        row = _extract_row(raw)
        df = pd.DataFrame([row, row])
        errors = validate_snapshot(df, _CFG)
        assert any("duplicados" in e for e in errors)

    def test_detects_null_overview(self):
        df = self._make_df(overview=None)
        errors = validate_snapshot(df, _CFG)
        assert any("overview" in e.lower() or "nulos" in e for e in errors)

    def test_detects_short_overview(self):
        df = self._make_df(overview="Só três palavras")
        errors = validate_snapshot(df, _CFG)
        assert any("sinopses" in e for e in errors)

    def test_detects_low_votes(self):
        df = self._make_df(vote_count=1)
        errors = validate_snapshot(df, _CFG)
        assert any("vote_count" in e for e in errors)


class TestWriteSnapshot:
    def test_writes_parquet_and_meta(self, tmp_path):
        raw = _load_fixture_278()
        rejection_counts = Counter({"no_overview": 5, "low_votes": 3})

        parquet_path, meta_path = write_snapshot(
            [raw], _CFG, rejection_counts, n_candidates=9, dest_dir=tmp_path
        )

        assert parquet_path.exists()
        assert meta_path.exists()
        assert parquet_path.suffix == ".parquet"
        assert meta_path.name == "snapshot_meta.json"

        df = pd.read_parquet(parquet_path)
        assert len(df) == 1
        assert df.iloc[0]["id"] == 278

        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        assert meta["accepted"] == 1
        assert meta["candidates_tested"] == 9
        assert meta["rejections_by_reason"]["no_overview"] == 5
        assert "file_size_bytes" in meta
        assert meta["overview_word_count"]["min"] > 0

    def test_raises_on_invalid_data(self, tmp_path):
        raw = _load_fixture_278()
        raw["vote_count"] = 0
        with pytest.raises(ValueError, match="Validações"):
            write_snapshot([raw], _CFG, Counter(), n_candidates=1, dest_dir=tmp_path)
