"""Testes para ir_movies.config.load_config."""

from pathlib import Path

import pytest

from ir_movies.config import load_config

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_load_config_default():
    """Sem path, carrega o config.yaml da raiz do projeto."""
    cfg = load_config()
    for key in ("snapshot", "tmdb", "text", "tfidf", "search", "logging", "ui"):
        assert key in cfg


def test_load_config_valid():
    """Carrega o config.yaml real com path explícito."""
    cfg = load_config(PROJECT_ROOT / "config.yaml")
    for key in ("snapshot", "tmdb", "text", "tfidf", "search", "logging", "ui"):
        assert key in cfg


def test_load_config_returns_tmdb_section():
    """A seção tmdb contém language e retry."""
    cfg = load_config(PROJECT_ROOT / "config.yaml")
    assert cfg["tmdb"]["language"] == "pt-BR"
    assert cfg["tmdb"]["retry"]["max_attempts"] >= 1


def test_load_config_missing_file():
    """Arquivo inexistente levanta FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_config("nao_existe.yaml")


def test_load_config_missing_keys(tmp_path):
    """YAML sem chaves obrigatórias levanta ValueError."""
    bad = tmp_path / "bad.yaml"
    bad.write_text("foo: 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Chaves obrigatórias ausentes"):
        load_config(bad)
