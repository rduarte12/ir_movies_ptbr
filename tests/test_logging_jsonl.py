"""Testes do QueryLogger (D-008, esquema de architecture.md secao 5)."""

import json
import logging
import re
import threading
from datetime import UTC, datetime, timedelta

import pytest

from ir_movies.logging_jsonl import MAX_TOP_IDS, QueryLogger, new_session_id
from ir_movies.query.types import MovieHit, QueryLoggerProtocol, SearchResult
from ir_movies.text.preprocess import PreprocessTrace

# Conjuntos de chaves de architecture.md secao 5, escritos à mão de propósito: se o
# código mudar o esquema, estes testes precisam falhar.
CONTEXT_KEYS = {"event", "ts", "session_id", "app_version", "snapshot_id", "model", "rewriter"}
SEARCH_KEYS = CONTEXT_KEYS | {
    "raw_query",
    "effective_query",
    "n_query_tokens",
    "n_oov_tokens",
    "n_results",
    "top_ids",
    "latency_ms",
}
CLICK_KEYS = CONTEXT_KEYS | {"movie_id", "rank"}

FIXED_NOW = datetime(2026, 11, 6, 14, 30, 5, 123000, tzinfo=UTC)


def make_result(
    n_hits=3, stems=("robo", "apaix", "robo"), oov=("xyzzyx",), query="robô apaixonado"
):
    trace = PreprocessTrace(
        original_tokens=["robo", "apaixonado", "robo"],
        stopped=[],
        stems=list(stems),
        stem_to_surface={},
    )
    hits = [
        MovieHit(movie_id=1000 + i, rank=i + 1, score=1.0 / (i + 1), doc_id=i)
        for i in range(n_hits)
    ]
    return SearchResult(
        raw_query=query,
        effective_query=query,
        trace=trace,
        hits=hits,
        oov_terms=list(oov),
        latency_ms=1.25,
        snapshot_id="20261106",
    )


def make_logger(tmp_path, **kwargs):
    kwargs.setdefault("clock", lambda: FIXED_NOW)
    return QueryLogger(tmp_path / "logs", app_version="9.9.9", snapshot_id="20261106", **kwargs)


def read_lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.fixture
def log_file(tmp_path):
    return tmp_path / "logs" / "queries-2026-11-06.jsonl"


class TestSchema:
    def test_search_line_has_exactly_the_documented_keys(self, tmp_path, log_file):
        make_logger(tmp_path).log_search(make_result(), "s1")
        (line,) = read_lines(log_file)
        assert set(line) == SEARCH_KEYS

    def test_click_line_has_exactly_the_documented_keys(self, tmp_path, log_file):
        make_logger(tmp_path).log_click("s1", movie_id=42, rank=3)
        (line,) = read_lines(log_file)
        assert set(line) == CLICK_KEYS

    def test_search_values(self, tmp_path, log_file):
        make_logger(tmp_path).log_search(make_result(), "s1")
        (line,) = read_lines(log_file)
        assert line["event"] == "search"
        assert line["session_id"] == "s1"
        assert line["app_version"] == "9.9.9"
        assert line["snapshot_id"] == "20261106"
        assert line["model"] == "tfidf"
        assert line["rewriter"] == "identity"
        assert line["raw_query"] == "robô apaixonado"
        assert line["effective_query"] == "robô apaixonado"
        assert line["n_results"] == 3
        assert line["top_ids"] == [1000, 1001, 1002]
        assert line["latency_ms"] == 1.25

    def test_click_values(self, tmp_path, log_file):
        make_logger(tmp_path).log_click("s1", movie_id=42, rank=3)
        (line,) = read_lines(log_file)
        assert line["event"] == "click"
        assert line["movie_id"] == 42
        assert line["rank"] == 3
        assert line["model"] == "tfidf"

    def test_query_tokens_count_distinct_stems(self, tmp_path, log_file):
        """stems = [robo, apaix, robo] -> 2 radicais distintos; 1 fora do acervo."""
        make_logger(tmp_path).log_search(make_result(), "s1")
        (line,) = read_lines(log_file)
        assert line["n_query_tokens"] == 2
        assert line["n_oov_tokens"] == 1

    def test_ts_is_utc_iso8601(self, tmp_path, log_file):
        make_logger(tmp_path).log_search(make_result(), "s1")
        (line,) = read_lines(log_file)
        assert line["ts"] == "2026-11-06T14:30:05.123+00:00"
        assert datetime.fromisoformat(line["ts"]).utcoffset() == timedelta(0)

    def test_empty_result_is_logged_with_empty_top_ids(self, tmp_path, log_file):
        result = make_result(n_hits=0, stems=(), oov=(), query="")
        make_logger(tmp_path).log_search(result, "s1")
        (line,) = read_lines(log_file)
        assert line["n_results"] == 0
        assert line["top_ids"] == []
        assert line["n_query_tokens"] == 0


class TestTopIds:
    def test_top_ids_truncated_at_ten(self, tmp_path, log_file):
        assert MAX_TOP_IDS == 10
        make_logger(tmp_path).log_search(make_result(n_hits=15), "s1")
        (line,) = read_lines(log_file)
        assert line["top_ids"] == [1000 + i for i in range(10)]

    def test_n_results_counts_all_hits_not_only_logged_ones(self, tmp_path, log_file):
        make_logger(tmp_path).log_search(make_result(n_hits=15), "s1")
        (line,) = read_lines(log_file)
        assert line["n_results"] == 15

    def test_fewer_than_ten_hits_are_all_kept(self, tmp_path, log_file):
        make_logger(tmp_path).log_search(make_result(n_hits=4), "s1")
        (line,) = read_lines(log_file)
        assert len(line["top_ids"]) == 4


class TestFileLayout:
    def test_one_line_per_event(self, tmp_path, log_file):
        logger = make_logger(tmp_path)
        logger.log_search(make_result(), "s1")
        logger.log_click("s1", 1000, 1)
        logger.log_search(make_result(), "s2")
        assert [x["event"] for x in read_lines(log_file)] == ["search", "click", "search"]

    def test_appends_across_logger_instances(self, tmp_path, log_file):
        make_logger(tmp_path).log_search(make_result(), "s1")
        before = log_file.read_text(encoding="utf-8")
        make_logger(tmp_path).log_click("s1", 1000, 1)
        after = log_file.read_text(encoding="utf-8")
        assert after.startswith(before)
        assert len(after.splitlines()) == 2

    def test_one_file_per_day(self, tmp_path):
        now = [FIXED_NOW]
        logger = make_logger(tmp_path, clock=lambda: now[0])
        logger.log_click("s1", 1, 1)
        now[0] = FIXED_NOW + timedelta(days=1)
        logger.log_click("s1", 2, 1)
        names = sorted(p.name for p in (tmp_path / "logs").iterdir())
        assert names == ["queries-2026-11-06.jsonl", "queries-2026-11-07.jsonl"]

    def test_file_date_follows_utc_instant_near_midnight(self, tmp_path):
        late = datetime(2026, 11, 6, 23, 59, 59, tzinfo=UTC)
        make_logger(tmp_path, clock=lambda: late).log_click("s1", 1, 1)
        assert (tmp_path / "logs" / "queries-2026-11-06.jsonl").exists()

    def test_creates_missing_directory(self, tmp_path):
        logger = QueryLogger(
            tmp_path / "a" / "b" / "logs",
            app_version="1",
            snapshot_id="x",
            clock=lambda: FIXED_NOW,
        )
        logger.log_click("s1", 1, 1)
        assert (tmp_path / "a" / "b" / "logs" / "queries-2026-11-06.jsonl").exists()

    def test_utf8_without_ascii_escaping(self, tmp_path, log_file):
        make_logger(tmp_path).log_search(make_result(query="ação e emoção"), "s1")
        raw = log_file.read_bytes()
        assert "ação e emoção".encode() in raw

    def test_line_endings_are_lf_only(self, tmp_path, log_file):
        logger = make_logger(tmp_path)
        logger.log_search(make_result(), "s1")
        logger.log_click("s1", 1, 1)
        raw = log_file.read_bytes()
        assert b"\r" not in raw
        assert raw.endswith(b"\n")
        assert raw.count(b"\n") == 2

    def test_default_clock_is_utc_in_ts_and_file_name(self, tmp_path):
        logger = QueryLogger(tmp_path / "logs", app_version="1", snapshot_id="x")
        before = datetime.now(UTC)
        logger.log_click("s1", 1, 1)
        after = datetime.now(UTC)

        (log_file,) = (tmp_path / "logs").glob("queries-*.jsonl")
        (line,) = read_lines(log_file)
        ts = datetime.fromisoformat(line["ts"])

        # O relógio padrão tem de ser UTC: um `ts` em hora local ficaria sem fuso
        # (naive) ou com deslocamento diferente de zero, e o nome do arquivo sozinho
        # coincide com a data UTC na maior parte do dia em qualquer fuso próximo.
        assert line["ts"].endswith("+00:00")
        assert ts.utcoffset() == timedelta(0)
        assert before - timedelta(milliseconds=1) <= ts <= after
        assert log_file.name == f"queries-{ts.strftime('%Y-%m-%d')}.jsonl"

    def test_concurrent_writes_stay_one_json_per_line(self, tmp_path, log_file):
        logger = make_logger(tmp_path)
        threads = [
            threading.Thread(target=logger.log_search, args=(make_result(), f"s{i}"))
            for i in range(40)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        lines = read_lines(log_file)
        assert len(lines) == 40
        assert {x["session_id"] for x in lines} == {f"s{i}" for i in range(40)}


class TestDisabled:
    def test_disabled_search_creates_nothing(self, tmp_path):
        make_logger(tmp_path, enabled=False).log_search(make_result(), "s1")
        assert not (tmp_path / "logs").exists()

    def test_disabled_click_creates_nothing(self, tmp_path):
        make_logger(tmp_path, enabled=False).log_click("s1", 1, 1)
        assert not (tmp_path / "logs").exists()

    def test_disabled_does_not_touch_existing_file(self, tmp_path, log_file):
        make_logger(tmp_path).log_click("s1", 1, 1)
        before = log_file.read_bytes()
        make_logger(tmp_path, enabled=False).log_click("s1", 2, 2)
        assert log_file.read_bytes() == before

    def test_from_config_honors_enabled_false(self, tmp_path):
        cfg = {"logging": {"dir": str(tmp_path / "logs"), "enabled": False}}
        logger = QueryLogger.from_config(cfg, app_version="1", snapshot_id="x")
        assert logger.enabled is False
        logger.log_click("s1", 1, 1)
        assert not (tmp_path / "logs").exists()

    def test_from_config_enabled_true_writes_to_configured_dir(self, tmp_path):
        cfg = {"logging": {"dir": str(tmp_path / "custom"), "enabled": True}}
        logger = QueryLogger.from_config(
            cfg, app_version="1", snapshot_id="x", clock=lambda: FIXED_NOW
        )
        logger.log_click("s1", 1, 1)
        assert (tmp_path / "custom" / "queries-2026-11-06.jsonl").exists()


class TestWriteFailure:
    def test_failure_is_a_warning_not_an_exception(self, tmp_path, caplog):
        blocker = tmp_path / "not_a_dir"
        blocker.write_text("arquivo no lugar do diretório", encoding="utf-8")
        logger = QueryLogger(
            blocker / "logs", app_version="1", snapshot_id="x", clock=lambda: FIXED_NOW
        )
        with caplog.at_level(logging.WARNING, logger="ir_movies.logging_jsonl"):
            logger.log_search(make_result(), "s1")
            logger.log_click("s1", 1, 1)
        assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 2


class TestPrivacy:
    FORBIDDEN = ("ip", "user_agent", "host", "email")

    def test_no_personal_key_or_value(self, tmp_path, log_file):
        logger = make_logger(tmp_path)
        logger.log_search(make_result(), new_session_id())
        logger.log_click(new_session_id(), 1000, 1)
        for line in read_lines(log_file):
            for key in line:
                assert not any(bad in key.lower() for bad in self.FORBIDDEN), key
            for value in line.values():
                words = re.findall(r"[a-z_]+", str(value).lower())
                assert not set(words) & set(self.FORBIDDEN), value

    def test_logger_has_no_way_to_receive_personal_data(self):
        """Assinaturas públicas: só campos do evento, nenhum de rede ou navegador."""
        import inspect

        for method in (QueryLogger.log_search, QueryLogger.log_click):
            params = set(inspect.signature(method).parameters) - {"self"}
            assert not any(bad in p for p in params for bad in self.FORBIDDEN)
        assert set(inspect.signature(QueryLogger.log_click).parameters) == {
            "self",
            "session_id",
            "movie_id",
            "rank",
        }


class TestSessionId:
    def test_format_is_16_hex_chars(self):
        assert re.fullmatch(r"[0-9a-f]{16}", new_session_id())

    def test_ids_are_not_repeated(self):
        assert len({new_session_id() for _ in range(200)}) == 200


class TestProtocol:
    def test_satisfies_query_logger_protocol(self, tmp_path):
        assert isinstance(make_logger(tmp_path), QueryLoggerProtocol)
