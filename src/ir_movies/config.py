"""Carrega e valida config.yaml."""

from pathlib import Path

import yaml

_REQUIRED_KEYS = ("snapshot", "tmdb", "text", "tfidf", "search", "logging", "ui")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_config(path: str | Path | None = None) -> dict:
    """Lê *path* (YAML) e devolve o dicionário de configuração validado.

    Se *path* não for informado, usa ``config.yaml`` na raiz do projeto.
    """
    if path is None:
        path = PROJECT_ROOT / "config.yaml"
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    missing = [k for k in _REQUIRED_KEYS if k not in cfg]
    if missing:
        raise ValueError(f"Chaves obrigatórias ausentes em {path}: {missing}")
    return cfg
