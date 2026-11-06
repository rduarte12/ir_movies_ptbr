# Sprint 02 — Coleta: filtros, checkpoint e snapshot

- **Data:** 2026-11-05 · **Branch:** `sprint02/collect-pipeline` · **Tag:** `sprint-02`
- **Sessão do Claude Code:** background job, Opus 4.6

## O que foi feito
- `collect/filters.py`: `evaluate(raw, cfg)` aplica filtros de qualidade (adult, sinopse ≥ 5 palavras, vote_count ≥ 2); retorna `(aceito, motivo_rejeição)`
- `collect/snapshot.py`: `_extract_row()` extrai colunas do JSON bruto para o esquema de `architecture.md`; `write_snapshot()` escreve parquet + `snapshot_meta.json`; `validate_snapshot()` confere invariantes D-025
- `collect/pipeline.py`: `run()` percorre candidatos sequencialmente, aplica filtros, checkpoint incremental em JSONL (D-024), retomável; para ao atingir `target_size`
- `collect/__init__.py`: exports públicos
- 32 testes novos (filters: 12, snapshot: 12, pipeline: 8), todos sem rede
- Notebook 01 atualizado com células de coleta completa, verificações de dados e visualização do snapshot
- `config.yaml`: adicionado `checkpoint_interval: 500`
- Decisões D-024, D-025, D-026 registradas; adendo D-004 (adult) aceito

## Decisões (IDs em `decisions.md`)
- D-024 — Formato do checkpoint incremental (`proposta`)
- D-025 — Validações do snapshot (`proposta`)
- D-026 — Pipeline de coleta sequencial (`proposta`)
- D-004 adendo — `adult=false` aceito

## Premissas assumidas
- O campo `keywords` no JSON da TMDB está sob `raw["keywords"]["keywords"]` (lista de objetos com `name`). Verificado com a fixture `movie_278.json`.
- O campo `director` está em `credits.crew` com `job == "Director"`. Verificado com a fixture.

## Desvios do plano
- Nenhum.

## Como verificar
- `python -m pytest` — 53 testes passam sem rede
- `python -m ruff check src/ tests/ notebooks/` — sem erros
- `python -m jupytext --sync notebooks/*.py` — sincronização sem erros
- Com `.env` preenchido: rodar notebook 01 → coleta completa → parquet + meta gerados
- Retomada: interromper o notebook durante a coleta; reiniciar → continua de onde parou (checkpoint em `data/checkpoints/`)

## Resultado das verificações
- pytest: 53 passed (1.31s)
- ruff: All checks passed
- jupytext: sincronizado sem alterações
- Coleta real: **pendente** (requer `.env` do Rafael e ~30–60 min de execução)

## Pendências e riscos
- D-024, D-025 e D-026 ainda como `proposta` — aguardam confirmação do Rafael
- Coleta real ainda não executada — parquet e meta serão gerados na primeira execução do notebook
- Se houver < 20.000 filmes com sinopse PT-BR e ≥ 2 votos, o parquet terá menos linhas (`target_size` é teto, não meta)
- Tamanho do parquet a conferir após a coleta (limite: 50 MB para git sem LFS)

## Teach-back (explicação do Rafael, com as próprias palavras)
- *(pendente)*
