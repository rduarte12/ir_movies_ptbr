"""Testes do contrato do serviço de busca (D-090).

Prova que o contrato de ``src/ir_movies/query/types.py`` é satisfazível e que a
implementação de referência (``tests/fakes.py``) obedece às cinco regras
documentadas em ``SearchServiceProtocol``.

O serviço real da Sprint 5 é conferido contra as mesmas regras nos testes da
própria trilha: é o que garante que a interface, construída contra o serviço
falso, funcione com o verdadeiro.
"""

import pytest

from ir_movies.query.types import (
    MAX_QUERY_CHARS,
    Movie,
    MovieHit,
    QueryLoggerProtocol,
    Rewriter,
    SearchResult,
    SearchServiceProtocol,
)
from tests.fakes import FakeSearchService, IdentityRewriterStub, MemoryQueryLogger

# Consultas com significado conhecido no corpus de brinquedo de 5 filmes.
QUERY_WITH_HITS = "robô apaixonado"
QUERY_ONLY_STOPWORDS = "o de a que"
QUERY_NOT_IN_CORPUS = "xyzzyx qwertyuiop"


@pytest.fixture
def service():
    return FakeSearchService.from_toy()


# --- Conformidade estrutural ---


class TestProtocolConformance:
    def test_service_satisfies_protocol(self, service):
        assert isinstance(service, SearchServiceProtocol)

    def test_rewriter_satisfies_protocol(self):
        assert isinstance(IdentityRewriterStub(), Rewriter)

    def test_logger_satisfies_protocol(self):
        assert isinstance(MemoryQueryLogger(), QueryLoggerProtocol)

    def test_protocol_rejects_unrelated_object(self):
        assert not isinstance(object(), SearchServiceProtocol)

    def test_search_returns_declared_types(self, service):
        result = service.search(QUERY_WITH_HITS)
        assert isinstance(result, SearchResult)
        assert all(isinstance(h, MovieHit) for h in result.hits)
        assert isinstance(service.get_movie(result.hits[0].movie_id), Movie)

    def test_identity_rewriter_name_goes_to_log(self):
        assert IdentityRewriterStub().name == "identity"


# --- Regra 1: consulta ruim não levanta exceção ---


class TestRuleOneNeverRaises:
    def test_empty_query(self, service):
        result = service.search("")
        assert result.hits == []
        assert result.trace.original_tokens == []

    def test_whitespace_query(self, service):
        assert service.search("   ").hits == []

    def test_only_stopwords_distinguishable_from_empty(self, service):
        """A interface precisa separar 'não escreveu nada' de 'só palavras
        comuns' (ui_spec.md secao 2), e o trace é o que permite isso."""
        result = service.search(QUERY_ONLY_STOPWORDS)
        assert result.hits == []
        assert result.trace.stopped != []
        assert result.trace.stems == []

    def test_no_word_in_corpus_is_reported_as_oov(self, service):
        result = service.search(QUERY_NOT_IN_CORPUS)
        assert result.hits == []
        assert result.oov_terms != []

    def test_punctuation_only(self, service):
        assert service.search("!!! ??? ...").hits == []


# --- Regra 2: truncagem ---


class TestRuleTwoTruncates:
    def test_long_query_is_truncated(self, service):
        result = service.search("robô " * 200)
        assert len(result.raw_query) == MAX_QUERY_CHARS

    def test_query_at_limit_is_untouched(self, service):
        query = "a" * MAX_QUERY_CHARS
        assert service.search(query).raw_query == query


# --- Regra 3: soma das contribuições = pontuação ---


class TestRuleThreeContributionsSumToScore:
    def test_every_hit_decomposes_exactly(self, service):
        result = service.search(QUERY_WITH_HITS)
        assert result.hits, "a consulta de referência precisa ter resultados"
        for hit in result.hits:
            parts = service.contributions(result.effective_query, hit.doc_id)
            assert sum(p.contribution for p in parts) == pytest.approx(hit.score, abs=1e-9)

    def test_contributions_carry_surface_forms_for_the_screen(self, service):
        result = service.search(QUERY_WITH_HITS)
        parts = service.contributions(result.effective_query, result.hits[0].doc_id)
        assert parts
        assert all(p.surface_forms for p in parts)


# --- Regra 4: log só quando pedido ---


class TestRuleFourLogging:
    def test_search_without_session_does_not_log(self, service):
        service.search(QUERY_WITH_HITS)
        assert service.logger.events == []

    def test_search_with_session_logs_one_event(self, service):
        service.search(QUERY_WITH_HITS, session_id="s1")
        assert [e.event for e in service.logger.events] == ["search"]

    def test_click_always_logs(self, service):
        service.log_click("s1", movie_id=1, rank=3)
        event = service.logger.events[0]
        assert event.event == "click"
        assert event.fields == {"movie_id": 1, "rank": 3}

    def test_events_accumulate_in_order(self, service):
        service.search(QUERY_WITH_HITS, session_id="s1")
        service.log_click("s1", movie_id=1, rank=1)
        assert [e.event for e in service.logger.events] == ["search", "click"]


# --- Regra 5: determinismo ---


class TestRuleFiveDeterminism:
    def test_same_query_same_ranking(self, service):
        first = service.search(QUERY_WITH_HITS)
        second = service.search(QUERY_WITH_HITS)
        assert [(h.movie_id, h.rank, h.score) for h in first.hits] == [
            (h.movie_id, h.rank, h.score) for h in second.hits
        ]

    def test_two_services_agree(self):
        a = FakeSearchService.from_toy().search(QUERY_WITH_HITS)
        b = FakeSearchService.from_toy().search(QUERY_WITH_HITS)
        assert [h.movie_id for h in a.hits] == [h.movie_id for h in b.hits]


# --- Forma dos resultados ---


class TestResultShape:
    def test_rank_is_one_based_and_consecutive(self, service):
        result = service.search(QUERY_WITH_HITS)
        assert [h.rank for h in result.hits] == list(range(1, len(result.hits) + 1))

    def test_scores_are_descending_without_semantic(self, service):
        """Hits ordenados por score TF-IDF decrescente quando semântica inativa (D-096)."""
        assert not service.semantic_active, "fixture deve ter semântica inativa"
        scores = [h.score for h in service.search(QUERY_WITH_HITS).hits]
        assert scores == sorted(scores, reverse=True)

    def test_k_limits_results(self, service):
        assert len(service.search("robô tubarão espaço chuva ilha", k=2).hits) <= 2

    def test_k_none_uses_service_default(self):
        svc = FakeSearchService.from_toy(top_k=1)
        assert len(svc.search("robô tubarão espaço chuva ilha").hits) == 1

    def test_effective_query_equals_raw_in_v1(self, service):
        result = service.search(QUERY_WITH_HITS)
        assert result.effective_query == result.raw_query

    def test_snapshot_id_and_app_version_are_reported(self, service):
        assert service.snapshot_id
        assert service.app_version

    def test_semantic_active_is_bool(self, service):
        assert isinstance(service.semantic_active, bool)

    def test_semantic_active_false_by_default(self, service):
        assert service.semantic_active is False
        assert service.search(QUERY_WITH_HITS).snapshot_id == service.snapshot_id

    def test_latency_is_measured(self, service):
        assert service.search(QUERY_WITH_HITS).latency_ms > 0


# --- Dados de exibição ---


class TestMovieData:
    def test_unknown_movie_raises_key_error(self, service):
        with pytest.raises(KeyError):
            service.get_movie(999999)

    def test_year_comes_from_release_date(self):
        movie = FakeSearchService.from_toy().get_movie(1)
        assert movie.year == movie.release_date[:4]

    def test_year_is_empty_when_release_date_is_empty(self):
        movie = FakeSearchService.from_toy().get_movie(1)
        assert type(movie)(**{**movie.__dict__, "release_date": ""}).year == ""

    def test_missing_poster_is_none_not_empty_string(self, service):
        """A interface decide o placeholder por ``is None``; '' passaria batido."""
        assert service.get_movie(5).poster_path is None

    def test_missing_runtime_is_none(self, service):
        assert service.get_movie(5).runtime is None

    def test_edge_cases_exist_in_the_toy_corpus(self, service):
        """Se o corpus de brinquedo deixar de ter esses casos, a interface perde
        a cobertura dos estados de ui_spec.md secao 2 sem nenhum teste falhar."""
        movies = [service.get_movie(i) for i in range(1, 6)]
        assert any(m.poster_path is None for m in movies)
        assert any(m.runtime is None for m in movies)
        assert any(not m.tagline for m in movies)
