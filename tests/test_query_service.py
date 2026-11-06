"""Testes do SearchService real (Sprint 5, D-036, D-090).

Duas famílias de fixture: o corpus de brinquedo (rápido, com o serviço falso de
``tests/fakes.py`` como referência) e o snapshot real (8.002 filmes, montado uma vez por
módulo). O log sempre vai para ``tmp_path``: nunca para o ``logs/`` do repositório.
"""

import copy
import json
import time
from datetime import UTC, datetime

import pytest

import ir_movies
from ir_movies.config import load_config
from ir_movies.logging_jsonl import QueryLogger
from ir_movies.query.rewriter import IdentityRewriter
from ir_movies.query.service import SearchService
from ir_movies.query.snapshot_loader import DEFAULT_DATA_DIR, LoadedSnapshot
from ir_movies.query.types import (
    MAX_QUERY_CHARS,
    MovieHit,
    SearchResult,
    SearchServiceProtocol,
)
from tests.fakes import FakeSearchService

# As regras do contrato (test_contract.py) valem para o serviço real tal como para o
# falso: as classes abaixo são reaproveitadas, rodando contra a fixture `service` daqui.
from tests.test_contract import (  # noqa: F401
    TestMovieData,
    TestRuleFiveDeterminism,
    TestRuleOneNeverRaises,
    TestRuleThreeContributionsSumToScore,
    TestRuleTwoTruncates,
)

QUERY_WITH_HITS = "robô apaixonado"

# Conjuntos de chaves de architecture.md secao 5, escritos à mão de propósito.
SEARCH_LOG_KEYS = {
    "event",
    "ts",
    "session_id",
    "app_version",
    "snapshot_id",
    "model",
    "rewriter",
    "raw_query",
    "effective_query",
    "n_query_tokens",
    "n_oov_tokens",
    "n_results",
    "top_ids",
    "latency_ms",
}
CLICK_LOG_KEYS = {
    "event",
    "ts",
    "session_id",
    "app_version",
    "snapshot_id",
    "model",
    "rewriter",
    "movie_id",
    "rank",
}


def make_cfg(log_dir, *, enabled=True, top_k=5):
    cfg = copy.deepcopy(load_config())
    cfg["logging"] = {"dir": str(log_dir), "enabled": enabled}
    cfg["search"] = {"top_k": top_k}
    return cfg


def toy_snapshot():
    fake = FakeSearchService.from_toy()
    return LoadedSnapshot.from_movies("toy-00000000", [fake.get_movie(i) for i in range(1, 6)])


def build_toy(tmp_path, **cfg_kwargs):
    return SearchService(toy_snapshot(), make_cfg(tmp_path / "logs", **cfg_kwargs))


def read_log(tmp_path):
    files = sorted((tmp_path / "logs").glob("queries-*.jsonl"))
    assert len(files) == 1, files
    return [json.loads(x) for x in files[0].read_text(encoding="utf-8").splitlines()]


@pytest.fixture
def service(tmp_path):
    return build_toy(tmp_path)


@pytest.fixture(scope="module")
def real(tmp_path_factory):
    """Serviço sobre o snapshot real, pelo caminho de produção (``from_config``)."""
    log_dir = tmp_path_factory.mktemp("real_logs")
    logger = QueryLogger(log_dir, app_version="test", snapshot_id="real")
    return SearchService.from_config(logger=logger)


# --- A12: conformidade com o contrato e com o serviço falso ---


class TestConformsToContract:
    def test_is_a_search_service(self, service):
        assert isinstance(service, SearchServiceProtocol)

    def test_real_service_is_a_search_service(self, real):
        assert isinstance(real, SearchServiceProtocol)

    @pytest.mark.parametrize(
        "query",
        [
            "robô apaixonado",
            "tubarão praia",
            "viagem espaço",
            "robô tubarão espaço chuva ilha",
            "chuva",
            "o de a que",
            "xyzzyx qwertyuiop",
            "",
        ],
    )
    def test_agrees_with_fake_service(self, tmp_path, query):
        real_svc = build_toy(tmp_path)
        fake = FakeSearchService.from_toy(top_k=5)

        got = real_svc.search(query)
        want = fake.search(query)

        assert [h.movie_id for h in got.hits] == [h.movie_id for h in want.hits]
        assert [h.rank for h in got.hits] == [h.rank for h in want.hits]
        assert [h.doc_id for h in got.hits] == [h.doc_id for h in want.hits]
        assert [h.score for h in got.hits] == pytest.approx(
            [h.score for h in want.hits], abs=1e-12
        )
        assert got.oov_terms == want.oov_terms
        assert got.trace == want.trace
        assert got.raw_query == want.raw_query
        assert got.effective_query == want.effective_query

    def test_agreement_is_not_vacuous(self, tmp_path):
        """Garante que a comparação acima compara listas de verdade."""
        assert len(build_toy(tmp_path).search("robô tubarão espaço chuva ilha").hits) >= 3

    def test_contributions_agree_with_fake(self, tmp_path):
        real_svc = build_toy(tmp_path)
        fake = FakeSearchService.from_toy()
        for doc_id in range(5):
            got = real_svc.contributions(QUERY_WITH_HITS, doc_id)
            want = fake.contributions(QUERY_WITH_HITS, doc_id)
            assert [(c.stem, c.surface_forms) for c in got] == [
                (c.stem, c.surface_forms) for c in want
            ]
            assert [c.contribution for c in got] == pytest.approx([c.contribution for c in want])

    def test_get_movie_agrees_with_fake(self, tmp_path):
        real_svc = build_toy(tmp_path)
        fake = FakeSearchService.from_toy()
        for movie_id in range(1, 6):
            assert real_svc.get_movie(movie_id) == fake.get_movie(movie_id)

    def test_returns_declared_types(self, service):
        result = service.search(QUERY_WITH_HITS)
        assert isinstance(result, SearchResult)
        assert result.hits and all(isinstance(h, MovieHit) for h in result.hits)


# --- Regra 4 do contrato e A1 a A4: log de ponta a ponta ---


class TestEndToEndLogging:
    def test_search_with_session_writes_exactly_one_line_dated_today(self, tmp_path, service):
        before = datetime.now(UTC).strftime("%Y-%m-%d")
        result = service.search(QUERY_WITH_HITS, session_id="s1")
        after = datetime.now(UTC).strftime("%Y-%m-%d")

        assert result.hits
        names = [p.name for p in (tmp_path / "logs").iterdir()]
        assert len(names) == 1
        assert names[0] in {f"queries-{before}.jsonl", f"queries-{after}.jsonl"}
        (line,) = read_log(tmp_path)
        assert line["event"] == "search"
        assert line["session_id"] == "s1"

    def test_search_without_session_writes_nothing(self, tmp_path, service):
        service.search(QUERY_WITH_HITS)
        assert not (tmp_path / "logs").exists()

    def test_each_search_adds_one_line(self, tmp_path, service):
        for i in range(3):
            service.search(QUERY_WITH_HITS, session_id=f"s{i}")
        assert len(read_log(tmp_path)) == 3

    def test_search_line_keys_equal_the_schema(self, tmp_path, service):
        service.search(QUERY_WITH_HITS, session_id="s1")
        (line,) = read_log(tmp_path)
        assert set(line) == SEARCH_LOG_KEYS

    def test_click_line_keys_equal_the_schema(self, tmp_path, service):
        service.log_click("s1", movie_id=3, rank=2)
        (line,) = read_log(tmp_path)
        assert set(line) == CLICK_LOG_KEYS

    def test_log_line_reflects_the_result(self, tmp_path, service):
        result = service.search(QUERY_WITH_HITS, session_id="s1")
        (line,) = read_log(tmp_path)
        assert line["raw_query"] == result.raw_query
        assert line["effective_query"] == result.effective_query
        assert line["n_results"] == len(result.hits)
        assert line["top_ids"] == [h.movie_id for h in result.hits]
        assert line["n_oov_tokens"] == len(result.oov_terms)
        assert line["n_query_tokens"] == len(set(result.trace.stems))
        assert line["latency_ms"] == result.latency_ms
        assert line["snapshot_id"] == service.snapshot_id == "toy-00000000"
        assert line["app_version"] == service.app_version == ir_movies.__version__
        assert line["model"] == "tfidf"
        assert line["rewriter"] == "identity"

    def test_log_has_no_personal_data(self, tmp_path, service):
        service.search(QUERY_WITH_HITS, session_id="s1")
        service.log_click("s1", 1, 1)
        for line in read_log(tmp_path):
            for key in line:
                assert not any(bad in key for bad in ("ip", "user_agent", "host", "email")), key
            assert not {"ip", "user_agent", "host", "email"} & {
                w for v in line.values() for w in str(v).lower().replace(".", " ").split()
            }

    def test_click_appends_and_keeps_previous_line(self, tmp_path, service):
        service.search(QUERY_WITH_HITS, session_id="s1")
        log_file = next((tmp_path / "logs").glob("queries-*.jsonl"))
        before = log_file.read_bytes()

        service.log_click("s1", movie_id=1, rank=2)

        after = log_file.read_bytes()
        assert after.startswith(before)
        lines = read_log(tmp_path)
        assert [x["event"] for x in lines] == ["search", "click"]
        assert lines[1]["movie_id"] == 1
        assert lines[1]["rank"] == 2
        assert lines[1]["session_id"] == "s1"
        assert json.loads(before.decode("utf-8").splitlines()[0]) == lines[0]

    def test_click_without_search_still_logs(self, tmp_path, service):
        service.log_click("s9", movie_id=5, rank=1)
        assert [x["event"] for x in read_log(tmp_path)] == ["click"]


class TestLoggingDisabled:
    def test_no_file_and_no_directory(self, tmp_path):
        service = build_toy(tmp_path, enabled=False)
        result = service.search(QUERY_WITH_HITS, session_id="s1")
        service.log_click("s1", 1, 1)
        assert result.hits  # a busca funciona normalmente
        assert not (tmp_path / "logs").exists()
        assert list(tmp_path.iterdir()) == []


# --- A5 a A10: comportamento da busca ---


class TestScoreDecomposition:
    QUERIES = [
        "batman cavaleiro das trevas",
        "robô apaixonado",
        "tubarão",
        "guerra mundial soldados",
        "comédia romântica em paris",
    ]

    @pytest.mark.parametrize("query", QUERIES)
    def test_contributions_sum_to_score_on_real_snapshot(self, real, query):
        result = real.search(query, k=20)
        assert len(result.hits) >= 10, "consulta precisa ter resultados para o teste valer"
        for hit in result.hits:
            parts = real.contributions(result.effective_query, hit.doc_id)
            assert sum(p.contribution for p in parts) == pytest.approx(hit.score, abs=1e-9)


class TestDeterminism:
    def test_same_query_same_ids_in_same_order_on_real_snapshot(self, real):
        first = real.search("batman cavaleiro das trevas", k=20)
        second = real.search("batman cavaleiro das trevas", k=20)
        assert [h.movie_id for h in first.hits] == [h.movie_id for h in second.hits]
        assert [h.score for h in first.hits] == [h.score for h in second.hits]
        assert len(first.hits) == 20

    def test_independent_instances_agree(self, tmp_path):
        a = build_toy(tmp_path).search("robô tubarão espaço chuva ilha")
        b = build_toy(tmp_path).search("robô tubarão espaço chuva ilha")
        assert [h.movie_id for h in a.hits] == [h.movie_id for h in b.hits]


class TestRealSnapshotMapping:
    def test_hit_movie_id_comes_from_doc_position_not_equal_to_it(self, real):
        """Na coleção real o id TMDB difere da posição; o mapeamento tem de ser feito."""
        result = real.search("batman cavaleiro das trevas", k=3)
        assert any(h.movie_id != h.doc_id for h in result.hits)
        for hit in result.hits:
            assert real.get_movie(hit.movie_id).id == hit.movie_id
        assert "Batman" in real.get_movie(result.hits[0].movie_id).title

    def test_known_title_is_found_in_top_results(self, real):
        result = real.search("tubarão", k=10)
        titles = [real.get_movie(h.movie_id).title for h in result.hits]
        assert any("Tubarão" in t for t in titles)

    def test_unknown_movie_raises_key_error(self, real):
        with pytest.raises(KeyError):
            real.get_movie(-1)


class TestEmptyAndUnmatchedQueries:
    """A interface distingue os três casos pelo ``trace`` e por ``oov_terms``."""

    def test_empty_query(self, real):
        result = real.search("")
        assert result.hits == []
        assert result.trace.original_tokens == []
        assert result.trace.stopped == []
        assert result.trace.stems == []
        assert result.oov_terms == []

    def test_only_common_words(self, real):
        result = real.search("o de a que")
        assert result.hits == []
        assert result.trace.original_tokens == ["o", "de", "a", "que"]
        assert result.trace.stopped == ["o", "de", "a", "que"]
        assert result.trace.stems == []
        assert result.oov_terms == []

    def test_no_word_in_the_collection(self, real):
        result = real.search("xyzzyx qwertyuiop")
        assert result.hits == []
        assert result.oov_terms == ["xyzzyx", "qwertyuiop"]
        assert result.trace.stems == ["xyzzyx", "qwertyuiop"]
        assert result.trace.stopped == []

    def test_partly_unknown_query_still_finds_and_reports_oov(self, real):
        result = real.search("tubarão xyzzyx")
        assert result.hits
        assert result.oov_terms == ["xyzzyx"]

    def test_none_is_treated_as_empty(self, real):
        result = real.search(None)
        assert result.hits == []
        assert result.raw_query == ""

    def test_unmatched_search_is_logged_with_zero_results(self, tmp_path, service):
        service.search("xyzzyx qwertyuiop", session_id="s1")
        (line,) = read_log(tmp_path)
        assert line["n_results"] == 0
        assert line["top_ids"] == []
        assert line["n_oov_tokens"] == 2
        assert line["n_query_tokens"] == 2


class TestTopK:
    def test_none_uses_configured_top_k(self, tmp_path):
        result = build_toy(tmp_path, top_k=2).search("robô tubarão espaço chuva ilha")
        assert len(result.hits) == 2

    def test_none_uses_config_value_not_a_constant(self, tmp_path):
        a = build_toy(tmp_path, top_k=1).search("robô tubarão espaço chuva ilha")
        b = build_toy(tmp_path, top_k=4).search("robô tubarão espaço chuva ilha")
        assert (len(a.hits), len(b.hits)) == (1, 4)

    def test_explicit_k_overrides_config(self, tmp_path):
        service = build_toy(tmp_path, top_k=5)
        assert len(service.search("robô tubarão espaço chuva ilha", k=2).hits) == 2

    def test_never_more_than_k(self, real):
        for k in (1, 5, 20):
            assert len(real.search("amor", k=k).hits) <= k

    def test_k_larger_than_matches_returns_all_matches(self, tmp_path):
        service = build_toy(tmp_path, top_k=1)
        assert len(service.search("robô tubarão espaço chuva ilha", k=50).hits) == 5

    def test_k_zero_and_negative_give_empty_list(self, service):
        assert service.search(QUERY_WITH_HITS, k=0).hits == []
        assert service.search(QUERY_WITH_HITS, k=-3).hits == []

    def test_default_top_k_from_the_real_config_is_20(self, real):
        assert len(real.search("amor").hits) == load_config()["search"]["top_k"] == 20


class TestTruncation:
    def test_500_chars_become_300_without_error(self, service):
        query = ("robô apaixonado " * 40)[:500]
        assert len(query) == 500
        result = service.search(query)
        assert len(result.raw_query) == MAX_QUERY_CHARS == 300
        assert result.raw_query == query[:300]
        assert result.effective_query == query[:300]

    def test_truncated_query_is_what_gets_logged(self, tmp_path, service):
        query = "robô " * 100
        service.search(query, session_id="s1")
        (line,) = read_log(tmp_path)
        assert line["raw_query"] == query[:300]
        assert len(line["effective_query"]) == 300

    def test_truncation_on_real_snapshot(self, real):
        result = real.search("a" * 500)
        assert len(result.raw_query) == 300


# --- A11: snapshot real ---


class TestRealSnapshotLoading:
    def test_service_loads_the_snapshot_named_in_the_meta(self, real):
        with open(DEFAULT_DATA_DIR / "snapshot_meta.json", encoding="utf-8") as f:
            meta = json.load(f)
        assert real.snapshot_id == meta["snapshot_id"]
        assert real.search("amor").snapshot_id == meta["snapshot_id"]
        assert len(real._movies) == meta["accepted"] == 8002

    def test_app_version_comes_from_package(self, real):
        assert real.app_version == ir_movies.__version__


# --- Latência, reescritor e montagem ---


class _SlowLogger:
    """Logger que demora de propósito: a latência da busca não pode incluí-lo."""

    delay = 0.3

    def __init__(self):
        self.calls = 0

    def log_search(self, result, session_id):
        self.calls += 1
        time.sleep(self.delay)

    def log_click(self, session_id, movie_id, rank):
        pass


class _ShoutRewriter:
    name = "shout"

    def rewrite(self, raw):
        return raw + " tubarão"


class TestLatency:
    def test_is_positive(self, service):
        assert service.search(QUERY_WITH_HITS).latency_ms > 0

    def test_excludes_the_log_write(self, tmp_path):
        slow = _SlowLogger()
        service = SearchService(toy_snapshot(), make_cfg(tmp_path / "logs"), logger=slow)
        started = time.perf_counter()
        result = service.search(QUERY_WITH_HITS, session_id="s1")
        total_ms = (time.perf_counter() - started) * 1000

        assert slow.calls == 1
        assert total_ms >= _SlowLogger.delay * 1000  # o log demorou de fato
        assert result.latency_ms < _SlowLogger.delay * 1000 / 2

    def test_logged_latency_is_the_result_latency(self, tmp_path, service):
        result = service.search(QUERY_WITH_HITS, session_id="s1")
        (line,) = read_log(tmp_path)
        assert line["latency_ms"] == result.latency_ms


class TestRewriterWiring:
    def test_default_rewriter_is_identity(self, service):
        result = service.search(QUERY_WITH_HITS)
        assert result.effective_query == result.raw_query == QUERY_WITH_HITS
        assert isinstance(service._rewriter, IdentityRewriter)

    def test_custom_rewriter_changes_effective_query_not_raw(self, tmp_path):
        service = SearchService(
            toy_snapshot(), make_cfg(tmp_path / "logs"), rewriter=_ShoutRewriter()
        )
        result = service.search("praia", session_id="s1")
        assert result.raw_query == "praia"
        assert result.effective_query == "praia tubarão"
        assert result.trace.original_tokens == ["praia", "tubarao"]
        (line,) = read_log(tmp_path)
        assert line["rewriter"] == "shout"
        assert line["raw_query"] == "praia"
        assert line["effective_query"] == "praia tubarão"

    def test_explicit_app_version_overrides_package_version(self, tmp_path):
        service = SearchService(
            toy_snapshot(), make_cfg(tmp_path / "logs"), app_version="9.9.9-test"
        )
        assert service.app_version == "9.9.9-test"
        service.search(QUERY_WITH_HITS, session_id="s1")
        assert read_log(tmp_path)[0]["app_version"] == "9.9.9-test"
