"""Conteúdo da tela: funções puras que montam o que a pessoa vê.

Separar isto de ``app.py`` é deliberado (D-057). Os blocos difíceis desta
interface são a legenda da grade e os três níveis da Explicabilidade — justo o
que não se pode aceitar "de olho", porque é onde os números têm de fechar com a
pontuação (``ui_spec.md`` secao 3). Aqui eles são funções que recebem o serviço
de busca e a configuração e devolvem texto, então um teste consegue conferir o
número exibido contra o número calculado.

``app.py`` cuida só dos componentes do Gradio e da ligação dos eventos.
"""

from __future__ import annotations

import html
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ir_movies.explain import highlight
from ir_movies.query.types import SearchResult
from ir_movies.ui import texts
from ir_movies.ui.format import (
    caption,
    format_score,
    highlight_level,
    placeholder_svg,
    poster_src,
    poster_url,
    rating_label,
    runtime_label,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ir_movies.index.tfidf import TermContribution
    from ir_movies.query.types import Movie, MovieHit, SearchServiceProtocol

logger = logging.getLogger(__name__)

# --- Estados da tela (ui_spec.md secao 2, D-059) ---

STATE_OK = "ok"
STATE_EMPTY_QUERY = "empty_query"
STATE_ONLY_STOPWORDS = "only_stopwords"
STATE_NO_WORD_IN_CORPUS = "no_word_in_corpus"
STATE_UNEXPECTED_ERROR = "unexpected_error"

_STATE_MESSAGES = {
    STATE_OK: "",
    STATE_EMPTY_QUERY: texts.STATE_EMPTY_QUERY,
    STATE_ONLY_STOPWORDS: texts.STATE_ONLY_STOPWORDS,
    STATE_NO_WORD_IN_CORPUS: texts.STATE_NO_WORD_IN_CORPUS,
    STATE_UNEXPECTED_ERROR: texts.STATE_UNEXPECTED_ERROR,
}


def query_state(result: SearchResult) -> str:
    """Classifica o resultado num dos estados de ``ui_spec.md`` secao 2.

    A ordem importa: "não escreveu nada" vem antes de "só palavras comuns", que
    vem antes de "nenhuma palavra no acervo". Nada aqui depende de exceção — a
    regra 1 do contrato (D-090) garante que a busca sempre devolve um resultado.
    """
    trace = result.trace
    if not trace.original_tokens:
        return STATE_EMPTY_QUERY
    if not trace.stems and trace.stopped:
        return STATE_ONLY_STOPWORDS
    if not result.hits:
        return STATE_NO_WORD_IN_CORPUS
    return STATE_OK


def state_message(state: str) -> str:
    """Texto do estado, exatamente como em ``ui_spec.md`` secao 2 (vazio se não há)."""
    return _STATE_MESSAGES.get(state, "")


# --- Estrutura do que vai para a tela ---


@dataclass(frozen=True)
class Panels:
    """Os quatro blocos que dependem do filme selecionado."""

    details: str
    level1: str
    level2: str
    level3: str


@dataclass(frozen=True)
class Screen:
    """Tudo o que uma busca produz para a tela."""

    gallery: list[tuple[str, str]]
    message: str
    panels: Panels
    result: SearchResult | None
    selected: int | None
    state: str = STATE_OK


# --- Blocos fixos ---


def header_html(cfg: dict) -> str:
    """Cabeçalho: nome do app e a frase de abertura (ui_spec.md secao 1.1)."""
    name = html.escape(str(cfg["ui"]["app_name"]))
    return f'<div class="fu-header"><h1>{name}</h1><p>{html.escape(texts.TAGLINE)}</p></div>'


def footer_html(service: SearchServiceProtocol) -> str:
    """Rodapé: atribuição da TMDB, aviso de log, versão e acervo (secao 1.6)."""
    return (
        '<div class="fu-footer">'
        f"<p>{html.escape(texts.TMDB_ATTRIBUTION)}</p>"
        f"<p>{html.escape(texts.LOG_NOTICE)}</p>"
        f"<p>{html.escape(texts.FOOTER_VERSION)} {html.escape(service.app_version)}"
        f" · {html.escape(texts.FOOTER_SNAPSHOT)} {html.escape(service.snapshot_id)}</p>"
        "</div>"
    )


def message_html(state: str) -> str:
    """Caixa de mensagem do estado; string vazia quando não há nada a dizer."""
    message = state_message(state)
    if not message:
        return ""
    return f'<div class="fu-message">{html.escape(message)}</div>'


# --- Grade de resultados (ui_spec.md secao 1.3) ---


def gallery_items(
    service: SearchServiceProtocol, cfg: dict, result: SearchResult
) -> list[tuple[str, str]]:
    """Itens da grade: ``(imagem, legenda)``, na ordem do ranking.

    A imagem é a URL do CDN da TMDB ou o placeholder, quando o filme não tem
    pôster (D-056). A legenda é ``Título (ano) · pontuação`` (D-054).
    """
    size = cfg["tmdb"]["poster_size"]
    decimals = cfg["ui"]["score_decimals"]
    items = []
    for hit in result.hits:
        movie = service.get_movie(hit.movie_id)
        items.append(
            (
                poster_src(movie.poster_path, size),
                caption(movie.title, movie.year, hit.score, decimals),
            )
        )
    return items


# --- Painel de detalhes (ui_spec.md secao 1.4) ---


def _poster_block(movie: Movie, size: str) -> str:
    """Pôster do painel de detalhes, ou o SVG de placeholder embutido (D-056)."""
    url = poster_url(movie.poster_path, size)
    if url is None:
        return placeholder_svg()
    return f'<img src="{html.escape(url, quote=True)}" alt="{html.escape(movie.title)}">'


def _definition(label: str, value: str | None) -> str:
    """Uma linha do painel; nada é emitido quando o dado não existe.

    Omitir é melhor que mostrar vazio ou zero: ``runtime`` ausente viraria
    "0 min", que é falso (ui_spec.md secao 1.4).
    """
    if not value:
        return ""
    return f"<dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd>"


def details_html(movie: Movie, cfg: dict) -> str:
    """Painel do filme selecionado: pôster e dados de exibição."""
    size = cfg["tmdb"]["poster_size"]
    rows = "".join(
        [
            _definition(texts.LABEL_ORIGINAL_TITLE, movie.original_title),
            _definition(texts.LABEL_RUNTIME, runtime_label(movie.runtime)),
            _definition(texts.LABEL_GENRES, ", ".join(movie.genres)),
            _definition(texts.LABEL_RATING, rating_label(movie.vote_average, movie.vote_count)),
            _definition(texts.LABEL_DIRECTOR, movie.director),
            _definition(texts.LABEL_CAST, ", ".join(movie.cast_top5)),
            f"<dt>{html.escape(texts.LABEL_OVERVIEW)}</dt>"
            f'<dd class="fu-overview">{html.escape(movie.overview)}</dd>',
        ]
    )
    year = f" ({html.escape(movie.year)})" if movie.year else ""
    tagline = (
        f'<p class="fu-hint"><em>{html.escape(movie.tagline)}</em></p>' if movie.tagline else ""
    )
    return (
        '<div class="fu-card fu-details">'
        f"<div>{_poster_block(movie, size)}</div>"
        "<div>"
        f"<h2>{html.escape(movie.title)}{year}</h2>"
        f"{tagline}"
        f"<dl>{rows}</dl>"
        "</div></div>"
    )


# --- Nível 1: onde suas palavras aparecem ---


def level1_html(movie: Movie, contributions: Sequence[TermContribution], cfg: dict) -> str:
    """Sinopse com as palavras que casaram destacadas (D-051)."""
    levels = cfg["ui"]["highlight_levels"]
    segments = highlight(movie.overview, contributions, cfg["text"])
    pieces = []
    for text, intensity in segments:
        escaped = html.escape(text)
        if intensity is None:
            pieces.append(escaped)
        else:
            level = highlight_level(intensity, levels)
            pieces.append(f'<mark class="hl-{level}">{escaped}</mark>')
    body = "".join(pieces)
    return (
        '<div class="fu-level">'
        f'<p class="fu-level-title">{html.escape(texts.LEVEL1_TITLE)}</p>'
        f'<p class="fu-hint">{html.escape(texts.LEVEL1_HINT)}</p>'
        f'<p class="fu-highlighted">{body}</p>'
        "</div>"
    )


# --- Nível 2: quanto cada palavra pesou ---


def word_label(contribution: TermContribution) -> str:
    """A palavra como a pessoa escreveu, não o radical (D-052)."""
    if contribution.surface_forms:
        return contribution.surface_forms[0]
    return contribution.stem


def rarity_badge(idf: float, threshold: float) -> str:
    """Selo de raridade da palavra no acervo (D-053). Nunca escreve "IDF"."""
    if idf >= threshold:
        return f'<span class="fu-badge fu-badge-rare">{html.escape(texts.LEVEL2_RARE)}</span>'
    return f'<span class="fu-badge fu-badge-common">{html.escape(texts.LEVEL2_COMMON)}</span>'


def level2_html(contributions: Sequence[TermContribution], cfg: dict) -> str:
    """Barras horizontais por palavra, com rótulo numérico sempre visível (D-052)."""
    decimals = cfg["ui"]["score_decimals"]
    threshold = cfg["ui"]["rare_idf_threshold"]
    if not contributions:
        body = f'<p class="fu-hint">{html.escape(texts.NO_MATCHED_WORDS)}</p>'
    else:
        largest = max(term.contribution for term in contributions)
        rows = []
        for term in contributions:
            share = (term.contribution / largest * 100) if largest > 0 else 0.0
            width = max(2.0, min(100.0, share))
            rows.append(
                "<tr>"
                f'<td class="fu-bar-word">{html.escape(word_label(term))}</td>'
                f'<td class="fu-bar-track">'
                f'<div class="fu-bar-fill" style="width: {width:.1f}%"></div></td>'
                f'<td class="fu-bar-value">{format_score(term.contribution, decimals)}</td>'
                f"<td>{rarity_badge(term.idf, threshold)}</td>"
                "</tr>"
            )
        body = (
            f'<table class="fu-bars">{"".join(rows)}</table>'
            f'<p class="fu-note">{html.escape(texts.LEVEL2_RARITY_EXPLANATION)}</p>'
        )
    return (
        '<div class="fu-level">'
        f'<p class="fu-level-title">{html.escape(texts.LEVEL2_TITLE)}</p>'
        f'<p class="fu-hint">{html.escape(texts.LEVEL2_HINT)}</p>'
        f"{body}</div>"
    )


# --- Nível 3: das palavras ao número ---


def _chips(values: Sequence[str], extra_class: str = "") -> str:
    """Lista de palavras como etiquetas; "nenhuma" quando a lista está vazia."""
    if not values:
        return f'<span class="fu-hint">{html.escape(texts.LEVEL3_NONE)}</span>'
    css = f"fu-chip {extra_class}".strip()
    return "".join(f'<span class="{css}">{html.escape(value)}</span>' for value in values)


def _step(label: str, body: str) -> str:
    return f'<li><span class="fu-step-label">{html.escape(label)}</span><br>{body}</li>'


def level3_table_html(contributions: Sequence[TermContribution], cfg: dict) -> str:
    """Tabela ``radical · peso na pergunta · peso no filme · produto`` e a soma.

    O total é a soma dos produtos em precisão cheia, só arredondada na exibição:
    é o que o torna igual, caractere a caractere, à pontuação da legenda da
    grade (D-054). Os valores das linhas, arredondados, podem somar 0,001 a
    menos ou a mais — daí a nota de arredondamento.
    """
    decimals = cfg["ui"]["score_decimals"]
    if not contributions:
        return f'<p class="fu-hint">{html.escape(texts.NO_MATCHED_WORDS)}</p>'
    total = sum(term.contribution for term in contributions)
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(term.stem)}</td>"
        f"<td>{format_score(term.q_weight, decimals)}</td>"
        f"<td>{format_score(term.d_weight, decimals)}</td>"
        f"<td>{format_score(term.contribution, decimals)}</td>"
        "</tr>"
        for term in contributions
    )
    return (
        '<table class="fu-table">'
        "<thead><tr>"
        f"<th>{html.escape(texts.LEVEL3_COL_STEM)}</th>"
        f"<th>{html.escape(texts.LEVEL3_COL_QUERY_WEIGHT)}</th>"
        f"<th>{html.escape(texts.LEVEL3_COL_DOC_WEIGHT)}</th>"
        f"<th>{html.escape(texts.LEVEL3_COL_PRODUCT)}</th>"
        "</tr></thead>"
        f"<tbody>{rows}</tbody>"
        '<tfoot><tr class="fu-total">'
        f'<td colspan="3">{html.escape(texts.LEVEL3_SUM_LABEL)}</td>'
        f'<td class="fu-total-value">{format_score(total, decimals)}</td>'
        "</tr></tfoot></table>"
        f'<p class="fu-note">{html.escape(texts.LEVEL3_ROUNDING_NOTE)}</p>'
    )


def level3_html(result: SearchResult, contributions: Sequence[TermContribution], cfg: dict) -> str:
    """Passo a passo da pergunta até a pontuação (ui_spec.md secao 1.5, nível 3)."""
    trace = result.trace
    stem_pairs = [
        f"{surfaces[0]} → {stem}" for stem, surfaces in trace.stem_to_surface.items() if surfaces
    ]
    steps = "".join(
        [
            _step(
                texts.LEVEL3_STEP_QUERY,
                _chips([result.raw_query] if result.raw_query.strip() else []),
            ),
            _step(texts.LEVEL3_STEP_STOPPED, _chips(trace.stopped)),
            _step(
                texts.LEVEL3_STEP_STEMS,
                _chips(stem_pairs)
                + f'<p class="fu-note">{html.escape(texts.LEVEL3_STEMS_HINT)}</p>',
            ),
            _step(texts.LEVEL3_STEP_OOV, _chips(result.oov_terms, "fu-chip-oov")),
            _step(texts.LEVEL3_STEP_TABLE, level3_table_html(contributions, cfg)),
        ]
    )
    return (
        '<div class="fu-level">'
        f'<p class="fu-level-title">{html.escape(texts.LEVEL3_TITLE)}</p>'
        f'<ul class="fu-steps">{steps}</ul>'
        "</div>"
    )


# --- Montagem dos painéis ---


def waiting_panels() -> Panels:
    """Painéis antes da primeira busca: os três níveis já visíveis (D-010)."""
    hint = f'<p class="fu-hint">{html.escape(texts.WAITING_FOR_SEARCH)}</p>'
    return Panels(
        details="",
        level1=f'<div class="fu-level"><p class="fu-level-title">'
        f"{html.escape(texts.LEVEL1_TITLE)}</p>{hint}</div>",
        level2=f'<div class="fu-level"><p class="fu-level-title">'
        f"{html.escape(texts.LEVEL2_TITLE)}</p>{hint}</div>",
        level3=f'<div class="fu-level"><p class="fu-level-title">'
        f"{html.escape(texts.LEVEL3_TITLE)}</p>{hint}</div>",
    )


def movie_panels(
    service: SearchServiceProtocol, cfg: dict, result: SearchResult, index: int
) -> Panels:
    """Detalhes e os três níveis para o filme na posição *index* do ranking."""
    hit: MovieHit = result.hits[index]
    movie = service.get_movie(hit.movie_id)
    contributions = service.contributions(result.effective_query, hit.doc_id)
    return Panels(
        details=details_html(movie, cfg),
        level1=level1_html(movie, contributions, cfg),
        level2=level2_html(contributions, cfg),
        level3=level3_html(result, contributions, cfg),
    )


def error_panels() -> Panels:
    """Painéis do estado "erro inesperado": mensagem genérica, nada técnico."""
    waiting = waiting_panels()
    return Panels(
        details=message_html(STATE_UNEXPECTED_ERROR),
        level1=waiting.level1,
        level2=waiting.level2,
        level3=waiting.level3,
    )


def _error_screen() -> Screen:
    """Tela do estado "erro inesperado" (ui_spec.md secao 2)."""
    return Screen(
        gallery=[],
        message=message_html(STATE_UNEXPECTED_ERROR),
        panels=error_panels(),
        result=None,
        selected=None,
        state=STATE_UNEXPECTED_ERROR,
    )


def search_screen(
    service: SearchServiceProtocol,
    cfg: dict,
    raw_query: str,
    session_id: str | None = None,
) -> Screen:
    """Executa a busca e monta a tela inteira.

    Por padrão seleciona o 1º resultado (``ui_spec.md`` secao 1.4), **sem**
    registrar clique: só a escolha explícita de um pôster é um clique (D-058).

    Qualquer exceção inesperada vira a mensagem genérica de ``ui_spec.md``
    secao 2; o detalhe técnico vai para o log do servidor, nunca para a tela.
    """
    try:
        result = service.search(raw_query, session_id=session_id)
        state = query_state(result)
        panels = movie_panels(service, cfg, result, 0) if result.hits else waiting_panels()
        return Screen(
            gallery=gallery_items(service, cfg, result),
            message=message_html(state),
            panels=panels,
            result=result,
            selected=0 if result.hits else None,
            state=state,
        )
    except Exception:
        logger.exception("Falha inesperada ao montar a tela de resultados")
        return _error_screen()


def select_panels(
    service: SearchServiceProtocol,
    cfg: dict,
    result: SearchResult | None,
    index: int | None,
    session_id: str | None = None,
) -> Panels:
    """Painéis do filme que a pessoa clicou, registrando o clique (D-058).

    ``rank`` começa em 1 e vem do próprio ``MovieHit``, não de uma contagem
    refeita aqui: é o mesmo número que a tela mostra e que o log registra.
    """
    try:
        if result is None or index is None or not (0 <= index < len(result.hits)):
            return waiting_panels()
        hit = result.hits[index]
        if session_id:
            service.log_click(session_id, hit.movie_id, hit.rank)
        return movie_panels(service, cfg, result, index)
    except Exception:
        logger.exception("Falha inesperada ao abrir um resultado")
        return error_panels()
