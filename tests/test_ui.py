"""Testes da interface de busca e dos três níveis da Explicabilidade.

A interface é construída contra ``FakeSearchService`` (D-090), que usa o índice
e o pré-processamento reais sobre o corpus de brinquedo. Isso importa: os testes
abaixo conferem os **números** da tela contra os números do índice, e com
pontuações inventadas eles não provariam nada.

Os textos dos seis estados de ``ui_spec.md`` secao 2 aparecem aqui como literais
copiados da especificação, e não importados de ``ui/texts.py``. É deliberado:
comparar a constante com ela mesma passaria sempre, inclusive depois de alguém
trocar a mensagem sem registrar decisão.
"""

import ast
import html
import os
import re
import subprocess
import sys
from pathlib import Path

import gradio as gr
import pytest

import ir_movies
from ir_movies.config import load_config
from ir_movies.query.types import MAX_QUERY_CHARS, SearchResult
from ir_movies.ui import format as ui_format
from ir_movies.ui import view
from ir_movies.ui.app import build_app, new_session_id
from tests.fakes import FakeSearchService, MemoryQueryLogger

# --- Textos de ui_spec.md secao 2, copiados palavra por palavra ---

SPEC_EMPTY_QUERY = "Escreva algo sobre o filme que você procura."
SPEC_ONLY_STOPWORDS = (
    "Todas as suas palavras são comuns demais para ajudar a busca. "
    "Tente incluir assuntos, objetos ou lugares."
)
SPEC_NO_WORD_IN_CORPUS = (
    "Nenhuma das suas palavras aparece nas sinopses. Tente outras palavras ou sinônimos."
)
SPEC_UNEXPECTED_ERROR = "Algo deu errado. Tente de novo."
SPEC_TMDB_ATTRIBUTION = (
    "Este produto usa a API da TMDB mas não é endossado nem certificado pela TMDB"
)
SPEC_LOG_NOTICE = "As buscas são registradas de forma anônima"
SPEC_TAGLINE = "Descreva um filme do seu jeito e veja como o buscador pensa."

# Consultas com comportamento conhecido no corpus de brinquedo de 5 filmes.
QUERY_WITH_HITS = "robô apaixonado"
QUERY_ONLY_STOPWORDS = "o de a que"
QUERY_NOT_IN_CORPUS = "xyzzyx qwertyuiop"
QUERY_PARTIALLY_OOV = "robô xyzzyx"

# Filme do corpus de brinquedo sem pôster e sem duração (ver tests/fakes.py).
MOVIE_WITHOUT_POSTER = 5

_SCORE_IN_CAPTION = re.compile(r"·\s*(\d+,\d+)\s*$")
_LEVEL3_TOTAL = re.compile(r'class="fu-total-value">([^<]+)<')


@pytest.fixture
def cfg():
    return load_config()


@pytest.fixture
def service():
    return FakeSearchService.from_toy()


class BrokenService:
    """Serviço que falha em tudo, para exercitar o estado "erro inesperado".

    Não implementa o protocolo de propósito: o ponto é provar que a tela
    contém a falha em vez de propagá-la.
    """

    snapshot_id = "quebrado"
    app_version = "0.0.0"

    def search(self, *args, **kwargs):
        raise RuntimeError("falha simulada no serviço de busca")

    def contributions(self, *args, **kwargs):
        raise RuntimeError("falha simulada nas contribuições")

    def get_movie(self, *args, **kwargs):
        raise RuntimeError("falha simulada nos dados do filme")

    def log_click(self, *args, **kwargs):
        raise RuntimeError("falha simulada no log")


def score_in_caption(caption: str) -> str:
    """Extrai a pontuação exibida na legenda de um item da grade."""
    match = _SCORE_IN_CAPTION.search(caption)
    assert match, f"legenda sem pontuação ao final: {caption!r}"
    return match.group(1)


def level3_total(level3_html: str) -> str:
    """Extrai a soma dos produtos exibida no nível 3."""
    match = _LEVEL3_TOTAL.search(level3_html)
    assert match, "o nível 3 precisa exibir a soma dos produtos"
    return match.group(1)


# --- C1: build_app devolve objeto Gradio e não abre servidor ---


class TestBuildApp:
    def test_returns_a_gradio_blocks(self, service, cfg):
        assert isinstance(build_app(service, cfg), gr.Blocks)

    def test_does_not_start_a_server(self, service, cfg):
        demo = build_app(service, cfg)
        assert demo.is_running is False
        assert demo.local_url is None
        assert demo.share_url is None

    def test_never_calls_launch(self, service, cfg, monkeypatch):
        """Convenção ``IR_MOVIES_NO_LAUNCH`` de D-090: quem lança é o notebook."""

        def explode(*args, **kwargs):
            raise AssertionError("build_app não pode chamar launch()")

        monkeypatch.setattr(gr.Blocks, "launch", explode)
        assert isinstance(build_app(service, cfg), gr.Blocks)

    def test_app_name_comes_from_the_config(self, service):
        """O nome público do app é parâmetro, não literal no código (D-050)."""
        custom = {**load_config(), "ui": {**load_config()["ui"], "app_name": "Nome De Teste"}}
        assert "Nome De Teste" in view.header_html(custom)

    def test_header_carries_the_opening_sentence(self, cfg):
        assert SPEC_TAGLINE in view.header_html(cfg)

    def test_query_box_limits_three_hundred_characters(self, service, cfg):
        demo = build_app(service, cfg)
        boxes = [b for b in demo.blocks.values() if isinstance(b, gr.Textbox)]
        assert len(boxes) == 1
        assert boxes[0].max_length == MAX_QUERY_CHARS == 300

    def test_grid_has_the_configured_number_of_columns(self, service, cfg):
        demo = build_app(service, cfg)
        galleries = [b for b in demo.blocks.values() if isinstance(b, gr.Gallery)]
        assert len(galleries) == 1
        assert galleries[0].columns == cfg["ui"]["grid_columns"] == 5

    def test_clickable_examples_come_from_the_config(self, service, cfg):
        """Os exemplos de ui_spec.md secao 1.2 viram botões clicáveis (D-060)."""
        demo = build_app(service, cfg)
        labels = [b.value for b in demo.blocks.values() if isinstance(b, gr.Button)]
        assert "um tubarão assustador na praia" in labels
        assert "robô que se apaixona" in labels
        for example in cfg["ui"]["examples"][: cfg["ui"]["max_examples"]]:
            assert example in labels

    def test_session_id_is_random_per_page_load(self):
        """D-058: um número sorteado por visita, sem nada da pessoa dentro."""
        first, second = new_session_id(), new_session_id()
        assert first != second
        assert len(first) == 32 and first.isalnum()


# --- Eventos ligados de verdade no Gradio ---


def wired_fn(demo: gr.Blocks, name: str):
    """O manipulador que ``build_app`` registrou no Gradio, pelo nome.

    Chamar a função registrada — e não a de ``view`` — é o que prova que a
    ligação dos eventos existe e que o número de saídas casa com o número de
    componentes de saída. Uma troca de ordem nos ``outputs`` passaria batida
    por qualquer teste que só chamasse ``view``.
    """
    found = [fn for fn in demo.fns.values() if getattr(fn.fn, "__name__", "") == name]
    assert found, f"nenhum evento registrado com o manipulador {name}"
    return found[0]


class TestWiredEvents:
    def test_search_event_is_wired_to_every_output(self, service, cfg):
        demo = build_app(service, cfg)
        event = wired_fn(demo, "on_search")
        returned = event.fn(QUERY_WITH_HITS, "sessao-1")
        assert len(returned) == len(event.outputs) == 7
        assert isinstance(returned[-1], SearchResult)

    def test_select_event_is_wired_to_the_four_panels(self, service, cfg):
        demo = build_app(service, cfg)
        assert wired_fn(demo, "on_select").outputs, "o clique precisa de saídas"
        assert len(wired_fn(demo, "on_select").outputs) == 4

    def test_select_event_is_registered_on_the_gallery(self, service, cfg):
        demo = build_app(service, cfg)
        gallery = next(b for b in demo.blocks.values() if isinstance(b, gr.Gallery))
        targets = wired_fn(demo, "on_select").targets
        assert (gallery._id, "select") in targets

    def test_clicking_the_second_poster_logs_rank_two(self, service, cfg):
        """C9 pelo caminho real: evento do Gradio, não a função de ``view``."""
        demo = build_app(service, cfg)
        gallery = next(b for b in demo.blocks.values() if isinstance(b, gr.Gallery))
        result = wired_fn(demo, "on_search").fn("robô tubarão espaço chuva ilha", "sessao-1")[-1]
        assert len(result.hits) >= 2
        service.logger.events.clear()

        event_data = gr.SelectData(
            target=gallery, data={"index": 1, "value": None, "selected": True}
        )
        panels = wired_fn(demo, "on_select").fn("sessao-1", result, event_data)

        assert len(panels) == 4
        assert service.logger.events[0].fields == {
            "movie_id": result.hits[1].movie_id,
            "rank": 2,
        }

    def test_page_load_event_creates_the_session_id(self, service, cfg):
        demo = build_app(service, cfg)
        event = wired_fn(demo, "new_session_id")
        assert [target[1] for target in event.targets] == ["load"]
        assert event.fn() != event.fn()


# --- C6: os seis estados de ui_spec.md secao 2 ---


class TestStates:
    def test_empty_query(self, service, cfg):
        screen = view.search_screen(service, cfg, "")
        assert screen.state == view.STATE_EMPTY_QUERY
        assert SPEC_EMPTY_QUERY in screen.message
        assert screen.gallery == []

    def test_whitespace_and_punctuation_count_as_empty(self, service, cfg):
        for query in ["   ", "!!! ??? ..."]:
            screen = view.search_screen(service, cfg, query)
            assert screen.state == view.STATE_EMPTY_QUERY
            assert SPEC_EMPTY_QUERY in screen.message

    def test_only_common_words(self, service, cfg):
        screen = view.search_screen(service, cfg, QUERY_ONLY_STOPWORDS)
        assert screen.state == view.STATE_ONLY_STOPWORDS
        assert SPEC_ONLY_STOPWORDS in screen.message

    def test_no_word_in_the_collection(self, service, cfg):
        screen = view.search_screen(service, cfg, QUERY_NOT_IN_CORPUS)
        assert screen.state == view.STATE_NO_WORD_IN_CORPUS
        assert SPEC_NO_WORD_IN_CORPUS in screen.message

    def test_some_terms_out_of_the_collection_do_not_block_results(self, service, cfg):
        """Estado 4: sem mensagem; os termos aparecem no nível 3(d)."""
        screen = view.search_screen(service, cfg, QUERY_PARTIALLY_OOV)
        assert screen.state == view.STATE_OK
        assert screen.message == ""
        assert screen.gallery, "a parte conhecida da pergunta tem de trazer resultados"
        assert screen.result is not None
        assert "xyzzyx" in screen.result.oov_terms
        assert "xyzzyx" in screen.panels.level3

    def test_unexpected_error_shows_the_generic_message(self, cfg):
        screen = view.search_screen(BrokenService(), cfg, QUERY_WITH_HITS)
        assert screen.state == view.STATE_UNEXPECTED_ERROR
        assert SPEC_UNEXPECTED_ERROR in screen.message
        assert screen.gallery == []
        assert screen.result is None

    def test_unexpected_error_hides_the_technical_detail(self, cfg):
        """O detalhe técnico vai para o log do servidor, nunca para a tela."""
        screen = view.search_screen(BrokenService(), cfg, QUERY_WITH_HITS)
        rendered = screen.message + screen.panels.details + screen.panels.level3
        assert "falha simulada" not in rendered
        assert "RuntimeError" not in rendered
        assert "Traceback" not in rendered

    def test_unexpected_error_when_opening_a_result(self, service, cfg):
        """O clique também não pode estourar uma exceção na tela."""
        result = view.search_screen(service, cfg, QUERY_WITH_HITS).result
        panels = view.select_panels(BrokenService(), cfg, result, 0, "s1")
        assert SPEC_UNEXPECTED_ERROR in panels.details

    def test_out_of_range_selection_is_ignored(self, service, cfg):
        result = view.search_screen(service, cfg, QUERY_WITH_HITS).result
        for index in (-1, 999, None):
            panels = view.select_panels(service, cfg, result, index, "s1")
            assert panels.details == ""
        assert service.logger.events == []

    def test_states_are_decided_without_exceptions(self, service, cfg):
        """Regra 1 do contrato: a tela nunca descobre o estado por exceção."""
        for query in ["", QUERY_ONLY_STOPWORDS, QUERY_NOT_IN_CORPUS, QUERY_WITH_HITS]:
            assert view.query_state(service.search(query)) in {
                view.STATE_EMPTY_QUERY,
                view.STATE_ONLY_STOPWORDS,
                view.STATE_NO_WORD_IN_CORPUS,
                view.STATE_OK,
            }


# --- C7 e C8: filme sem pôster e sem duração ---


class TestEdgeCaseMovies:
    def test_movie_without_poster_uses_the_placeholder_in_the_grid(self, service, cfg):
        """C7: o corpus de brinquedo traz um filme sem pôster de propósito."""
        movie = service.get_movie(MOVIE_WITHOUT_POSTER)
        assert movie.poster_path is None
        result = service.search("ilha deserta segredos")
        assert any(h.movie_id == MOVIE_WITHOUT_POSTER for h in result.hits)
        items = view.gallery_items(service, cfg, result)
        sources = [src for src, _ in items]
        assert str(ui_format.PLACEHOLDER_PATH) in sources
        assert ui_format.PLACEHOLDER_PATH.is_file()

    def test_movie_without_poster_renders_details_without_raising(self, service, cfg):
        movie = service.get_movie(MOVIE_WITHOUT_POSTER)
        html = view.details_html(movie, cfg)
        assert "<svg" in html
        assert "image.tmdb.org" not in html
        assert movie.title in html

    def test_movie_with_poster_uses_the_tmdb_cdn(self, service, cfg):
        movie = service.get_movie(1)
        expected = f"https://image.tmdb.org/t/p/{cfg['tmdb']['poster_size']}{movie.poster_path}"
        assert expected in view.details_html(movie, cfg)
        assert expected in [
            src for src, _ in view.gallery_items(service, cfg, service.search(QUERY_WITH_HITS))
        ]

    def test_movie_without_runtime_does_not_show_a_duration(self, service, cfg):
        """C8: ``runtime is None`` some da tela, em vez de virar "0 min"."""
        movie = service.get_movie(MOVIE_WITHOUT_POSTER)
        assert movie.runtime is None
        html = view.details_html(movie, cfg)
        assert "Duração" not in html
        assert "min</dd>" not in html

    def test_movie_with_runtime_shows_a_duration(self, service, cfg):
        movie = service.get_movie(1)
        assert movie.runtime == 91
        html = view.details_html(movie, cfg)
        assert "Duração" in html
        assert "91 min" in html

    def test_zero_runtime_is_treated_as_unknown(self):
        """O snapshot usa 0 para duração desconhecida; 0 min seria falso."""
        assert ui_format.runtime_label(0) is None
        assert ui_format.runtime_label(None) is None
        assert ui_format.runtime_label(102) == "102 min"

    def test_movie_without_tagline_renders_without_raising(self, service, cfg):
        movie = service.get_movie(4)
        assert movie.tagline == ""
        assert movie.title in view.details_html(movie, cfg)

    def test_caption_without_year_omits_the_parentheses(self):
        assert ui_format.caption("Sem Data", "", 0.5) == "Sem Data · 0,500"
        assert ui_format.caption("Com Data", "1999", 0.5) == "Com Data (1999) · 0,500"


# --- C9: clique registra o rank correto ---


class TestClickLogging:
    def test_click_logs_the_one_based_rank(self, service, cfg):
        result = view.search_screen(service, cfg, "robô tubarão espaço chuva ilha").result
        assert len(result.hits) >= 2, "a consulta precisa trazer mais de um resultado"
        service.logger.events.clear()

        view.select_panels(service, cfg, result, 1, "sessao-1")

        events = service.logger.events
        assert [e.event for e in events] == ["click"]
        assert events[0].session_id == "sessao-1"
        assert events[0].fields == {"movie_id": result.hits[1].movie_id, "rank": 2}

    @pytest.mark.parametrize("index", [0, 1, 2])
    def test_rank_matches_the_position_on_screen(self, service, cfg, index):
        result = view.search_screen(service, cfg, "robô tubarão espaço chuva ilha").result
        if index >= len(result.hits):
            pytest.skip("o corpus de brinquedo não tem resultado nesta posição")
        logger = MemoryQueryLogger()
        fresh = FakeSearchService.from_toy(logger=logger)
        view.select_panels(fresh, cfg, result, index, "s1")
        assert logger.events[0].fields["rank"] == index + 1
        assert logger.events[0].fields["rank"] == result.hits[index].rank

    def test_default_selection_does_not_log_a_click(self, service, cfg):
        """D-058: o 1º resultado aparece selecionado, mas ninguém clicou nele."""
        view.search_screen(service, cfg, QUERY_WITH_HITS, "s1")
        assert [e.event for e in service.logger.events] == ["search"]

    def test_search_without_session_does_not_log(self, service, cfg):
        view.search_screen(service, cfg, QUERY_WITH_HITS)
        assert service.logger.events == []


# --- C5: os números do nível 3 batem com a pontuação da legenda ---


class TestLevelThreeNumbers:
    def test_sum_equals_the_score_in_the_caption(self, service, cfg):
        """Invariante 1 de architecture.md, do jeito que a tela a mostra."""
        screen = view.search_screen(service, cfg, QUERY_WITH_HITS)
        assert screen.gallery, "a consulta de referência precisa ter resultados"
        assert score_in_caption(screen.gallery[0][1]) == level3_total(screen.panels.level3)

    @pytest.mark.parametrize("index", [0, 1, 2])
    def test_sum_equals_the_score_for_every_result(self, service, cfg, index):
        screen = view.search_screen(service, cfg, "robô tubarão espaço chuva ilha")
        if index >= len(screen.gallery):
            pytest.skip("o corpus de brinquedo não tem resultado nesta posição")
        panels = view.select_panels(service, cfg, screen.result, index, "s1")
        assert score_in_caption(screen.gallery[index][1]) == level3_total(panels.level3)

    def test_displayed_sum_equals_the_computed_score(self, service, cfg):
        """Compara o número da tela com o número do índice, não com outro texto."""
        screen = view.search_screen(service, cfg, QUERY_WITH_HITS)
        hit = screen.result.hits[0]
        parts = service.contributions(screen.result.effective_query, hit.doc_id)
        computed = sum(part.contribution for part in parts)
        assert computed == pytest.approx(hit.score, abs=1e-9)
        expected = ui_format.format_score(computed, cfg["ui"]["score_decimals"])
        assert level3_total(screen.panels.level3) == expected
        assert score_in_caption(screen.gallery[0][1]) == expected

    def test_every_product_in_the_table_is_query_weight_times_doc_weight(self, service, cfg):
        """A tabela mostra a conta, então a conta tem de estar certa na tabela."""
        screen = view.search_screen(service, cfg, QUERY_WITH_HITS)
        hit = screen.result.hits[0]
        decimals = cfg["ui"]["score_decimals"]
        for part in service.contributions(screen.result.effective_query, hit.doc_id):
            assert part.q_weight * part.d_weight == pytest.approx(part.contribution, abs=1e-12)
            row = (
                f"<td>{part.stem}</td>"
                f"<td>{ui_format.format_score(part.q_weight, decimals)}</td>"
                f"<td>{ui_format.format_score(part.d_weight, decimals)}</td>"
                f"<td>{ui_format.format_score(part.contribution, decimals)}</td>"
            )
            assert row in screen.panels.level3

    def test_three_decimals_everywhere(self, service, cfg):
        """ui_spec.md secao 3: a mesma convenção em todos os níveis."""
        assert cfg["ui"]["score_decimals"] == 3
        screen = view.search_screen(service, cfg, QUERY_WITH_HITS)
        numbers = re.findall(r"\d+,\d+", screen.panels.level2 + screen.panels.level3)
        assert numbers
        assert all(len(value.split(",")[1]) == 3 for value in numbers)
        assert len(score_in_caption(screen.gallery[0][1]).split(",")[1]) == 3

    def test_comma_is_the_decimal_separator(self):
        assert ui_format.format_score(0.3842) == "0,384"
        assert ui_format.format_score(1.0) == "1,000"
        assert ui_format.format_score(0.0005) == "0,001"


# --- Níveis 1, 2 e 3: conteúdo ---


class TestExplainabilityPanels:
    def test_the_three_levels_are_all_present_after_a_search(self, service, cfg):
        """D-010: os três níveis ao mesmo tempo, não em abas."""
        screen = view.search_screen(service, cfg, QUERY_WITH_HITS)
        assert "1 · Onde suas palavras aparecem" in screen.panels.level1
        assert "2 · Quanto cada palavra pesou" in screen.panels.level2
        assert "3 · Das palavras ao número" in screen.panels.level3

    def test_the_three_levels_are_present_before_any_search(self):
        panels = view.waiting_panels()
        assert "1 · Onde suas palavras aparecem" in panels.level1
        assert "2 · Quanto cada palavra pesou" in panels.level2
        assert "3 · Das palavras ao número" in panels.level3

    def test_level1_highlights_the_matched_words_of_the_synopsis(self, service, cfg):
        screen = view.search_screen(service, cfg, QUERY_WITH_HITS)
        assert "<mark" in screen.panels.level1
        assert "robô" in screen.panels.level1

    def test_level1_shows_the_whole_synopsis(self, service, cfg):
        """O destaque não pode comer pedaço da sinopse (C2, visto pela tela)."""
        screen = view.search_screen(service, cfg, QUERY_WITH_HITS)
        movie = service.get_movie(screen.result.hits[0].movie_id)
        # Tirar só as marcas de destaque tem de devolver a sinopse inteira.
        without_marks = re.sub(r"</?mark[^>]*>", "", screen.panels.level1)
        assert html.escape(movie.overview) in without_marks

    def test_level2_always_shows_a_numeric_label(self, service, cfg):
        """ui_spec.md secao 3: nada depende só de cor."""
        screen = view.search_screen(service, cfg, QUERY_WITH_HITS)
        bars = screen.panels.level2.count('class="fu-bar-fill"')
        values = screen.panels.level2.count('class="fu-bar-value"')
        assert bars >= 1
        assert bars == values

    def test_level2_bar_widths_are_proportional_to_the_contribution(self, service, cfg):
        screen = view.search_screen(service, cfg, QUERY_WITH_HITS)
        widths = [float(w) for w in re.findall(r"width: ([\d.]+)%", screen.panels.level2)]
        assert widths
        assert max(widths) == 100.0
        assert all(0 < w <= 100 for w in widths)
        assert widths == sorted(widths, reverse=True)

    def test_level2_shows_a_rarity_badge_per_word(self, service, cfg):
        screen = view.search_screen(service, cfg, QUERY_WITH_HITS)
        badges = screen.panels.level2.count("fu-badge-rare") + screen.panels.level2.count(
            "fu-badge-common"
        )
        assert badges == screen.panels.level2.count('class="fu-bar-word"')

    def test_rarity_badge_follows_the_configured_threshold(self, cfg):
        threshold = cfg["ui"]["rare_idf_threshold"]
        assert "palavra rara" in view.rarity_badge(threshold, threshold)
        assert "palavra rara" in view.rarity_badge(threshold + 1.0, threshold)
        assert "palavra comum" in view.rarity_badge(threshold - 0.01, threshold)

    def test_level2_labels_the_word_the_person_typed_not_the_stem(self, service, cfg):
        """D-052: o radical é assunto do nível 3, onde é explicado."""
        screen = view.search_screen(service, cfg, "apaixonado")
        parts = service.contributions(screen.result.effective_query, screen.result.hits[0].doc_id)
        assert parts[0].stem == "apaixon"
        assert parts[0].surface_forms[0] == "apaixonado"
        assert ">apaixonado<" in screen.panels.level2

    def test_level3_lists_the_five_steps(self, service, cfg):
        screen = view.search_screen(service, cfg, "o robô apaixonado xyzzyx")
        level3 = screen.panels.level3
        assert "a) Sua pergunta" in level3
        assert "b) Palavras ignoradas por serem comuns" in level3
        assert "c) Palavras reduzidas ao radical" in level3
        assert "d) Palavras que não existem no acervo" in level3
        assert "e) Conta de cada radical" in level3

    def test_level3_shows_the_question_the_stopwords_and_the_stems(self, service, cfg):
        screen = view.search_screen(service, cfg, "o robô apaixonado")
        level3 = screen.panels.level3
        assert "o robô apaixonado" in level3
        assert ">o<" in level3, "a palavra ignorada tem de aparecer no passo (b)"
        assert "robo → rob" in level3
        assert "apaixonado → apaixon" in level3

    def test_level3_says_nenhuma_when_a_step_is_empty(self, service, cfg):
        screen = view.search_screen(service, cfg, "robô")
        assert screen.result.trace.stopped == []
        assert screen.result.oov_terms == []
        assert screen.panels.level3.count("nenhuma") >= 2

    def test_level3_table_columns_follow_the_spec(self, service, cfg):
        level3 = view.search_screen(service, cfg, QUERY_WITH_HITS).panels.level3
        for column in ["radical", "peso na pergunta", "peso no filme", "produto"]:
            assert f"<th>{column}</th>" in level3

    def test_level3_warns_about_rounding(self, service, cfg):
        """D-054: a soma é exata; as linhas estão arredondadas."""
        level3 = view.search_screen(service, cfg, QUERY_WITH_HITS).panels.level3
        assert "arredondados para 3 casas decimais" in level3

    def test_panels_without_matching_words_say_so(self, cfg):
        assert "Nenhuma palavra da sua pergunta aparece neste filme." in view.level2_html([], cfg)
        assert "Nenhuma palavra da sua pergunta aparece neste filme." in view.level3_table_html(
            [], cfg
        )

    def test_no_unexplained_jargon_on_screen(self, service, cfg):
        """ui_spec.md secao 3: "IDF" aparece como "raridade da palavra no acervo"."""
        screen = view.search_screen(service, cfg, QUERY_WITH_HITS)
        rendered = " ".join(
            [
                screen.message,
                screen.panels.details,
                screen.panels.level1,
                screen.panels.level2,
                screen.panels.level3,
            ]
        )
        for jargon in ["IDF", "idf", "TF-IDF", "cosseno", "cosine", "vetor", "token"]:
            assert jargon not in rendered, f"jargão sem explicação na tela: {jargon}"
        assert "raridade da palavra no acervo" in screen.panels.level2


# --- Rodapé e segurança do HTML ---


class TestFooterAndEscaping:
    def test_footer_has_the_tmdb_attribution(self, service):
        assert SPEC_TMDB_ATTRIBUTION in view.footer_html(service)

    def test_footer_has_the_anonymous_log_notice(self, service):
        assert SPEC_LOG_NOTICE in view.footer_html(service)

    def test_footer_has_the_version_and_the_snapshot_id(self, service):
        footer = view.footer_html(service)
        assert service.app_version in footer
        assert service.snapshot_id in footer

    def test_footer_version_comes_from_the_package(self, cfg):
        """``app_version`` vem de ``ir_movies.__version__`` pelo serviço (D-090)."""
        service = FakeSearchService.from_toy(app_version=ir_movies.__version__)
        assert ir_movies.__version__ in view.footer_html(service)

    def test_movie_text_is_escaped(self, cfg):
        """Sinopse da TMDB é dado, não marcação: ``<`` e ``&`` têm de ser escapados."""
        movies = [
            {
                "id": 1,
                "title": "Filme <b>com</b> & marcação",
                "tagline": "",
                "overview": "Uma sinopse com <script>alerta</script> e & comercial",
                "genres": ["Drama"],
            }
        ]
        service = FakeSearchService(movies)
        movie = service.get_movie(1)
        html = view.details_html(movie, cfg)
        assert "<b>" not in html
        assert "<script>" not in html
        assert "&lt;b&gt;" in html
        assert "&amp;" in html

    def test_highlighted_synopsis_is_escaped(self, cfg):
        movies = [
            {
                "id": 1,
                "title": "Teste",
                "tagline": "",
                "overview": "Um robô <b>destacado</b> & nada mais aqui nesta sinopse",
                "genres": ["Drama"],
            }
        ]
        service = FakeSearchService(movies)
        screen = view.search_screen(service, cfg, "robô")
        assert "<b>" not in screen.panels.level1
        assert "&lt;b&gt;" in screen.panels.level1
        assert "<mark" in screen.panels.level1


# --- C10: a interface só conhece o contrato ---


class TestInterfaceDependencies:
    FORBIDDEN = ("logging_jsonl", "index.tfidf", "TfidfIndex")

    def _imported_names(self, path: Path, *, runtime_only: bool = False) -> str:
        """Nomes importados pelo arquivo, como um texto só.

        Com *runtime_only*, descarta o bloco ``if TYPE_CHECKING:``: ele não roda,
        então não cria dependência — serve apenas para anotar tipos. É essa a
        distinção que importa, porque o que a regra proíbe é a interface
        **conhecer** o índice e o log em tempo de execução.
        """
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if runtime_only:
            tree.body = [
                node
                for node in tree.body
                if not (isinstance(node, ast.If) and "TYPE_CHECKING" in ast.unparse(node.test))
            ]
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.append(node.module or "")
                names.extend(alias.name for alias in node.names)
        return " ".join(names)

    def test_app_module_does_not_import_the_index_or_the_log(self):
        """Nem para anotar tipos: ``ui/app.py`` só conhece o contrato."""
        path = Path(ir_movies.__file__).parent / "ui" / "app.py"
        imported = self._imported_names(path)
        for forbidden in self.FORBIDDEN:
            assert forbidden not in imported, f"ui/app.py não pode importar {forbidden}"

    def test_no_ui_module_imports_the_index_or_the_log_at_runtime(self):
        ui_dir = Path(ir_movies.__file__).parent / "ui"
        checked = 0
        for path in sorted(ui_dir.glob("*.py")):
            imported = self._imported_names(path, runtime_only=True)
            checked += 1
            for forbidden in self.FORBIDDEN:
                assert forbidden not in imported, f"{path.name} não pode importar {forbidden}"
        assert checked >= 5, "os cinco módulos de ui/ têm de ser conferidos (D-057)"

    def test_the_helper_would_catch_a_forbidden_import(self, tmp_path):
        """Prova que o teste acima não passa por não enxergar nada."""
        sample = tmp_path / "sample.py"
        sample.write_text("from ir_movies.index.tfidf import TfidfIndex\n", encoding="utf-8")
        assert "index.tfidf" in self._imported_names(sample, runtime_only=True)

    def test_importing_the_app_does_not_load_the_log_module(self):
        """Prova em tempo de execução, não só na leitura do arquivo."""
        src = str(Path(ir_movies.__file__).parent.parent)
        env = {**os.environ, "PYTHONPATH": src}
        code = "import sys, ir_movies.ui.app;print('ir_movies.logging_jsonl' in sys.modules)"
        completed = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        assert completed.stdout.strip() == "False"

    def test_the_fake_service_is_enough_to_build_the_whole_screen(self, service, cfg):
        """Se a tela precisasse de mais que o protocolo, isto falharia."""
        from ir_movies.query.types import SearchServiceProtocol

        assert isinstance(service, SearchServiceProtocol)
        screen = view.search_screen(service, cfg, QUERY_WITH_HITS, "s1")
        assert isinstance(screen.result, SearchResult)
        assert screen.panels.details and screen.panels.level1
        assert screen.panels.level2 and screen.panels.level3
