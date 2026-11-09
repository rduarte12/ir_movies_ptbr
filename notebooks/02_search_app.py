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
# # 02 — App de busca
#
# Interface Gradio do buscador de filmes PT-BR.
# Lógica em `src/ir_movies/`. Este notebook apenas orquestra.
#
# **Seções:**
# 1. Setup (funciona no Colab e localmente)
# 2. Serviço de busca (ponto de injeção)
# 3. Interface
# 4. Log da feira (opcional, só no Colab)
#
# Para montar a tela sem abrir servidor — é o que os testes fazem —, defina
# `IR_MOVIES_NO_LAUNCH=1` no ambiente antes de executar (D-090).

# %% [markdown]
# ---
# ## Parte 1 — Setup
#
# No Colab: clona o repositório e instala `requirements-app.txt`.
# Localmente: não há nada a instalar, só o caminho do pacote a ajustar.

# %%
import os
import sys
from pathlib import Path

try:
    import google.colab  # noqa: F401

    IN_COLAB = True
except ImportError:
    IN_COLAB = False

REPO_URL = "https://github.com/rduarte12/ir_movies_ptbr.git"
REPO_NAME = "ir_movies_ptbr"

if IN_COLAB:
    repo_dir = Path("/content") / REPO_NAME
    if not repo_dir.exists():
        os.system(f"git clone --depth 1 {REPO_URL} {repo_dir}")
    os.chdir(repo_dir)
    os.system("pip install -q -r requirements-app.txt")
    project_root = repo_dir
else:
    # Notebook roda em notebooks/; a raiz do projeto é o diretório acima.
    project_root = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()

src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

print(f"Colab: {IN_COLAB}")
print(f"Raiz do projeto: {project_root}")

# %%
# Os imports do pacote vêm depois do setup, de propósito: no Colab o
# repositório só existe a partir da célula anterior.
import ir_movies  # noqa: E402
from ir_movies.config import load_config  # noqa: E402
from ir_movies.ui.app import build_app  # noqa: E402
from ir_movies.ui.format import format_score  # noqa: E402
from ir_movies.ui.styles import FORCE_LIGHT_JS  # noqa: E402

cfg = load_config(project_root / "config.yaml")

print(f"Versão do app: {ir_movies.__version__}")
print(f"Nome do app:   {cfg['ui']['app_name']}")
print(f"Resultados:    {cfg['search']['top_k']} por busca")

# %% [markdown]
# ---
# ## Parte 2 — Serviço de busca
#
# ### PONTO DE INJEÇÃO
#
# A interface depende **somente** de `SearchServiceProtocol` e recebe o serviço
# por injeção (D-090): não conhece o índice TF-IDF nem o arquivo de log. Por
# isso o serviço é montado aqui, fora da interface, e não dentro dela.
#
# Duas formas de fornecê-lo, nesta ordem:
#
# 1. definir a variável `service` **antes** de executar a célula abaixo — é o
#    que um teste automatizado faz, com um serviço sobre um acervo pequeno;
# 2. deixar a célula montar o `SearchService` real, que lê o snapshot de `data/`.
#
# Carregar o snapshot e construir o índice leva alguns segundos. É a única
# etapa lenta do notebook: a busca em si é instantânea.

# %%
if "service" not in globals():
    from ir_movies.query.service import SearchService

    # from_config tenta carregar a etapa semântica quando semantic.enabled = true
    # e cai para TF-IDF puro com aviso no log se os vetores não existirem (D-097).
    service = SearchService.from_config(project_root / "config.yaml")

print(f"Acervo:  {service.snapshot_id}")
print(f"Versão:  {service.app_version}")

# %% [markdown]
# Conferência rápida antes de abrir a tela: uma busca de exemplo, sem registrar
# nada no log (sem `session_id`, o serviço não registra — regra 4 de D-090).

# %%
exemplo = cfg["ui"]["examples"][0]
previa = service.search(exemplo)

print(f'Pergunta: "{exemplo}"')
print(f"Resultados: {len(previa.hits)} em {previa.latency_ms:.1f} ms")
for hit in previa.hits[:5]:
    filme = service.get_movie(hit.movie_id)
    pontuacao = format_score(hit.score, cfg["ui"]["score_decimals"])
    print(f"  {hit.rank:>2}. {filme.title} ({filme.year}) · {pontuacao}")

# %% [markdown]
# ---
# ## Parte 3 — Interface
#
# `build_app` monta e devolve o objeto Gradio; quem lança é este notebook, e só
# quando `IR_MOVIES_NO_LAUNCH` não vale exatamente `"1"` (D-090). É isso que
# permite testar a montagem da tela sem abrir servidor nenhum.

# %%
demo = build_app(service, cfg)

if os.environ.get("IR_MOVIES_NO_LAUNCH") != "1":
    demo.launch(share=True, inline=False, js=FORCE_LIGHT_JS)
else:
    print("Tela montada; lançamento desativado por IR_MOVIES_NO_LAUNCH=1.")

# %% [markdown]
# ---
# ## Parte 4 — Log da feira (opcional)
#
# O log fica no disco da máquina que roda o notebook (Q-001). No Colab, a
# célula abaixo compacta a pasta `logs/` e oferece o download — o arquivo
# **tem de ser baixado antes de a sessão do Colab terminar**, senão o disco é
# descartado com ele. Fora do Colab, a célula só diz onde os arquivos estão.
#
# O log é anônimo: não há IP, identificação de navegador nem dado pessoal
# nenhum (D-008).

# %%
logs_dir = project_root / cfg["logging"]["dir"]
arquivos = sorted(logs_dir.glob("*.jsonl")) if logs_dir.is_dir() else []

if not arquivos:
    print(f"Nenhum log em {logs_dir}.")
elif IN_COLAB:
    import shutil

    from google.colab import files  # noqa: PLC0415

    pacote = shutil.make_archive(str(project_root / "logs_feira"), "zip", logs_dir)
    print(f"{len(arquivos)} arquivo(s) compactado(s) em {pacote}")
    files.download(pacote)
else:
    total = sum(1 for arquivo in arquivos for _ in arquivo.open(encoding="utf-8"))
    print(f"{len(arquivos)} arquivo(s) de log em {logs_dir}, {total} evento(s).")
    for arquivo in arquivos:
        print(f"  {arquivo.name}")
