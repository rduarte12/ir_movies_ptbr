"""Testes para ir_movies.tmdb.client (sem rede, usando unittest.mock)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ir_movies.tmdb.client import TmdbApiError, TmdbClient

FIXTURES_DIR = Path(__file__).parent / "fixtures"

_CFG = {
    "tmdb": {
        "language": "pt-BR",
        "retry": {"max_attempts": 3, "backoff_factor": 0.01},
        "rate_limit_rps": 1000,  # sem espera nos testes
    }
}


def _load_fixture_278() -> dict:
    with open(FIXTURES_DIR / "movie_278.json", encoding="utf-8") as f:
        return json.load(f)


def _mock_response(status_code: int, json_data: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = json.dumps(json_data or {})[:200]
    return resp


class TestGetMovieSuccess:
    def test_returns_json_for_200(self):
        """Resposta 200 devolve o JSON com os campos esperados."""
        fixture = _load_fixture_278()
        with patch.object(TmdbClient, "_throttle"):
            client = TmdbClient(token="fake-token", cfg=_CFG)
            with patch.object(client._session, "get", return_value=_mock_response(200, fixture)):
                result = client.get_movie(278)

        assert result["id"] == 278
        assert result["title"] == "Um Sonho de Liberdade"
        assert "overview" in result
        assert "credits" in result
        assert "keywords" in result

    def test_sends_correct_params(self):
        """Verifica language e append_to_response na chamada."""
        fixture = _load_fixture_278()
        with patch.object(TmdbClient, "_throttle"):
            client = TmdbClient(token="fake-token", cfg=_CFG)
            with patch.object(
                client._session, "get", return_value=_mock_response(200, fixture)
            ) as mock_get:
                client.get_movie(278)

        _, kwargs = mock_get.call_args
        assert kwargs["params"]["language"] == "pt-BR"
        assert kwargs["params"]["append_to_response"] == "credits,keywords"

    def test_bearer_token_in_header(self):
        """O header Authorization usa Bearer token."""
        client = TmdbClient(token="my-secret-token", cfg=_CFG)
        assert client._session.headers["Authorization"] == "Bearer my-secret-token"
        client.close()


class TestGetMovieRetry:
    def test_retries_on_429(self):
        """HTTP 429 na primeira tentativa; 200 na segunda."""
        fixture = _load_fixture_278()
        responses = [_mock_response(429), _mock_response(200, fixture)]
        with patch.object(TmdbClient, "_throttle"):
            client = TmdbClient(token="fake", cfg=_CFG)
            with patch.object(client._session, "get", side_effect=responses):
                result = client.get_movie(278)

        assert result["id"] == 278

    def test_retries_on_500(self):
        """HTTP 500 na primeira tentativa; 200 na segunda."""
        fixture = _load_fixture_278()
        responses = [_mock_response(500), _mock_response(200, fixture)]
        with patch.object(TmdbClient, "_throttle"):
            client = TmdbClient(token="fake", cfg=_CFG)
            with patch.object(client._session, "get", side_effect=responses):
                result = client.get_movie(278)

        assert result["id"] == 278


class TestGetMovieErrors:
    def test_raises_on_404(self):
        """HTTP 404 levanta TmdbApiError sem retry."""
        with patch.object(TmdbClient, "_throttle"):
            client = TmdbClient(token="fake", cfg=_CFG)
            with (
                patch.object(client._session, "get", return_value=_mock_response(404)),
                pytest.raises(TmdbApiError, match="404"),
            ):
                client.get_movie(99999999)

    def test_raises_after_max_retries(self):
        """Esgotando retries em 429 levanta TmdbApiError."""
        all_429 = [_mock_response(429)] * 3
        with patch.object(TmdbClient, "_throttle"):
            client = TmdbClient(token="fake", cfg=_CFG)
            with (
                patch.object(client._session, "get", side_effect=all_429),
                pytest.raises(TmdbApiError, match="429"),
            ):
                client.get_movie(278)


class TestContextManager:
    def test_context_manager(self):
        """TmdbClient funciona como context manager."""
        with TmdbClient(token="fake", cfg=_CFG) as client:
            assert client is not None
