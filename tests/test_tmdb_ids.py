"""Testes para ir_movies.tmdb.ids (sem rede)."""

from pathlib import Path

from ir_movies.tmdb.ids import load_candidates

FIXTURES_DIR = Path(__file__).parent / "fixtures"
EXPORT_SAMPLE = FIXTURES_DIR / "export_sample.jsonl.gz"


def test_load_candidates_filters_adult():
    """Entradas com adult=True são excluídas por padrão."""
    candidates = load_candidates(EXPORT_SAMPLE)
    ids = {c[0] for c in candidates}
    assert 99999 not in ids
    assert 88888 not in ids
    assert len(candidates) == 4


def test_load_candidates_include_adult():
    """Com exclude_adult=False, retorna todos (6 entradas)."""
    candidates = load_candidates(EXPORT_SAMPLE, exclude_adult=False)
    assert len(candidates) == 6


def test_load_candidates_sorted_by_popularity():
    """Ordenação decrescente por popularidade."""
    candidates = load_candidates(EXPORT_SAMPLE)
    popularities = [c[1] for c in candidates]
    assert popularities == sorted(popularities, reverse=True)


def test_load_candidates_returns_tuples():
    """Cada elemento é (int, float)."""
    candidates = load_candidates(EXPORT_SAMPLE)
    for movie_id, popularity in candidates:
        assert isinstance(movie_id, int)
        assert isinstance(popularity, float)


def test_load_candidates_first_is_most_popular():
    """O primeiro candidato deve ser o de maior popularidade (278, Shawshank)."""
    candidates = load_candidates(EXPORT_SAMPLE)
    assert candidates[0] == (278, 152.805)


def test_load_candidates_stable_tiebreak():
    """Empates em popularidade usam id crescente como desempate."""
    candidates = load_candidates(EXPORT_SAMPLE)
    for i in range(len(candidates) - 1):
        pop_a, id_a = candidates[i][1], candidates[i][0]
        pop_b, id_b = candidates[i + 1][1], candidates[i + 1][0]
        if pop_a == pop_b:
            assert id_a < id_b
