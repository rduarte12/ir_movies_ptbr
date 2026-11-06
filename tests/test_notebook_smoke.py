"""Teste de fumaça do notebook 02 sobre o acervo mínimo (D-072, D-073).

Prova que "Run all" não quebra e que nenhum servidor é aberto, sem exigir
dependência além das já fixadas em ``requirements-dev.txt``: o par jupytext é
lido com ``jupytext`` e as células de código são executadas, em ordem, num
subprocesso. Detalhes e limitações em ``docs/decisions.md`` (D-072).

Como o teste isola o ambiente:

- monta numa pasta temporária um mini-projeto (``src/``, ``config.yaml``, o
  notebook e o acervo mínimo em ``data/``); ``PROJECT_ROOT`` é derivado da
  localização do pacote, então o notebook enxerga o acervo mínimo como o
  ``data/`` do projeto e grava os logs na pasta temporária;
- define ``IR_MOVIES_NO_LAUNCH=1`` (convenção de D-090);
- troca ``gradio.Blocks.launch`` por uma função que levanta erro: se alguma
  célula tentar abrir servidor, o teste falha.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK = ROOT / "notebooks" / "02_search_app.py"
MINI_SNAPSHOT_DIR = ROOT / "tests" / "fixtures" / "mini_snapshot"
TIMEOUT_SECONDS = 180

# Executado no subprocesso. Equivale a "Run all": lê o par jupytext e executa as
# células de código, em ordem, num único espaço de nomes.
_DRIVER = """
import sys

import gradio
import jupytext

notebook_path = sys.argv[1]
blocks_created = []
original_init = gradio.Blocks.__init__


def counting_init(self, *args, **kwargs):
    blocks_created.append(self)
    original_init(self, *args, **kwargs)


def forbidden_launch(self, *args, **kwargs):
    raise RuntimeError("Blocks.launch foi chamado com IR_MOVIES_NO_LAUNCH=1")


gradio.Blocks.__init__ = counting_init
gradio.Blocks.launch = forbidden_launch

notebook = jupytext.read(notebook_path)
namespace = {"__name__": "__main__"}
executed = 0
for number, cell in enumerate(notebook.cells):
    if cell.cell_type != "code":
        continue
    # Magics e comandos de shell (instalação de dependências) são passos do Colab.
    lines = [ln for ln in cell.source.splitlines() if not ln.lstrip().startswith(("%", "!"))]
    source = "\\n".join(lines)
    if not source.strip():
        continue
    exec(compile(source, f"<celula {number}>", "exec"), namespace)
    executed += 1

print(f"CELLS_EXECUTED={executed}")
print(f"BLOCKS_CREATED={len(blocks_created)}")
"""


def build_mini_project(dest: Path, notebook: Path = NOTEBOOK) -> Path:
    """Monta em *dest* um mini-projeto para executar *notebook*; devolve o caminho da cópia."""
    shutil.copytree(
        ROOT / "src", dest / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    shutil.copy2(ROOT / "config.yaml", dest / "config.yaml")
    shutil.copytree(MINI_SNAPSHOT_DIR, dest / "data")
    (dest / "logs").mkdir()
    (dest / "notebooks").mkdir()
    copied = dest / "notebooks" / notebook.name
    shutil.copy2(notebook, copied)
    return copied


def run_notebook(project: Path, notebook: Path) -> subprocess.CompletedProcess:
    """Executa as células de *notebook* num subprocesso, com o projeto mínimo no caminho."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(project / "src")
    env["IR_MOVIES_NO_LAUNCH"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("TMDB_READ_ACCESS_TOKEN", None)  # o notebook 02 não usa a API da TMDB
    driver = project / "run_notebook_driver.py"
    driver.write_text(_DRIVER, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(driver), str(notebook)],
        cwd=notebook.parent,  # como no Jupyter: diretório de trabalho = pasta do notebook
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=TIMEOUT_SECONDS,
    )


def parse_counter(stdout: str, name: str) -> int:
    for line in stdout.splitlines():
        if line.startswith(f"{name}="):
            return int(line.split("=", 1)[1])
    raise AssertionError(f"{name} ausente na saída do notebook:\n{stdout}")


def test_notebook_02_run_all_without_launching_server(tmp_path):
    notebook = build_mini_project(tmp_path)

    result = run_notebook(tmp_path, notebook)

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert parse_counter(result.stdout, "CELLS_EXECUTED") >= 1
    # A interface foi de fato montada...
    assert parse_counter(result.stdout, "BLOCKS_CREATED") >= 1
    # ...e `launch` não foi chamado (se fosse, o subprocesso teria falhado acima).
    assert "Running on" not in result.stdout + result.stderr
