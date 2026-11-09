"""Contratos do serviço de busca: tipos e protocolos (D-090).

Este módulo é a única peça compartilhada entre o serviço de busca (Sprint 5) e a
interface (Sprints 6 e 7). A interface depende apenas de ``SearchServiceProtocol``
e recebe o serviço por injeção, sem conhecer o índice TF-IDF nem o log.

As assinaturas seguem ``docs/architecture.md`` secao 3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import numpy as np

from ir_movies.index.tfidf import TermContribution
from ir_movies.text.preprocess import PreprocessTrace

if TYPE_CHECKING:
    pass

# Campo `model` do log (D-005: a v1 tem um único modelo).
MODEL_NAME = "tfidf"

# Limite de caracteres aceito numa consulta (ui_spec.md secao 1.2).
# O serviço trunca por conta própria: a interface não é a única guarda.
MAX_QUERY_CHARS = 300

__all__ = [
    "MAX_QUERY_CHARS",
    "MODEL_NAME",
    "Encoder",
    "Movie",
    "MovieHit",
    "QueryLoggerProtocol",
    "Rewriter",
    "SearchResult",
    "SearchServiceProtocol",
]


@dataclass(frozen=True)
class Movie:
    """Dados de um filme para exibição; espelha o esquema do snapshot.

    Normalizações feitas pelo carregador do snapshot, para que a interface
    tenha uma regra só:

    - ``runtime``: ``None`` quando desconhecido (o snapshot usa 0 nesse caso);
    - ``poster_path``: ``None`` quando ausente (a interface usa um placeholder);
    - ``tagline``, ``director`` e ``release_date``: string vazia quando ausentes.
    """

    id: int
    title: str
    original_title: str
    tagline: str
    overview: str
    genres: list[str]
    cast_top5: list[str]
    director: str
    release_date: str
    runtime: int | None
    vote_average: float
    vote_count: int
    poster_path: str | None

    @property
    def year(self) -> str:
        """Ano de lançamento, ou string vazia se desconhecido.

        Convenção única para a legenda da grade e o painel de detalhes.
        """
        return self.release_date[:4] if self.release_date else ""


@dataclass(frozen=True)
class MovieHit:
    """Um resultado de busca: qual filme, em que posição, com que pontuação."""

    movie_id: int
    """Id TMDB do filme; é o que vai para o log de clique."""

    rank: int
    """Posição na lista de resultados, começando em 1 (igual à tela e ao log)."""

    score: float
    """Cosseno TF-IDF entre a consulta e o documento. Base da Explicabilidade (D-096)."""

    doc_id: int
    """Posição do filme no corpus; liga o resultado às contribuições por termo."""

    semantic_score: float | None = field(default=None)
    """Cosseno semântico (D-096). None quando a etapa semântica está inativa."""

    rrf_score: float | None = field(default=None)
    """Pontuação RRF combinada (D-095, D-096). None quando a etapa semântica está inativa."""


@dataclass(frozen=True)
class SearchResult:
    """Resultado completo de uma busca (``docs/architecture.md`` secao 3)."""

    raw_query: str
    """Consulta como a pessoa digitou, truncada em ``MAX_QUERY_CHARS``."""

    effective_query: str
    """Consulta depois do ``Rewriter``. Igual à bruta na v1 (D-009)."""

    trace: PreprocessTrace
    """Rastreio do pré-processamento, base do nível 3 da Explicabilidade."""

    hits: list[MovieHit]
    """Resultados ordenados pela pontuação final (D-096): cosseno TF-IDF decrescente
    quando a etapa semântica está inativa; pontuação RRF decrescente quando ativa.
    Vazio é um caso válido."""

    oov_terms: list[str]
    """Radicais da consulta que não existem no acervo (nível 3d da tela)."""

    latency_ms: float
    """Tempo só do caminho de busca, sem montagem de índice nem escrita de log."""

    snapshot_id: str
    """Identificador do acervo usado, para rastreabilidade do log e do rodapé."""


@runtime_checkable
class Encoder(Protocol):
    """Codificação densa de textos para a etapa semântica (D-093, D-094).

    A implementação de produção usa ``sentence-transformers``; os testes usam
    ``FakeEncoder`` com vetores pequenos e fixos.
    """

    def encode(self, texts: list[str]) -> np.ndarray:
        """Devolve matriz ``(N, D) float32`` L2-normalizada, onde ``N = len(texts)``."""
        ...


@runtime_checkable
class Rewriter(Protocol):
    """Reescrita da consulta antes do pré-processamento (D-009).

    A v1 usa ``IdentityRewriter``. O ponto de extensão existe para que um
    reescritor por modelo de linguagem possa entrar depois sem mudar o resto do
    pipeline — ao custo do determinismo, hoje garantido.
    """

    name: str
    """Identificador curto que vai para o campo ``rewriter`` do log."""

    def rewrite(self, raw: str) -> str:
        """Devolve a consulta efetiva a partir da consulta bruta."""
        ...


@runtime_checkable
class QueryLoggerProtocol(Protocol):
    """Log de consultas e cliques em JSONL (D-008).

    O contexto fixo de cada linha (``app_version``, ``snapshot_id``, ``model``,
    ``rewriter``) é dado ao construir o logger, não a cada chamada: assim quem
    registra um evento não precisa saber de rastreabilidade.

    Nunca registrar IP, user-agent ou qualquer dado pessoal.
    """

    def log_search(self, result: SearchResult, session_id: str) -> None:
        """Acrescenta uma linha de evento ``search``."""
        ...

    def log_click(self, session_id: str, movie_id: int, rank: int) -> None:
        """Acrescenta uma linha de evento ``click`` (``rank`` começa em 1)."""
        ...


@runtime_checkable
class SearchServiceProtocol(Protocol):
    """O que a interface pode pedir ao buscador — e nada além disto.

    Invariantes que toda implementação deve respeitar (verificados em
    ``tests/test_contract.py``):

    1. ``search`` nunca levanta exceção por causa da consulta: consulta vazia,
       só com palavras comuns ou sem nenhuma palavra no acervo devolve
       ``hits == []`` com o ``trace`` preenchido, para a interface distinguir os
       casos de ``ui_spec.md`` secao 2.
    2. ``search`` trunca a consulta em ``MAX_QUERY_CHARS``.
    3. Para todo ``hit``, a soma de ``contributions(result.effective_query,
       hit.doc_id)`` é igual a ``hit.score`` com tolerância de 1e-9
       (invariante 1 de ``architecture.md``). ``hit.score`` é sempre o cosseno
       TF-IDF, independentemente da etapa semântica (D-096).
    4. ``search`` só registra no log quando recebe ``session_id``;
       ``log_click`` registra sempre.
    5. Determinismo: a mesma consulta no mesmo acervo devolve os mesmos
       ``hits``, na mesma ordem (invariante 3 de ``architecture.md``).
    6. Ordenação (D-096): quando a etapa semântica está inativa, ``hits`` estão
       em ordem decrescente de ``score`` (TF-IDF). Quando ativa, em ordem
       decrescente de ``rrf_score`` (desempate pelo posto semântico). Em ambos
       os casos, ``rank`` é consecutivo começando em 1.
    """

    @property
    def snapshot_id(self) -> str:
        """Identificador do acervo carregado (rodapé e log)."""
        ...

    @property
    def app_version(self) -> str:
        """Versão da aplicação (rodapé e log)."""
        ...

    @property
    def semantic_active(self) -> bool:
        """Indica se a etapa semântica está de fato ativa (D-097, D-100).

        ``False`` quando desligada por config, quando os vetores não carregaram
        ou quando o modelo falhou ao inicializar (falha suave).
        """
        ...

    def search(
        self,
        raw_query: str,
        k: int | None = None,
        session_id: str | None = None,
    ) -> SearchResult:
        """Busca *raw_query* e devolve até *k* resultados.

        ``k=None`` usa ``search.top_k`` do ``config.yaml``.
        ``session_id=None`` não registra o evento no log.
        """
        ...

    def contributions(self, effective_query: str, doc_id: int) -> list[TermContribution]:
        """Decompõe a pontuação de um documento, termo a termo.

        Recebe a consulta **efetiva** (depois do ``Rewriter``), não a bruta.
        """
        ...

    def get_movie(self, movie_id: int) -> Movie:
        """Dados de exibição de um filme. Levanta ``KeyError`` se não existir."""
        ...

    def log_click(self, session_id: str, movie_id: int, rank: int) -> None:
        """Registra que a pessoa abriu um resultado (``rank`` começa em 1)."""
        ...
