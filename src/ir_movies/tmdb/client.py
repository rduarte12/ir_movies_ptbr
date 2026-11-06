"""Cliente HTTP para /movie/{id} com retry e backoff (D-023)."""

from __future__ import annotations

import logging
import time

import requests
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.themoviedb.org/3/movie/{movie_id}"


class TmdbApiError(Exception):
    """Erro não-retentável da API da TMDB (ex.: 404)."""

    def __init__(self, status_code: int, movie_id: int, body: str = ""):
        self.status_code = status_code
        self.movie_id = movie_id
        super().__init__(f"TMDB HTTP {status_code} para movie_id={movie_id}: {body}")


def _is_retryable_response(response: requests.Response) -> bool:
    return response.status_code == 429 or response.status_code >= 500


class TmdbClient:
    """Cliente para a API de detalhes de filmes da TMDB.

    Usa Bearer token (API v4 read access) e retry com backoff exponencial.
    """

    def __init__(self, token: str, cfg: dict) -> None:
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {token}"
        self._session.headers["Accept"] = "application/json"

        tmdb_cfg = cfg.get("tmdb", {})
        self._language = tmdb_cfg.get("language", "pt-BR")
        retry_cfg = tmdb_cfg.get("retry", {})
        self._max_attempts = retry_cfg.get("max_attempts", 3)
        self._backoff_factor = retry_cfg.get("backoff_factor", 1.0)
        self._rate_limit_interval = 1.0 / tmdb_cfg.get("rate_limit_rps", 20)
        self._last_request_time: float = 0.0

    def _throttle(self) -> None:
        """Espera o tempo necessário para respeitar o rate limit."""
        elapsed = time.monotonic() - self._last_request_time
        wait = self._rate_limit_interval - elapsed
        if wait > 0:
            time.sleep(wait)

    def get_movie(self, movie_id: int) -> dict:
        """Busca detalhes do filme *movie_id* em PT-BR, com credits e keywords.

        Retorna o JSON bruto da TMDB. Levanta ``TmdbApiError`` em 404 ou
        outros erros não-retentáveis após esgotar as tentativas.
        """
        url = _BASE_URL.format(movie_id=movie_id)
        params = {
            "language": self._language,
            "append_to_response": "credits,keywords",
        }

        @retry(
            stop=stop_after_attempt(self._max_attempts),
            wait=wait_exponential(multiplier=self._backoff_factor),
            retry=(
                retry_if_result(_is_retryable_response)
                | retry_if_exception_type((requests.ConnectionError, requests.Timeout))
            ),
            reraise=True,
        )
        def _do_request() -> requests.Response:
            self._throttle()
            self._last_request_time = time.monotonic()
            return self._session.get(url, params=params, timeout=30)

        try:
            resp = _do_request()
        except RetryError as exc:
            last = exc.last_attempt.result()
            raise TmdbApiError(last.status_code, movie_id, last.text[:200]) from exc

        if resp.status_code == 200:
            return resp.json()

        raise TmdbApiError(resp.status_code, movie_id, resp.text[:200])

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> TmdbClient:
        return self

    def __exit__(self, *exc) -> None:
        self.close()
