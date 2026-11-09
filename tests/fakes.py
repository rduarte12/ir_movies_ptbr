"""Implementação de referência do contrato de busca, para testes (D-090).

Serve dois propósitos:

1. A interface (Sprints 6 e 7) é construída e testada contra este objeto, antes
   de o serviço real (Sprint 5) existir.
2. ``tests/test_contract.py`` prova que o contrato de ``query/types.py`` é
   satisfazível, e o serviço real é conferido contra as mesmas regras.

O índice e o pré-processamento aqui são os **reais** (prontos desde a Sprint 4),
sobre o corpus de brinquedo de cinco filmes. Números inventados não serviriam: a
Explicabilidade é construída sobre o invariante "soma das contribuições =
cosseno", e com pontuações falsas a interface seria montada contra um invariante
que não vale.

O que é de fato falso aqui: a origem dos dados (fixture, não snapshot) e o log
(lista em memória, não arquivo).
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ir_movies.index.tfidf import TermContribution, TfidfIndex
from ir_movies.query.types import (
    MAX_QUERY_CHARS,
    Movie,
    MovieHit,
    SearchResult,
)
from ir_movies.text.preprocess import Preprocessor

FIXTURES_DIR = Path(__file__).parent / "fixtures"

TEXT_CFG = {"stemmer": "snowball_pt", "extra_stopwords": [], "strip_accents": True}

TFIDF_CFG = {
    "ngram_range": [1, 1],
    "norm": "l2",
    "smooth_idf": True,
    "sublinear_tf": False,
    "min_df": 1,
}

# Casos de borda que a interface precisa tratar (ui_spec.md secao 2). O corpus de
# brinquedo não traz esses campos, então eles são atribuídos aqui de propósito,
# para que a interface tenha com que trabalhar sem depender do snapshot real.
_NO_POSTER_IDS = frozenset({5})
_NO_RUNTIME_IDS = frozenset({5})
_NO_TAGLINE_IDS = frozenset({4})


FAKE_ENCODER_DIM = 4
"""Dimensão dos vetores do FakeEncoder; pequena para manter os testes rápidos."""


class FakeEncoder:
    """Encoder falso para testes: vetores 4-D fixos por texto, L2-normalizados.

    Determinístico: o mesmo texto sempre produz o mesmo vetor. Obedece ao
    protocolo ``Encoder`` de ``query/types.py``.
    """

    dim: int = FAKE_ENCODER_DIM

    def encode(self, texts: list[str]) -> np.ndarray:
        result = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16) % (2**32)
            rng = np.random.default_rng(seed)
            vec = rng.standard_normal(self.dim).astype(np.float32)
            norm = np.linalg.norm(vec)
            result[i] = vec / max(norm, 1e-8)
        return result


class IdentityRewriterStub:
    """Reescritor trivial: devolve a consulta como veio (D-009).

    Existe só para o contrato poder ser testado antes de a Sprint 5 entregar o
    ``IdentityRewriter`` de verdade. Não usar fora dos testes.
    """

    name = "identity"

    def rewrite(self, raw: str) -> str:
        return raw


@dataclass(frozen=True)
class LoggedEvent:
    """Um evento registrado em memória."""

    event: str
    session_id: str
    fields: dict


@dataclass
class MemoryQueryLogger:
    """Log em memória, obedecendo ``QueryLoggerProtocol``, sem tocar o disco.

    **Não** é a referência do esquema JSONL: isso é o ``QueryLogger`` da
    Sprint 5, definido por ``docs/architecture.md`` secao 5. Aqui guardamos o
    mínimo para os testes verificarem *que* algo foi registrado e com quais
    valores-chave.
    """

    events: list[LoggedEvent] = field(default_factory=list)

    def log_search(self, result: SearchResult, session_id: str) -> None:
        self.events.append(
            LoggedEvent(
                event="search",
                session_id=session_id,
                fields={
                    "raw_query": result.raw_query,
                    "effective_query": result.effective_query,
                    "n_results": len(result.hits),
                    "n_oov_tokens": len(result.oov_terms),
                    "top_ids": [h.movie_id for h in result.hits[:10]],
                    "snapshot_id": result.snapshot_id,
                },
            )
        )

    def log_click(self, session_id: str, movie_id: int, rank: int) -> None:
        self.events.append(
            LoggedEvent(
                event="click",
                session_id=session_id,
                fields={"movie_id": movie_id, "rank": rank},
            )
        )


def _to_movie(raw: dict) -> Movie:
    """Converte uma entrada do corpus de brinquedo em ``Movie``.

    Preenche os campos que a fixture não tem, aplicando as normalizações que o
    carregador do snapshot real também aplica (``runtime`` e ``poster_path``
    viram ``None`` quando ausentes).
    """
    movie_id = int(raw["id"])
    return Movie(
        id=movie_id,
        title=raw["title"],
        original_title=raw["title"],
        tagline="" if movie_id in _NO_TAGLINE_IDS else raw.get("tagline", ""),
        overview=raw["overview"],
        genres=list(raw.get("genres") or []),
        cast_top5=[f"Elenco {movie_id}-1", f"Elenco {movie_id}-2"],
        director=f"Direção {movie_id}",
        release_date=f"{1999 + movie_id}-01-01",
        runtime=None if movie_id in _NO_RUNTIME_IDS else 90 + movie_id,
        vote_average=6.0 + movie_id / 10,
        vote_count=10 * movie_id,
        poster_path=None if movie_id in _NO_POSTER_IDS else f"/fake{movie_id}.jpg",
    )


def document_text(movie: Movie) -> str:
    """Texto indexado de um filme: título + tagline + sinopse + gêneros (D-013).

    A concatenação é responsabilidade de quem chama ``TfidfIndex.build``; esta
    função fixa a convenção para que o serviço falso e o real indexem igual.
    """
    return " ".join([movie.title, movie.tagline, movie.overview, " ".join(movie.genres)])


class FakeSearchService:
    """Serviço de busca sobre um acervo de brinquedo, obedecendo ao contrato."""

    def __init__(
        self,
        movies: list[dict],
        *,
        top_k: int = 5,
        snapshot_id: str = "toy-00000000",
        app_version: str = "0.0.0-toy",
        rewriter: object | None = None,
        logger: MemoryQueryLogger | None = None,
    ) -> None:
        self._movies = [_to_movie(m) for m in movies]
        self._by_id = {m.id: m for m in self._movies}
        self._top_k = top_k
        self._snapshot_id = snapshot_id
        self._app_version = app_version
        self._rewriter = rewriter if rewriter is not None else IdentityRewriterStub()
        self.logger = logger if logger is not None else MemoryQueryLogger()

        self._preprocessor = Preprocessor(TEXT_CFG)
        docs = [document_text(m) for m in self._movies]
        self._index = TfidfIndex.build(docs, self._preprocessor, TFIDF_CFG)

    @classmethod
    def from_toy(cls, **kwargs) -> FakeSearchService:
        """Monta o serviço a partir de ``tests/fixtures/toy_corpus.json``."""
        with open(FIXTURES_DIR / "toy_corpus.json", encoding="utf-8") as f:
            movies = json.load(f)
        return cls(movies, **kwargs)

    # --- Contrato: SearchServiceProtocol ---

    @property
    def snapshot_id(self) -> str:
        return self._snapshot_id

    @property
    def app_version(self) -> str:
        return self._app_version

    @property
    def semantic_active(self) -> bool:
        """Sempre False: o serviço de brinquedo não tem etapa semântica."""
        return False

    def search(
        self,
        raw_query: str,
        k: int | None = None,
        session_id: str | None = None,
    ) -> SearchResult:
        started = time.perf_counter()

        raw = (raw_query or "")[:MAX_QUERY_CHARS]
        effective = self._rewriter.rewrite(raw)
        trace = self._preprocessor.trace(effective)
        limit = self._top_k if k is None else k

        hits = [
            MovieHit(
                movie_id=self._movies[hit.doc_id].id,
                rank=position,
                score=hit.score,
                doc_id=hit.doc_id,
            )
            for position, hit in enumerate(self._index.search(effective, k=limit), start=1)
        ]

        result = SearchResult(
            raw_query=raw,
            effective_query=effective,
            trace=trace,
            hits=hits,
            oov_terms=self._index.oov_terms(effective),
            latency_ms=(time.perf_counter() - started) * 1000,
            snapshot_id=self._snapshot_id,
        )

        if session_id is not None:
            self.logger.log_search(result, session_id)
        return result

    def contributions(self, effective_query: str, doc_id: int) -> list[TermContribution]:
        return self._index.contributions(effective_query, doc_id)

    def get_movie(self, movie_id: int) -> Movie:
        return self._by_id[movie_id]

    def log_click(self, session_id: str, movie_id: int, rank: int) -> None:
        self.logger.log_click(session_id, movie_id, rank)
