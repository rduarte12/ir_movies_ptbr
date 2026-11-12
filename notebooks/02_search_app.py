# ---
# jupyter:
#   jupytext:
#     formats: py:percent,ipynb
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.6
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # FilmUSP — buscador de filmes que mostra como pensa
#
# Descreva um filme do seu jeito ("um tubarão assustador na praia") e veja os filmes que mais
# combinam e **por que** cada um apareceu.
#
# ## Como rodar no Google Colab
#
# 1. Menu **Ambiente de execução → Executar tudo** (não precisa de GPU).
# 2. Espere de 3 a 5 minutos na primeira vez: o notebook baixa o projeto, instala as
#    bibliotecas que faltam no Colab e baixa o modelo de linguagem (cerca de 470 MB).
# 3. Na célula 4 aparece um link `https://….gradio.live`. Clique nele para abrir o app.
#
# Nada é pedido durante a execução: não há login nem chave de API.
#
# O mesmo notebook roda num Jupyter local (veja o `README.md`).

# %% [markdown]
# ## 1. Preparar o ambiente
#
# No Colab, baixa o repositório e instala `requirements-colab.txt`. Num Jupyter local, só ajusta
# o caminho do pacote (as bibliotecas vêm de `requirements-app.txt`).

# %%
import os
import subprocess
import sys
from pathlib import Path

try:
    import google.colab  # noqa: F401

    IN_COLAB = True
except ImportError:
    IN_COLAB = False

REPO_URL = "https://github.com/rduarte12/ir_movies_ptbr.git"


def run(cmd: list[str]) -> None:
    """Executa um comando e para o notebook com a mensagem de erro, se ele falhar."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Falhou: {' '.join(cmd)}\n{result.stdout}\n{result.stderr}")


if IN_COLAB:
    project_root = Path("/content/ir_movies_ptbr")
    if project_root.exists():
        run(["git", "-C", str(project_root), "pull", "--ff-only"])
    else:
        run(["git", "clone", "--depth", "1", REPO_URL, str(project_root)])
    os.chdir(project_root)
    print("Instalando bibliotecas (1 a 2 minutos)...")
    run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements-colab.txt"])
else:
    # Num Jupyter local, o notebook roda em notebooks/; a raiz do projeto é a pasta acima.
    project_root = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()

if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

print(f"Rodando no Colab: {IN_COLAB}")
print(f"Pasta do projeto: {project_root}")

# %% [markdown]
# ## 2. Carregar os filmes e o buscador
#
# Lê o acervo (8 mil filmes com sinopse em português), monta o índice de palavras (TF-IDF) e
# carrega o modelo de linguagem com os vetores de características já calculados. Na primeira
# vez, o modelo é baixado da internet. Se ele não carregar, o buscador continua funcionando só
# com as palavras.

# %%
import ir_movies  # noqa: E402
from ir_movies.config import load_config  # noqa: E402
from ir_movies.ui.app import build_app  # noqa: E402
from ir_movies.ui.format import format_score  # noqa: E402
from ir_movies.ui.styles import FORCE_LIGHT_JS  # noqa: E402

cfg = load_config(project_root / "config.yaml")

# Um teste automático pode entregar o próprio serviço antes desta célula (D-090).
if "service" not in globals():
    from ir_movies.query.service import SearchService

    service = SearchService.from_config(project_root / "config.yaml")

modo = "palavras + sentido" if getattr(service, "semantic_active", False) else "só palavras"
print(f"FilmUSP {ir_movies.__version__} · acervo {service.snapshot_id} · busca por {modo}")

# %% [markdown]
# ## 3. Uma busca de teste
#
# Confere que tudo funciona antes de abrir a tela. Esta busca não entra no registro de uso.

# %%
exemplo = cfg["ui"]["examples"][0]
previa = service.search(exemplo)

print(f'Busca: "{exemplo}" · {len(previa.hits)} resultados em {previa.latency_ms:.0f} ms\n')
for hit in previa.hits[:5]:
    filme = service.get_movie(hit.movie_id)
    pontuacao = format_score(hit.score, cfg["ui"]["score_decimals"])
    print(f"  {hit.rank}º  {filme.title} ({filme.year})  · pontuação {pontuacao}")

# %% [markdown]
# ## 4. Abrir o app
#
# Clique no link `https://….gradio.live` que aparece abaixo. Ele fica ativo enquanto este
# notebook estiver aberto.

# %%
demo = build_app(service, cfg)

# IR_MOVIES_NO_LAUNCH=1 monta a tela sem abrir servidor; é o que os testes usam (D-090).
if os.environ.get("IR_MOVIES_NO_LAUNCH") != "1":
    demo.launch(share=True, inline=False, js=FORCE_LIGHT_JS)
else:
    print("Tela montada; abertura desativada por IR_MOVIES_NO_LAUNCH=1.")

# %% [markdown]
# ## 5. (Opcional) Baixar o registro de uso
#
# Só para quem apresentou o app na feira. O registro é anônimo (sem nenhum dado pessoal) e fica
# no disco do Colab, que é apagado ao fechar a sessão. Para baixar, troque `BAIXAR_REGISTRO`
# para `True` e execute esta célula.

# %%
BAIXAR_REGISTRO = False

logs_dir = project_root / cfg["logging"]["dir"]
arquivos = sorted(logs_dir.glob("*.jsonl")) if logs_dir.is_dir() else []

if not BAIXAR_REGISTRO:
    print(f"{len(arquivos)} arquivo(s) de registro em {logs_dir}.")
elif not arquivos:
    print("Ainda não há registro para baixar.")
elif IN_COLAB:
    import shutil

    from google.colab import files  # noqa: PLC0415

    pacote = shutil.make_archive(str(project_root / "registro_feira"), "zip", logs_dir)
    files.download(pacote)
else:
    print("Fora do Colab, os arquivos já estão nesta pasta:")
    for arquivo in arquivos:
        print(f"  {arquivo}")
