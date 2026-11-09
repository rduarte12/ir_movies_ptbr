"""SearchService: orquestra reescrita, índice, explicabilidade e log (D-036, D-090).

Fluxo de ``search`` quando a etapa semântica está ativa (D-092 a D-097):
  consulta bruta -> truncagem -> Rewriter -> pré-processamento
    -> SemanticRetriever.top_k (20 candidatos)
    -> TfidfIndex.score_subset (pontua só os candidatos)
    -> RRF (D-095) -> SearchResult

Quando inativa, o fluxo é idêntico ao da v1:
  consulta bruta -> truncagem -> Rewriter -> pré-processamento
    -> TfidfIndex.search -> SearchResult

Implementa ``SearchServiceProtocol`` por completo; a interface só conhece o protocolo.
"""

from __future__ import annotations

import logging as _logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from ir_movies.index.semantic import SemanticRetriever

__all__ = ["SearchService"]

logger = _logging.getLogger(__name__)


def _rrf_score(rank: int, k: int) -> float:
    return 1.0 / (k + rank)


class SearchService:
    """Serviço de busca TF-IDF + cosseno, com etapa semântica opcional (D-092)."""

    def __init__(
        self,
        snapshot: LoadedSnapshot,
        cfg: dict,
        *,
        rewriter: Rewriter | None = None,
        logger: QueryLoggerProtocol | None = None,
        app_version: str | None = None,
        semantic_retriever: SemanticRetriever | None = None,
    ) -> None:
        """Monta pré-processador e índice a partir de ``text`` e ``tfidf`` de *cfg*.

        *logger* padrão: ``QueryLogger.from_config`` (seção ``logging`` de *cfg*).
        *app_version* padrão: ``ir_movies.__version__``.
        *semantic_retriever* opcional: injetável para testes (D-097); quando ``None``
        e ``semantic.enabled`` é verdadeiro, ``from_config`` tenta carregar do disco.
        """
        self._movies = list(snapshot.movies)
        self._by_id = {m.id: m for m in self._movies}
        self._snapshot_id = snapshot.snapshot_id
        self._app_version = ir_movies.__version__ if app_version is None else app_version
        self._top_k = int(cfg["search"]["top_k"])
        self._rewriter: Rewriter = IdentityRewriter() if rewriter is None else rewriter
        self._sem_cfg = cfg.get("semantic", {})
        self._semantic_retriever: SemanticRetriever | None = semantic_retriever

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
        """Caminho de produção: lê config, carrega snapshot, tenta etapa semântica."""
        cfg = load_config(config_path)
        snapshot = load_snapshot(data_dir)

        retriever = None
        sem_cfg = cfg.get("semantic", {})
        if sem_cfg.get("enabled", False):
            retriever = _try_load_retriever(cfg, snapshot.snapshot_id)

        return cls(snapshot, cfg, semantic_retriever=retriever, **kwargs)

    # --- Contrato: SearchServiceProtocol ---

    @property
    def snapshot_id(self) -> str:
        return self._snapshot_id

    @property
    def app_version(self) -> str:
        return self._app_version

    @property
    def semantic_active(self) -> bool:
        """Verdadeiro quando a etapa semântica está de fato ativa (D-097)."""
        return self._semantic_retriever is not None

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

        if self._semantic_retriever is not None:
            hits = self._search_hybrid(effective, limit)
        else:
            hits = self._search_tfidf(effective, limit)

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

    # --- Busca interna ---

    def _search_tfidf(self, effective: str, k: int) -> list[MovieHit]:
        """Busca TF-IDF pura (comportamento da v1)."""
        return [
            MovieHit(
                movie_id=self._movies[hit.doc_id].id,
                rank=position,
                score=hit.score,
                doc_id=hit.doc_id,
            )
            for position, hit in enumerate(self._index.search(effective, k=k), start=1)
        ]

    def _search_hybrid(self, effective: str, k: int) -> list[MovieHit]:
        """Busca híbrida: semântica -> TF-IDF -> RRF (D-092, D-095, D-096)."""
        retriever = self._semantic_retriever  # já verificado não-None pelo chamador
        assert retriever is not None

        n_candidates = int(self._sem_cfg.get("candidates", 20))
        rrf_k = int(self._sem_cfg.get("rrf_k", 60))

        # Passo 1: top-k semântico
        sem_hits = retriever.top_k(effective, k=n_candidates)
        if not sem_hits:
            return self._search_tfidf(effective, k)

        # Passo 2: pontua só os candidatos com o IDF do corpus inteiro
        candidate_doc_ids = [doc_id for doc_id, _ in sem_hits]
        tfidf_hits = self._index.score_subset(effective, candidate_doc_ids)
        tfidf_by_doc: dict[int, float] = {h.doc_id: h.score for h in tfidf_hits}

        # Posto TF-IDF: só os candidatos com score > 0, em ordem de score desc
        tfidf_ranked = sorted(tfidf_by_doc.keys(), key=lambda d: (-tfidf_by_doc[d], d))
        tfidf_rank_of: dict[int, int] = {d: i + 1 for i, d in enumerate(tfidf_ranked)}

        # Passo 3: RRF sobre os candidatos semânticos
        sem_score_of: dict[int, float] = {doc_id: score for doc_id, score in sem_hits}
        sem_rank_of: dict[int, int] = {doc_id: i + 1 for i, (doc_id, _) in enumerate(sem_hits)}

        rrf_scores: list[tuple[int, float, int]] = []  # (doc_id, rrf_score, sem_rank)
        for doc_id, _sem_score in sem_hits:
            rrf = _rrf_score(sem_rank_of[doc_id], rrf_k)
            if doc_id in tfidf_rank_of:
                rrf += _rrf_score(tfidf_rank_of[doc_id], rrf_k)
            rrf_scores.append((doc_id, rrf, sem_rank_of[doc_id]))

        # Ordem: rrf_score desc; empate: menor posto semântico (D-095)
        rrf_scores.sort(key=lambda t: (-t[1], t[2]))

        return [
            MovieHit(
                movie_id=self._movies[doc_id].id,
                rank=position,
                score=tfidf_by_doc.get(doc_id, 0.0),
                doc_id=doc_id,
                semantic_score=sem_score_of[doc_id],
                rrf_score=rrf,
            )
            for position, (doc_id, rrf, _) in enumerate(rrf_scores[:k], start=1)
        ]


def _try_load_retriever(cfg: dict, snapshot_id: str) -> SemanticRetriever | None:
    """Tenta carregar o retriever semântico; em falha, retorna None e loga aviso."""
    try:
        encoder = _build_encoder(cfg)
        from ir_movies.index.semantic import load_semantic_retriever

        return load_semantic_retriever(cfg, snapshot_id, encoder)
    except Exception as exc:
        logger.warning(
            "Etapa semântica desativada (falha suave, D-097): %s", exc
        )
        return None


def _build_encoder(cfg: dict) -> object:
    """Constrói o encoder sentence-transformers conforme o config."""
    sem_cfg = cfg.get("semantic", {})
    model_name: str = str(sem_cfg.get("model", ""))
    revision: str | None = str(sem_cfg.get("revision")) or None

    from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

    model = SentenceTransformer(model_name, revision=revision)
    return _SentenceTransformerEncoder(model)


class _SentenceTransformerEncoder:
    """Adaptador do SentenceTransformer para o protocolo Encoder."""

    def __init__(self, model) -> None:
        self._model = model

    def encode(self, texts: list[str]):
        import numpy as np

        vecs = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.array(vecs, dtype=np.float32)
