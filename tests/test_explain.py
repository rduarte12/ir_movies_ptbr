"""Testes do nível 1 da Explicabilidade: ``explain.highlight`` (Sprint 7).

O eixo destes testes é a garantia de que a tela mostra a sinopse **original**:
o casamento de palavras é feito sobre o texto normalizado, mas o que volta é o
texto como a TMDB o escreveu. Um destaque que "come" um acento ou troca a caixa
de uma letra é um defeito visível no projetor, e é o que ``test_lossless``
impede.
"""

import pytest

from ir_movies.explain import highlight, intensities
from ir_movies.index.tfidf import TermContribution
from tests.fakes import TEXT_CFG, FakeSearchService

QUERY_WITH_HITS = "robô apaixonado"


def term(stem: str, contribution: float, *, idf: float = 2.0) -> TermContribution:
    """Contribuição de termo com os campos que o nível 1 usa.

    ``q_weight`` e ``d_weight`` entram coerentes com ``contribution`` para que o
    objeto não minta sobre si mesmo, ainda que ``highlight`` só olhe o produto.
    """
    return TermContribution(
        stem=stem,
        surface_forms=[stem],
        idf=idf,
        q_weight=contribution,
        d_weight=1.0,
        contribution=contribution,
    )


@pytest.fixture
def service():
    return FakeSearchService.from_toy()


# --- C2: nada se perde ---


class TestLossless:
    """Concatenar os segmentos tem de reproduzir a entrada caractere a caractere."""

    @pytest.mark.parametrize(
        "text",
        [
            "Um robô apaixonado.",
            "ROBÔ, robô e Robôs: três formas.",
            "Acentuação cedilha ênfase àquela ação — travessão.",
            "Sem palavra nenhuma: !!! ??? ... 123",
            "   espaços   nas   pontas   ",
            "linha um\nlinha dois\tcom tabulação",
            "hífen-composto e aspas \"citadas\" e 'simples'",
            "<tag> & ampersand",
            "",
            "robô",
            "robô robô robô",
        ],
    )
    def test_lossless(self, text):
        segments = highlight(text, [term("rob", 0.5), term("apaixon", 0.2)], TEXT_CFG)
        assert "".join(part for part, _ in segments) == text

    def test_lossless_on_every_overview_of_the_toy_corpus(self, service):
        """Texto real do acervo de brinquedo, com as contribuições reais."""
        result = service.search(QUERY_WITH_HITS)
        assert result.hits, "a consulta de referência precisa ter resultados"
        for hit in result.hits:
            movie = service.get_movie(hit.movie_id)
            parts = service.contributions(result.effective_query, hit.doc_id)
            segments = highlight(movie.overview, parts, TEXT_CFG)
            assert "".join(part for part, _ in segments) == movie.overview

    def test_original_characters_are_preserved_in_the_highlighted_segment(self):
        """O segmento destacado carrega acento e caixa do original, não o radical."""
        segments = highlight("O ROBÔ e o Robô.", [term("rob", 0.5)], TEXT_CFG)
        highlighted = [part for part, value in segments if value is not None]
        assert highlighted == ["ROBÔ", "Robô"]


# --- C4: lista de contribuições vazia ---


class TestEmptyContributions:
    def test_single_segment_without_highlight(self):
        text = "Uma sinopse qualquer."
        assert highlight(text, [], TEXT_CFG) == [(text, None)]

    def test_empty_text_with_contributions(self):
        assert highlight("", [term("rob", 0.5)], TEXT_CFG) == [("", None)]


# --- C3: intensidades ---


class TestIntensities:
    def test_all_intensities_in_the_unit_interval(self, service):
        result = service.search(QUERY_WITH_HITS)
        for hit in result.hits:
            parts = service.contributions(result.effective_query, hit.doc_id)
            values = intensities(parts).values()
            assert values, "o filme encontrado tem de ter ao menos um termo"
            assert all(0.0 <= value <= 1.0 for value in values)

    def test_largest_contribution_gets_the_largest_intensity(self):
        parts = [term("rob", 0.6), term("apaixon", 0.3), term("cient", 0.1)]
        values = intensities(parts)
        assert values["rob"] == max(values.values()) == 1.0
        assert values["apaixon"] == pytest.approx(0.5)
        assert values["cient"] == pytest.approx(1 / 6)

    def test_largest_contribution_gets_the_largest_intensity_on_real_numbers(self, service):
        result = service.search(QUERY_WITH_HITS)
        parts = service.contributions(result.effective_query, result.hits[0].doc_id)
        assert len(parts) >= 2, "a consulta de referência precisa casar dois termos"
        top = max(parts, key=lambda part: part.contribution)
        values = intensities(parts)
        assert values[top.stem] == max(values.values())

    def test_intensities_in_the_segments_follow_the_contributions(self):
        segments = highlight(
            "Um robô apaixonado.", [term("rob", 0.6), term("apaixon", 0.3)], TEXT_CFG
        )
        marked = {part: value for part, value in segments if value is not None}
        assert marked["robô"] == 1.0
        assert marked["apaixonado"] == pytest.approx(0.5)

    def test_no_contributions_means_no_intensities(self):
        assert intensities([]) == {}

    def test_all_zero_contributions_give_zero_not_a_division_error(self):
        values = intensities([term("rob", 0.0), term("apaixon", 0.0)])
        assert values == {"rob": 0.0, "apaixon": 0.0}
        segments = highlight("Um robô.", [term("rob", 0.0)], TEXT_CFG)
        assert ("robô", 0.0) in segments


# --- Casamento por radical ---


class TestStemMatching:
    def test_matches_another_inflection_of_the_same_word(self):
        """A pergunta diz "assustador"; a sinopse diz "assustadora"."""
        segments = highlight("Uma criatura assustadora.", [term("assust", 0.5)], TEXT_CFG)
        assert ("assustadora", 1.0) in segments

    def test_surface_form_alone_would_not_be_enough(self):
        """Prova que o casamento não é por forma de superfície.

        A contribuição traz ``surface_forms = ["assustador"]``; a sinopse não
        contém essa palavra, e ainda assim a flexão é destacada.
        """
        contribution = TermContribution(
            stem="assust",
            surface_forms=["assustador"],
            idf=2.0,
            q_weight=0.5,
            d_weight=1.0,
            contribution=0.5,
        )
        text = "Uma criatura assustadora na praia."
        assert "assustador " not in text
        marked = [part for part, value in highlight(text, [contribution], TEXT_CFG) if value]
        assert marked == ["assustadora"]

    def test_unmatched_words_are_not_highlighted(self):
        segments = highlight("Um tubarão na praia.", [term("rob", 0.5)], TEXT_CFG)
        assert all(value is None for _, value in segments)
        assert len(segments) == 1

    def test_accents_do_not_block_the_match(self):
        assert ("Robô", 1.0) in highlight("Robô", [term("rob", 0.5)], TEXT_CFG)

    def test_stopword_in_the_text_is_never_highlighted(self):
        """``de`` é stopword: o pré-processamento a descarta, então não casa."""
        segments = highlight("casa de praia", [term("de", 0.5)], TEXT_CFG)
        assert all(value is None for _, value in segments)

    def test_adjacent_plain_segments_are_merged(self):
        """Segmentos vizinhos sem destaque viram um só, para não inflar o HTML."""
        segments = highlight("um robô qualquer aqui", [term("rob", 0.5)], TEXT_CFG)
        assert [value is None for _, value in segments] == [True, False, True]


# --- Configuração ---


class TestConfiguration:
    def test_uses_the_project_config_when_none_is_given(self):
        """Sem ``text_cfg``, lê a seção ``text`` do ``config.yaml``."""
        assert ("Robô", 1.0) in highlight("Robô", [term("rob", 0.5)])

    def test_preprocessor_is_reused_between_calls(self):
        """Mesma configuração não reconstrói o pré-processador (carrega stopwords)."""
        from ir_movies import explain

        explain.highlight("robô", [term("rob", 0.5)], TEXT_CFG)
        before = len(explain._PREPROCESSORS)
        explain.highlight("outro robô", [term("rob", 0.5)], TEXT_CFG)
        assert len(explain._PREPROCESSORS) == before
