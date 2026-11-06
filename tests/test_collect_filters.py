"""Testes para ir_movies.collect.filters."""

import json
from pathlib import Path

from ir_movies.collect.filters import evaluate

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


class TestAccepted:
    def test_fixture_278_accepted(self):
        """Filme 278 (Shawshank) passa em todos os filtros."""
        raw = _load_fixture_278()
        accepted, reason = evaluate(raw, _CFG)
        assert accepted is True
        assert reason is None


class TestAdultFilter:
    def test_rejects_adult(self):
        raw = _load_fixture_278()
        raw["adult"] = True
        accepted, reason = evaluate(raw, _CFG)
        assert accepted is False
        assert reason == "adult"

    def test_accepts_adult_when_disabled(self):
        raw = _load_fixture_278()
        raw["adult"] = True
        cfg = {"snapshot": {**_CFG["snapshot"], "exclude_adult": False}}
        accepted, reason = evaluate(raw, cfg)
        assert accepted is True


class TestOverviewFilter:
    def test_rejects_no_overview(self):
        raw = _load_fixture_278()
        raw["overview"] = ""
        accepted, reason = evaluate(raw, _CFG)
        assert accepted is False
        assert reason == "no_overview"

    def test_rejects_none_overview(self):
        raw = _load_fixture_278()
        raw["overview"] = None
        accepted, reason = evaluate(raw, _CFG)
        assert accepted is False
        assert reason == "no_overview"

    def test_rejects_whitespace_only(self):
        raw = _load_fixture_278()
        raw["overview"] = "   "
        accepted, reason = evaluate(raw, _CFG)
        assert accepted is False
        assert reason == "no_overview"

    def test_rejects_short_overview(self):
        raw = _load_fixture_278()
        raw["overview"] = "Apenas quatro palavras aqui"  # 4 palavras
        accepted, reason = evaluate(raw, _CFG)
        assert accepted is False
        assert reason == "short_overview"

    def test_accepts_exactly_min_words(self):
        raw = _load_fixture_278()
        raw["overview"] = "Uma dois três quatro cinco"  # 5 palavras
        accepted, reason = evaluate(raw, _CFG)
        assert accepted is True


class TestVoteCountFilter:
    def test_rejects_low_votes(self):
        raw = _load_fixture_278()
        raw["vote_count"] = 1
        accepted, reason = evaluate(raw, _CFG)
        assert accepted is False
        assert reason == "low_votes"

    def test_rejects_zero_votes(self):
        raw = _load_fixture_278()
        raw["vote_count"] = 0
        accepted, reason = evaluate(raw, _CFG)
        assert accepted is False
        assert reason == "low_votes"

    def test_accepts_exactly_min_votes(self):
        raw = _load_fixture_278()
        raw["vote_count"] = 2
        accepted, reason = evaluate(raw, _CFG)
        assert accepted is True


class TestFilterPriority:
    def test_adult_checked_first(self):
        """Se adulto e sem sinopse, o motivo deve ser 'adult'."""
        raw = _load_fixture_278()
        raw["adult"] = True
        raw["overview"] = ""
        accepted, reason = evaluate(raw, _CFG)
        assert reason == "adult"
