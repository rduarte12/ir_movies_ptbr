"""Testes de fumaça: verifica que o pacote é importável e o esqueleto está intacto."""

import importlib


def test_import_package():
    """O pacote ir_movies deve ser importável."""
    import ir_movies

    assert hasattr(ir_movies, "__version__")
    assert ir_movies.__version__ == "0.1.0"


def test_submodules_importable():
    """Todos os submódulos devem ser importáveis sem erro."""
    modules = [
        "ir_movies.config",
        "ir_movies.tmdb",
        "ir_movies.tmdb.ids",
        "ir_movies.tmdb.client",
        "ir_movies.collect",
        "ir_movies.collect.pipeline",
        "ir_movies.collect.filters",
        "ir_movies.collect.snapshot",
        "ir_movies.text",
        "ir_movies.text.preprocess",
        "ir_movies.index",
        "ir_movies.index.tfidf",
        "ir_movies.query",
        "ir_movies.query.rewriter",
        "ir_movies.query.service",
        "ir_movies.explain",
        "ir_movies.logging_jsonl",
        "ir_movies.ui",
        "ir_movies.ui.app",
    ]
    for name in modules:
        mod = importlib.import_module(name)
        assert mod is not None, f"Falha ao importar {name}"
