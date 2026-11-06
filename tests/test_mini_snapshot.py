"""Testes do acervo mínimo de testes (D-070 a D-072)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

from ir_movies.collect.snapshot import validate_snapshot
from ir_movies.config import load_config

ROOT = Path(__file__).resolve().parent.parent
MINI_DIR = ROOT / "tests" / "fixtures" / "mini_snapshot"
REAL_DIR = ROOT / "data"
MAX_MOVIES = 50


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "make_mini_snapshot", ROOT / "scripts" / "make_mini_snapshot.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def mini_meta() -> dict:
    with open(MINI_DIR / "snapshot_meta.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def mini_df(mini_meta) -> pd.DataFrame:
    return pd.read_parquet(MINI_DIR / f"movies_ptbr_{mini_meta['snapshot_id']}.parquet")


def test_mini_snapshot_is_small_and_valid(mini_df, mini_meta):
    assert 0 < len(mini_df) <= MAX_MOVIES
    assert mini_meta["accepted"] == len(mini_df)
    assert validate_snapshot(mini_df, load_config()) == []


def test_mini_snapshot_has_same_columns_as_real(mini_df, mini_meta):
    with open(REAL_DIR / "snapshot_meta.json", encoding="utf-8") as f:
        real_id = json.load(f)["snapshot_id"]
    real = pd.read_parquet(REAL_DIR / f"movies_ptbr_{real_id}.parquet")
    assert list(mini_df.columns) == list(real.columns)
    assert mini_meta["snapshot_id"] == real_id


def test_mini_snapshot_covers_edge_states(mini_df):
    assert mini_df["poster_path"].isna().any(), "falta filme sem pôster"
    assert (mini_df["tagline"] == "").any(), "falta filme sem tagline"
    assert (mini_df["runtime"] == 0).any(), "falta filme sem duração"
    assert (mini_df["director"] == "").any(), "falta filme sem direção"


def test_mini_snapshot_answers_example_queries(mini_df):
    """As consultas de exemplo da tela encontram algo no acervo mínimo."""
    script = _load_script()
    from ir_movies.index.tfidf import TfidfIndex
    from ir_movies.text.preprocess import Preprocessor

    cfg = load_config()
    docs = [script._document_text(row) for _, row in mini_df.iterrows()]
    index = TfidfIndex.build(docs, Preprocessor(cfg["text"]), cfg["tfidf"])
    for query in script.EXAMPLE_QUERIES:
        assert index.search(query, k=5), f"consulta de exemplo sem resultado: {query!r}"


def test_generation_is_deterministic(tmp_path):
    script = _load_script()
    first = script.build_mini_snapshot(REAL_DIR, tmp_path / "a")
    second = script.build_mini_snapshot(REAL_DIR, tmp_path / "b")
    for path_a, path_b in zip(first, second, strict=True):
        assert _sha256(path_a) == _sha256(path_b)


def test_committed_fixture_matches_generated(tmp_path):
    """A fixture versionada é a que o script gera hoje.

    O parquet é comparado byte a byte. O JSON é comparado pelo conteúdo: o
    controle de versão pode converter fim de linha na cópia de trabalho.
    """
    script = _load_script()
    parquet, meta = script.build_mini_snapshot(REAL_DIR, tmp_path)
    hint = "rode scripts/make_mini_snapshot.py"
    assert _sha256(parquet) == _sha256(MINI_DIR / parquet.name), f"parquet desatualizado: {hint}"
    generated = json.loads(meta.read_text(encoding="utf-8"))
    committed = json.loads((MINI_DIR / meta.name).read_text(encoding="utf-8"))
    assert generated == committed, f"snapshot_meta.json desatualizado: {hint}"


def test_generation_does_not_touch_real_snapshot(tmp_path):
    script = _load_script()
    with open(REAL_DIR / "snapshot_meta.json", encoding="utf-8") as f:
        real_id = json.load(f)["snapshot_id"]
    before = {p.name: _sha256(p) for p in REAL_DIR.iterdir() if p.is_file()}
    script.build_mini_snapshot(REAL_DIR, tmp_path / "out")
    after = {p.name: _sha256(p) for p in REAL_DIR.iterdir() if p.is_file()}
    assert before == after
    assert {p.name for p in tmp_path.rglob("*") if p.is_file()} == {
        "snapshot_meta.json",
        f"movies_ptbr_{real_id}.parquet",
    }
