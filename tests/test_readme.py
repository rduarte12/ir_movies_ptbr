"""Garante que o README mantém os avisos obrigatórios e as informações de reprodução (D-074)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def readme() -> str:
    return (ROOT / "README.md").read_text(encoding="utf-8")


def test_readme_has_exact_tmdb_attribution(readme):
    assert "Este produto usa a API da TMDB mas não é endossado nem certificado pela TMDB" in readme


def test_readme_has_anonymous_log_notice(readme):
    assert "As buscas são registradas de forma anônima" in readme
    assert "Nenhum dado pessoal é guardado" in readme


def test_readme_mentions_python_version_and_requirements_files(readme):
    assert ">=3.13,<3.14" in readme
    for name in ("requirements-app.txt", "requirements-collect.txt", "requirements-dev.txt"):
        assert name in readme
        assert (ROOT / name).exists(), f"{name} citado no README mas não existe"


def test_readme_mentions_current_snapshot(readme):
    meta = json.loads((ROOT / "data" / "snapshot_meta.json").read_text(encoding="utf-8"))
    assert meta["snapshot_id"] in readme
    assert f"{meta['accepted']:,}".replace(",", ".") in readme


def test_readme_local_links_exist(readme):
    """Todo link relativo para arquivo do repositório aponta para algo que existe."""
    targets = re.findall(r"\]\(((?!https?://|#)[^)\s]+)\)", readme)
    assert targets, "o README deveria linkar a documentação do projeto"
    for target in targets:
        assert (ROOT / target.split("#")[0]).exists(), f"link quebrado no README: {target}"


def test_rehearsal_checklist_covers_required_topics():
    """O roteiro cobre ensaio de 2 h, desconexão do Colab, plano B e pessoas leigas (D-075)."""
    text = (ROOT / "docs" / "rehearsal_checklist.md").read_text(encoding="utf-8")
    for heading in (
        "## B. Ensaio de 2 horas contínuas no Colab",
        "## C. Plano B: Jupyter local",
        "## D. Teste dos textos com 2 ou 3 pessoas leigas",
        "## E. Se o Colab cair no meio da feira",
    ):
        assert heading in text, f"seção ausente no roteiro: {heading}"
    assert "B3. Registro de desconexões e de lentidão" in text
