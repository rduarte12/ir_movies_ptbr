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
# **Seções:**
# 1. Setup + download de IDs + coleta via API (requer `.env`)
# 2. Geração do snapshot a partir do checkpoint (não requer `.env`)
# 3. Verificações e visualização

# %% [markdown]
# ---
# ## Parte 1 — Coleta (requer `.env` com token TMDB)
#
# Pode pular esta parte se já tem um checkpoint em `data/checkpoints/`.

# %% [markdown]
# ### Setup

# %%
import json
import logging
import os
from datetime import date

import pandas as pd
from dotenv import load_dotenv

from ir_movies.collect.pipeline import load_checkpoint
from ir_movies.collect.pipeline import run as run_pipeline
from ir_movies.collect.snapshot import validate_snapshot, write_snapshot
from ir_movies.config import PROJECT_ROOT, load_config
from ir_movies.tmdb.ids import download_id_export, load_candidates

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

cfg = load_config()
print(f"Config carregado. target_size: {cfg['snapshot']['target_size']}")

# %% [markdown]
# ### Download do export diário de IDs
#
# O export é um arquivo gzipped JSONL com todos os IDs de filmes da TMDB,
# publicado diariamente (~8h UTC). Não requer autenticação (D-022).

# %%
load_dotenv(PROJECT_ROOT / ".env")
token = os.environ["TMDB_READ_ACCESS_TOKEN"]

export_path = download_id_export(date.today(), PROJECT_ROOT / "data" / "raw")
print(f"Export salvo em: {export_path}")

# %% [markdown]
# ### Carregar candidatos
#
# Lemos o export, excluímos filmes adultos (D-004) e ordenamos por
# popularidade decrescente (D-003, D-027).

# %%
candidates = load_candidates(export_path)
print(f"Total de candidatos (sem adult): {len(candidates):,}")
print("\nTop 10 por popularidade:")
for movie_id, pop in candidates[:10]:
    print(f"  id={movie_id:>8}  popularity={pop:.2f}")

# %% [markdown]
# ### Coleta via API
#
# Busca detalhes dos top `target_size` candidatos, aplica filtros (D-004)
# e salva checkpoint incremental (D-024, D-027).
#
# Se interromper e reiniciar, a coleta retoma de onde parou.

# %%
result = run_pipeline(
    cfg=cfg,
    token=token,
    candidates=candidates,
)

print(f"\n{'=' * 60}")
print(f"  Aceitos:    {result.accepted}")
print(f"  Rejeitados: {result.rejected}")
print(f"  Erros:      {result.errors}")
print(f"  Rejeições:  {dict(result.rejection_counts)}")

# %% [markdown]
# ---
# ## Parte 2 — Snapshot a partir do checkpoint
#
# Gera o parquet e `snapshot_meta.json` lendo os dados já coletados
# em `data/checkpoints/`. **Não precisa de `.env` nem da API.**

# %%
checkpoint_dir = PROJECT_ROOT / "data" / "checkpoints"
data_dir = PROJECT_ROOT / "data"

processed_ids, accepted_movies, rejection_counts = load_checkpoint(checkpoint_dir)

n_processed = len(processed_ids)
n_accepted = len(accepted_movies)
n_rejected = sum(rejection_counts.values())
n_errors = n_processed - n_accepted - n_rejected

print(f"Checkpoint: {n_processed} processados, {n_accepted} aceitos")
print(f"           {n_rejected} rejeitados, {n_errors} erros")
print(f"Rejeições: {dict(rejection_counts)}")

# %%
if accepted_movies:
    parquet_path, meta_path = write_snapshot(
        accepted_movies,
        cfg,
        rejection_counts,
        n_candidates=n_processed,
        dest_dir=data_dir,
    )
    size_mb = parquet_path.stat().st_size / (1024 * 1024)
    print(f"Parquet: {parquet_path} ({size_mb:.1f} MB)")
    print(f"Meta:    {meta_path}")
else:
    print("Nenhum filme aceito no checkpoint.")

# %% [markdown]
# ---
# ## Parte 3 — Verificações de dados (D-025)
#
# Conferimos o snapshot gerado: nulos, duplicatas, tamanho das sinopses.

# %%
parquet_files = sorted(data_dir.glob("movies_ptbr_*.parquet"))
if parquet_files:
    parquet_path = parquet_files[-1]
    print(f"Lendo: {parquet_path}")
    df = pd.read_parquet(parquet_path)
    print(f"Linhas: {len(df)}")
    print("\nNulos por coluna:")
    print(df.isnull().sum().to_string())

    overview_words = df["overview"].apply(lambda x: len(str(x).split()))
    print("\nTamanho das sinopses (palavras):")
    print(f"  Mín: {overview_words.min()}")
    print(f"  Mediana: {overview_words.median():.0f}")
    print(f"  Máx: {overview_words.max()}")

    validation_errors = validate_snapshot(df, cfg)
    if validation_errors:
        print("\nERROS DE VALIDAÇÃO:")
        for e in validation_errors:
            print(f"  - {e}")
    else:
        print("\nValidações OK.")
else:
    print("Nenhum parquet encontrado em data/.")

# %% [markdown]
# ### Metadados do snapshot

# %%
meta_path = data_dir / "snapshot_meta.json"
if meta_path.exists():
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    for k, v in meta.items():
        print(f"  {k}: {v}")
else:
    print("Nenhum meta encontrado.")

# %% [markdown]
# ### Amostra de 3 filmes

# %%
if parquet_files:
    df = pd.read_parquet(parquet_files[-1])
    for _, row in df.head(3).iterrows():
        overview = row["overview"]
        if len(overview) > 200:
            overview = overview[:200] + "..."
        print(f"{'=' * 60}")
        print(f"  ID:          {row['id']}")
        print(f"  Título:      {row['title']}")
        print(f"  Original:    {row['original_title']}")
        print(f"  Gêneros:     {row['genres']}")
        print(f"  Votos:       {row['vote_count']}")
        print(f"  Popularidade:{row['popularity']:.2f}")
        print(f"  Sinopse:     {overview}")
        print()
