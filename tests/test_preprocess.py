"""Testes do pré-processamento PT-BR (D-014)."""

import pytest

from ir_movies.text.preprocess import Preprocessor, PreprocessTrace

# --- Configuração padrão (espelha config.yaml seção text) ---

DEFAULT_CFG = {
    "stemmer": "snowball_pt",
    "extra_stopwords": [],
    "strip_accents": True,
}


@pytest.fixture
def prep():
    return Preprocessor(DEFAULT_CFG)


# --- Caixa ---


def test_lowercase(prep):
    """Texto em maiúsculas é normalizado."""
    tokens = prep.tokens("ROBÔ APAIXONADO")
    assert all(t == t.lower() for t in tokens)
    assert len(tokens) == 2


# --- Acentos ---


def test_accents_removed(prep):
    """Acentos são removidos antes do stemming."""
    trace = prep.trace("ação é incrível")
    # "e" vira stopword (normalizado de "é")
    assert "e" in trace.stopped
    # tokens originais não têm acentos
    assert "acao" in trace.original_tokens
    assert "incrivel" in trace.original_tokens


# --- Hífens ---


def test_hyphens_split(prep):
    """Hífens separam tokens (verificado no trace, antes de stopwords)."""
    trace = prep.trace("bem-estar")
    assert "bem" in trace.original_tokens
    assert "estar" in trace.original_tokens
    assert len(trace.original_tokens) == 2


# --- Números ---


def test_numbers_kept(prep):
    """Números são mantidos como tokens."""
    tokens = prep.tokens("2001 uma odisseia")
    assert "2001" in tokens


# --- Stopwords ---


def test_stopwords_removed(prep):
    """Stopwords do NLTK PT são removidas."""
    trace = prep.trace("o gato de um vizinho")
    assert "o" in trace.stopped
    assert "de" in trace.stopped
    assert "um" in trace.stopped


def test_accented_stopword(prep):
    """Stopwords com acento casam após normalização (ex.: 'é' → 'e')."""
    trace = prep.trace("é muito bom")
    assert "e" in trace.stopped


def test_filme_not_stopword(prep):
    """'filme' não é stopword (Q-004: extra_stopwords vazio)."""
    tokens = prep.tokens("filme brasileiro")
    assert len(tokens) == 2


# --- Consultas completas ---


def test_full_query(prep):
    """Consulta típica da UI retorna radicais esperados."""
    tokens = prep.tokens("um tubarão assustador na praia")
    # "um" e "na" são stopwords → removidos
    # sobram: tubarao, assustador, praia → stems
    assert len(tokens) == 3


def test_only_stopwords(prep):
    """Texto com só stopwords retorna lista vazia."""
    tokens = prep.tokens("o de a um uma")
    assert tokens == []


def test_empty_text(prep):
    """Texto vazio retorna lista vazia."""
    assert prep.tokens("") == []


# --- Trace ---


def test_trace_structure(prep):
    """Trace tem os campos corretos e coerentes."""
    trace = prep.trace("o robô descobre emoções")
    assert isinstance(trace, PreprocessTrace)
    # "o" é stopword
    assert "o" in trace.stopped
    # tokens restantes viraram stems
    assert len(trace.stems) == 3
    # stem_to_surface mapeia cada radical a pelo menos uma forma
    for stem in trace.stems:
        assert stem in trace.stem_to_surface
        assert len(trace.stem_to_surface[stem]) >= 1


def test_trace_consistency(prep):
    """stopped + kept == original_tokens em quantidade."""
    trace = prep.trace("o gato preto de uma casa velha")
    n_stopped = len(trace.stopped)
    n_kept = len(trace.stems)
    assert n_stopped + n_kept == len(trace.original_tokens)


def test_trace_stem_to_surface_dedup(prep):
    """Formas repetidas não duplicam no stem_to_surface."""
    trace = prep.trace("casa casa casa")
    for forms in trace.stem_to_surface.values():
        assert len(forms) == len(set(forms))


# --- Determinismo (invariante 3 de architecture.md) ---


def test_determinism(prep):
    """Mesma entrada, mesma saída."""
    text = "robô que se apaixona por uma cientista"
    assert prep.tokens(text) == prep.tokens(text)
    t1 = prep.trace(text)
    t2 = prep.trace(text)
    assert t1.stems == t2.stems
    assert t1.stopped == t2.stopped
