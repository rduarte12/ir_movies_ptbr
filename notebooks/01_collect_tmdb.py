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
# # 01 — Coleta TMDB
#
# Notebook de coleta de dados da TMDB.
# Lógica em `src/ir_movies/`. Este notebook apenas orquestra.
#
# **Pré-requisito:** `.env` com `TMDB_READ_ACCESS_TOKEN` preenchido.

# %% [markdown]
# ## Setup

# %%
import os
from datetime import date

from dotenv import load_dotenv

from ir_movies.config import PROJECT_ROOT, load_config
from ir_movies.tmdb.client import TmdbClient
from ir_movies.tmdb.ids import download_id_export, load_candidates

load_dotenv(PROJECT_ROOT / ".env")

cfg = load_config()
token = os.environ["TMDB_READ_ACCESS_TOKEN"]
print(f"Config carregado. Idioma: {cfg['tmdb']['language']}")

# %% [markdown]
# ## Download do export diário de IDs
#
# O export é um arquivo gzipped JSONL com todos os IDs de filmes da TMDB,
# publicado diariamente (~8h UTC). Não requer autenticação (D-022).

# %%
export_path = download_id_export(date.today(), PROJECT_ROOT / "data" / "raw")
print(f"Export salvo em: {export_path}")

# %% [markdown]
# ## Carregar candidatos
#
# Lemos o export, excluímos filmes adultos (D-004) e ordenamos por
# popularidade decrescente (D-003).

# %%
candidates = load_candidates(export_path)
print(f"Total de candidatos (sem adult): {len(candidates):,}")
print("\nTop 10 por popularidade:")
for movie_id, pop in candidates[:10]:
    print(f"  id={movie_id:>8}  popularity={pop:.2f}")

# %% [markdown]
# ## Buscar detalhes de 50 filmes
#
# Testamos o cliente TMDB com uma amostra pequena. O Sprint 2 escala para
# 20.000 com filtros, checkpoint e snapshot.

# %%
SAMPLE_SIZE = 50

movies = []
errors = []

with TmdbClient(token=token, cfg=cfg) as client:
    for i, (movie_id, _pop) in enumerate(candidates[:SAMPLE_SIZE]):
        try:
            movie = client.get_movie(movie_id)
            movies.append(movie)
        except Exception as e:
            errors.append((movie_id, str(e)))
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{SAMPLE_SIZE} buscados...")

print(f"\nBuscados: {len(movies)} filmes, {len(errors)} erros")
if errors:
    print("Erros:", errors[:5])

# %% [markdown]
# ## Exibir 3 exemplos
#
# Visualização rápida dos dados retornados pela API.

# %%
for movie in movies[:3]:
    genres = ", ".join(g["name"] for g in movie.get("genres", []))
    overview = movie.get("overview", "")
    if len(overview) > 200:
        overview = overview[:200] + "..."
    print(f"{'=' * 60}")
    print(f"  ID:          {movie['id']}")
    print(f"  Título:      {movie.get('title', '?')}")
    print(f"  Original:    {movie.get('original_title', '?')}")
    print(f"  Gêneros:     {genres}")
    print(f"  Votos:       {movie.get('vote_count', 0)}")
    print(f"  Popularidade:{movie.get('popularity', 0):.2f}")
    print(f"  Sinopse:     {overview}")
    print()
