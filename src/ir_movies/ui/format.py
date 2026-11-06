"""Formatação de números, legendas e endereços de pôster para a tela.

Uma função só por convenção, para que a convenção não possa divergir entre os
blocos da tela. A regra que importa é a de ``ui_spec.md`` secao 3: a pontuação
aparece sempre com o mesmo número de casas decimais, nos três níveis da
Explicabilidade e na legenda da grade (D-054).
"""

from __future__ import annotations

from pathlib import Path

from ir_movies.ui import texts

# Endereço do CDN da TMDB (``architecture.md`` secao 4). O projeto não baixa
# pôster nenhum: monta a URL e deixa o navegador buscar a imagem.
POSTER_BASE_URL = "https://image.tmdb.org/t/p/"

# Pôster ausente (D-056). SVG é texto: o Gradio lê o arquivo local e o embute na
# página, então o placeholder não depende de rede nem de pasta servida.
PLACEHOLDER_PATH = Path(__file__).parent / "assets" / "no_poster.svg"


def format_score(value: float, decimals: int = 3) -> str:
    """Formata uma pontuação ou contribuição com vírgula decimal (D-054).

    >>> format_score(0.3842)
    '0,384'
    """
    return f"{value:.{decimals}f}".replace(".", ",")


def poster_url(poster_path: str | None, size: str) -> str | None:
    """URL da imagem no CDN da TMDB, ou ``None`` quando o filme não tem pôster."""
    if not poster_path:
        return None
    return f"{POSTER_BASE_URL}{size}{poster_path}"


def poster_src(poster_path: str | None, size: str) -> str:
    """Imagem a exibir: a URL do CDN ou o caminho do placeholder (D-056)."""
    return poster_url(poster_path, size) or str(PLACEHOLDER_PATH)


def placeholder_svg() -> str:
    """Conteúdo do SVG de pôster ausente, para embutir direto no HTML."""
    return PLACEHOLDER_PATH.read_text(encoding="utf-8")


def caption(title: str, year: str, score: float, decimals: int = 3) -> str:
    """Legenda de um item da grade: ``Título (ano) · pontuação``.

    Sem ano conhecido, o parêntese é omitido em vez de mostrar vazio.
    """
    head = f"{title} ({year})" if year else title
    return f"{head} · {format_score(score, decimals)}"


def runtime_label(runtime: int | None) -> str | None:
    """Duração em minutos, ou ``None`` quando desconhecida.

    ``None`` faz a linha de duração desaparecer do painel de detalhes: melhor
    omitir do que afirmar "0 min", que seria falso (``ui_spec.md`` secao 1.4).
    """
    if not runtime:
        return None
    return f"{runtime} {texts.RUNTIME_UNIT}"


def rating_label(vote_average: float, vote_count: int) -> str:
    """Nota da TMDB com o número de votos, que é o que a torna interpretável."""
    return f"{vote_average:.1f}".replace(".", ",") + f" ({vote_count} {texts.RATING_VOTES})"


def highlight_level(intensity: float, levels: int) -> int:
    """Faixa de cor de um destaque, de 1 (mais fraca) a *levels* (D-051).

    A intensidade é contínua, mas num projetor variação contínua de cor não se
    distingue: as faixas discretas são o que torna "esta palavra pesou mais"
    legível a distância.
    """
    levels = max(1, levels)
    value = min(1.0, max(0.0, intensity))
    return min(levels, int(value * levels) + 1)
