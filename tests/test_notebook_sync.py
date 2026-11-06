"""Garante que cada notebook .py (percent) está sincronizado com o seu .ipynb (D-077).

O README manda abrir o .ipynb (Colab e Jupyter), enquanto o teste de fumaça
executa o .py. Este teste fecha a lacuna: se os dois divergirem, ele falha e
indica o comando que resolve (``python -m jupytext --sync notebooks/*.py``).
"""

from __future__ import annotations

from pathlib import Path

import jupytext
import pytest

NOTEBOOKS_DIR = Path(__file__).resolve().parent.parent / "notebooks"
PY_NOTEBOOKS = sorted(NOTEBOOKS_DIR.glob("*.py"))


def _cells(path: Path) -> list[tuple[str, str]]:
    """(tipo, texto) de cada célula; ignora saídas, metadados e contadores de execução."""
    notebook = jupytext.read(path)
    return [(cell.cell_type, cell.source.strip()) for cell in notebook.cells]


def test_there_are_notebooks_to_check():
    assert PY_NOTEBOOKS, "nenhum notebook .py encontrado em notebooks/"


@pytest.mark.parametrize("py_path", PY_NOTEBOOKS, ids=lambda p: p.name)
def test_py_and_ipynb_are_in_sync(py_path):
    ipynb_path = py_path.with_suffix(".ipynb")
    assert ipynb_path.exists(), f"falta o par {ipynb_path.name}"
    assert _cells(py_path) == _cells(ipynb_path), (
        f"{py_path.name} e {ipynb_path.name} divergem: "
        "rode `python -m jupytext --sync notebooks/*.py`"
    )
