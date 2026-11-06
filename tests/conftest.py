"""Configuração compartilhada do pytest."""

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def toy_corpus():
    """Carrega o corpus de brinquedo para testes de TF-IDF."""
    path = FIXTURES_DIR / "toy_corpus.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)
