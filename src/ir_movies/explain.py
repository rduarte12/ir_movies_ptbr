"""Explicabilidade: destaque de palavras na sinopse proporcional à contribuição.

Esta é a base do **nível 1** da seção Explicabilidade (D-010): a sinopse do filme
com as palavras que casaram com a pergunta destacadas, mais forte quanto mais a
palavra somou à pontuação (D-051).

Duas exigências moldam o módulo:

1. **Nada se perde.** Concatenar os segmentos devolvidos reproduz o texto de
   entrada caractere a caractere — acentos, caixa, pontuação e espaços. A tela
   mostra a sinopse que a TMDB escreveu, não uma versão normalizada dela.
2. **O casamento é por radical.** "assustador" na pergunta tem de destacar
   "assustadora" na sinopse, porque é isso que o índice faz. Então o texto da
   sinopse passa pelo *mesmo* pré-processamento (minúsculas, sem acento,
   stemming Snowball) só para **decidir** o que destacar; o segmento devolvido
   carrega o pedaço original do texto.

``TermContribution.surface_forms`` guarda as palavras da pergunta e serve de
rótulo no nível 2, mas não basta aqui: são as formas que a *pessoa* escreveu, e
a sinopse costuma usar outra flexão da mesma palavra.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ir_movies.config import load_config
from ir_movies.text.preprocess import Preprocessor

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ir_movies.index.tfidf import TermContribution

__all__ = ["Segment", "highlight", "intensities"]

Segment = tuple[str, float | None]
"""Um pedaço do texto e a intensidade do destaque (``None`` = sem destaque)."""

# Uma "palavra" do texto original: letras e números seguidos, na mesma ideia da
# tokenização do pré-processamento (D-028) — hífen, pontuação e espaço separam.
# Note que o casamento abaixo é feito palavra por palavra, e não por posição no
# texto normalizado: remover acentos pode mudar o comprimento da string (``æ``
# vira ``ae``), e aí as posições não serviriam para recortar o texto original.
_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)

_PREPROCESSORS: dict[tuple, Preprocessor] = {}


def _config_key(text_cfg: dict) -> tuple:
    """Chave imutável para guardar um ``Preprocessor`` já construído."""
    return tuple(
        sorted(
            (key, tuple(value) if isinstance(value, list) else value)
            for key, value in text_cfg.items()
        )
    )


def _preprocessor(text_cfg: dict | None) -> Preprocessor:
    """Devolve o pré-processador da configuração dada, construído uma só vez.

    Sem *text_cfg*, usa a seção ``text`` do ``config.yaml`` — a mesma que o
    índice usa, que é o que garante o casamento por radical. Construir um
    ``Preprocessor`` carrega as stopwords, então o resultado fica guardado.
    """
    if text_cfg is None:
        text_cfg = load_config()["text"]
    key = _config_key(text_cfg)
    if key not in _PREPROCESSORS:
        _PREPROCESSORS[key] = Preprocessor(text_cfg)
    return _PREPROCESSORS[key]


def intensities(contributions: Sequence[TermContribution]) -> dict[str, float]:
    """Intensidade de destaque por radical, em ``[0, 1]`` (D-051).

    A escala é linear e relativa ao filme exibido: o termo que mais contribuiu
    recebe 1.0 e os outros, a fração correspondente. Se todas as contribuições
    forem zero, todo radical recebe 0.0 — casou, mas não somou nada.
    """
    if not contributions:
        return {}
    largest = max(term.contribution for term in contributions)
    if largest <= 0:
        return {term.stem: 0.0 for term in contributions}
    return {term.stem: min(1.0, max(0.0, term.contribution / largest)) for term in contributions}


def _merge(segments: list[Segment]) -> list[Segment]:
    """Junta segmentos vizinhos de mesma intensidade e descarta os vazios."""
    merged: list[Segment] = []
    for text, value in segments:
        if not text:
            continue
        if merged and merged[-1][1] == value:
            merged[-1] = (merged[-1][0] + text, value)
        else:
            merged.append((text, value))
    return merged


def highlight(
    text: str,
    contributions: Sequence[TermContribution],
    text_cfg: dict | None = None,
) -> list[Segment]:
    """Divide *text* em segmentos, marcando as palavras que casam por radical.

    Devolve uma lista de pares ``(pedaço do texto, intensidade)``, onde a
    intensidade é ``None`` nos pedaços sem destaque e um número em ``[0, 1]``
    nas palavras que casaram, proporcional à contribuição do termo (D-051).

    Garantia verificada em teste: ``"".join(t for t, _ in highlight(...)) == text``.

    Sem contribuições, devolve um único segmento sem destaque — é o caso de um
    filme que apareceu por outros termos, ou de uma pergunta sem resultado.
    """
    by_stem = intensities(contributions)
    if not by_stem or not text:
        return [(text, None)]

    preprocessor = _preprocessor(text_cfg)
    segments: list[Segment] = []
    cursor = 0

    for match in _WORD_RE.finditer(text):
        # ``tokens`` aplica normalização, stopwords e stemming. Uma palavra sozinha
        # vira exatamente um radical; lista vazia é stopword, e mais de um radical
        # só acontece quando a remoção de acento parte a palavra (caso raro).
        stems = preprocessor.tokens(match.group(0))
        if len(stems) != 1:
            continue
        value = by_stem.get(stems[0])
        if value is None:
            continue
        if match.start() > cursor:
            segments.append((text[cursor : match.start()], None))
        segments.append((match.group(0), value))
        cursor = match.end()

    if cursor < len(text):
        segments.append((text[cursor:], None))

    return _merge(segments) or [(text, None)]
