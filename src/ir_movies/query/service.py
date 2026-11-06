"""SearchService: orquestra reescrita, índice, explicabilidade e log (D-036, D-090).

Fluxo de ``search``: consulta bruta -> truncagem -> ``Rewriter`` -> pré-processamento ->
``TfidfIndex`` -> ``SearchResult`` -> (opcional) linha de log.

Implementa ``SearchServiceProtocol`` por completo; a interface só conhece o protocolo.
"""

from __future__ import annotations

import time
from pathlib import Path

import ir_movies
from ir_movies.config import load_config
from ir_movies.index.tfidf import TermContribution, TfidfIndex
from ir_movies.logging_jsonl import QueryLogger
from ir_movies.query.rewriter import IdentityRewriter
from ir_movies.query.snapshot_loader import LoadedSnapshot, load_snapshot
from ir_movies.query.types import (
    MAX_QUERY_CHARS,
    MODEL_NAME,
    Movie,
    MovieHit,
    QueryLoggerProtocol,
    Rewriter,
    SearchResult,
)
from ir_movies.text.preprocess import Preprocessor

__all__ = ["SearchService"]


class SearchService:
    """Serviço de busca TF-IDF + cosseno sobre um acervo já carregado."""

    def __init__(
        self,
        snapshot: LoadedSnapshot,
        cfg: dict,
        *,
        rewriter: Rewriter | None = None,
        logger: QueryLoggerProtocol | None = None,
        app_version: str | None = None,
    ) -> None:
        """Monta pré-processador e índice a partir de ``text`` e ``tfidf`` de *cfg*.

        *logger* padrão: ``QueryLogger.from_config`` (seção ``logging`` de *cfg*).
        *app_version* padrão: ``ir_movies.__version__``.
        """
        self._movies = list(snapshot.movies)
        self._by_id = {m.id: m for m in self._movies}
        self._snapshot_id = snapshot.snapshot_id
        self._app_version = ir_movies.__version__ if app_version is None else app_version
        self._top_k = int(cfg["search"]["top_k"])
        self._rewriter: Rewriter = IdentityRewriter() if rewriter is None else rewriter

        self._preprocessor = Preprocessor(cfg["text"])
        self._index = TfidfIndex.build(snapshot.texts, self._preprocessor, cfg["tfidf"])

        self.logger: QueryLoggerProtocol = (
            logger
            if logger is not None
            else QueryLogger.from_config(
                cfg,
                app_version=self._app_version,
                snapshot_id=self._snapshot_id,
                model=MODEL_NAME,
                rewriter=self._rewriter.name,
            )
        )

    @classmethod
    def from_config(
        cls,
        config_path: str | Path | None = None,
        *,
        data_dir: str | Path | None = None,
        **kwargs,
    ) -> SearchService:
        """Caminho de produção: lê ``config.yaml``, carrega o snapshot e monta o serviço."""
        cfg = load_config(config_path)
        return cls(load_snapshot(data_dir), cfg, **kwargs)

    # --- Contrato: SearchServiceProtocol ---

    @property
    def snapshot_id(self) -> str:
        return self._snapshot_id

    @property
    def app_version(self) -> str:
        return self._app_version

    def search(
        self,
        raw_query: str,
        k: int | None = None,
        session_id: str | None = None,
    ) -> SearchResult:
        """Busca *raw_query* e devolve até *k* resultados (``None``: ``search.top_k``).

        Nunca levanta exceção por causa da consulta (vazia, só palavras comuns ou sem
        nenhuma palavra do acervo): devolve ``hits == []`` com o ``trace`` preenchido.
        A latência cobre só este caminho, sem a escrita do log (D-032).
        """
        started = time.perf_counter()

        raw = (raw_query or "")[:MAX_QUERY_CHARS]
        effective = self._rewriter.rewrite(raw)
        trace = self._preprocessor.trace(effective)
        limit = max(0, self._top_k if k is None else k)

        hits = [
            MovieHit(
                movie_id=self._movies[hit.doc_id].id,
                rank=position,
                score=hit.score,
                doc_id=hit.doc_id,
            )
            for position, hit in enumerate(self._index.search(effective, k=limit), start=1)
        ]
        oov_terms = self._index.oov_terms(effective)
        latency_ms = (time.perf_counter() - started) * 1000

        result = SearchResult(
            raw_query=raw,
            effective_query=effective,
            trace=trace,
            hits=hits,
            oov_terms=oov_terms,
            latency_ms=latency_ms,
            snapshot_id=self._snapshot_id,
        )

        if session_id is not None:
            self.logger.log_search(result, session_id)
        return result

    def contributions(self, effective_query: str, doc_id: int) -> list[TermContribution]:
        """Decompõe a pontuação do documento *doc_id*, termo a termo."""
        return self._index.contributions(effective_query, doc_id)

    def get_movie(self, movie_id: int) -> Movie:
        """Dados de exibição de um filme. Levanta ``KeyError`` se não existir."""
        return self._by_id[movie_id]

    def log_click(self, session_id: str, movie_id: int, rank: int) -> None:
        """Registra que a pessoa abriu um resultado (``rank`` começa em 1)."""
        self.logger.log_click(session_id, movie_id, rank)
