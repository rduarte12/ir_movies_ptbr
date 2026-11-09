# Sprint 09 — Busca semântica opcional (pré-filtro + RRF)

- **Data:** 2026-11-08 · **Branch:** `sprint-09/busca-semantica` · **Tag:** `sprint-09`

## O que foi feito

- `src/ir_movies/index/semantic.py`: `SemanticRetriever` (top-k por cosseno em vetores L2-normalizados), `EmbeddingsMeta`, `load_semantic_retriever` com validação de snapshot_id, modelo e dimensão.
- `src/ir_movies/index/tfidf.py`: método `score_subset` — pontua um subconjunto de doc_ids usando o IDF do corpus inteiro, sem re-fitting.
- `src/ir_movies/query/types.py`: protocolo `Encoder`, campos opcionais `semantic_score` e `rrf_score` em `MovieHit`, propriedade `semantic_active` em `SearchServiceProtocol`.
- `src/ir_movies/query/service.py`: `_search_hybrid` (semântico → TF-IDF subset → RRF k=60), `_try_load_retriever` (falha suave), `_SentenceTransformerEncoder` (adaptador).
- `src/ir_movies/ui/texts.py`: `SEMANTIC_NOTICE`.
- `src/ir_movies/ui/view.py`: `semantic_notice_html`.
- `src/ir_movies/ui/app.py`: aviso semântico logo após o cabeçalho.
- `scripts/build_embeddings.py`: geração de vetores em lotes, L2-normalização, metadados JSON.
- `scripts/measure_latency.py`: medição de latência (50 consultas, mediana e p95).
- `data/embeddings_sentence_transformers_paraphrase_multilingual_minilm_l12_v2_20261106.{npy,json}`: vetores de 8 002 filmes (384 dims, float32), revisão fixada.
- `config.yaml`: seção `semantic` com `revision` preenchida após extração.
- `tests/fakes.py`: `FakeEncoder`, `FAKE_ENCODER_DIM`, `semantic_active` em `FakeSearchService`.
- `tests/test_semantic.py`: 26 novos testes.

## Decisões (IDs em `decisions.md`)

- D-092 — Pré-filtro semântico opcional (`proposta`)
- D-093 — Modelo paraphrase-multilingual-MiniLM-L12-v2, revisão e8f8c21... (`proposta`)
- D-094 — Texto do documento = mesmo texto do TF-IDF (`proposta`)
- D-095 — RRF k=60, desempate por posto semântico (`proposta`)
- D-096 — `MovieHit.score` = cosseno TF-IDF; ordenação por RRF quando ativa (`proposta`)
- D-097 — Falha suave → TF-IDF puro + aviso no log (`proposta`)
- D-098 — Toggle só via config (`proposta`)
- D-099 — Offline via `HF_HUB_OFFLINE=1`, revisão fixada (`proposta`)
- D-100 — Uma linha de aviso na UI quando semântica ativa (`proposta`)

## Premissas assumidas

- Coluna de texto indexada é a mesma do TF-IDF (título + sinopse concatenados), conforme D-094.
- O `.npy` e o `.json` ficam em `data/` (versionados), não em `data/raw/` nem `data/checkpoints/`.
- A revisão do modelo foi lida do cache local do Hugging Face após extração offline.

## Desvios do plano

- `revision` ficou vazia no JSON gerado pelo `build_embeddings.py` (a leitura do cache HF não localizou o campo no momento da extração); preenchida manualmente a partir do diretório de snapshots do HF (`~/.cache/huggingface/hub/models--...`). O campo no JSON e no config foram corrigidos.
- 1 956 de 8 002 documentos (24,4 %) têm texto truncado pelo limite de 128 tokens do modelo; registrado em `n_docs_truncated` nos metadados, mas não bloqueia a demo — os vetores existem para todos os filmes.

## Como verificar

```
python -m pytest                      # deve passar 434 testes (408 anteriores + 26 novos)
python -m ruff check .                # zero erros
python scripts/measure_latency.py    # p95 ≤ 200 ms
```

Com `semantic.enabled: true` no `config.yaml`:
```
python -c "
import sys; sys.path.insert(0,'src')
from ir_movies.query.service import SearchService
svc = SearchService.from_config('config.yaml')
print(svc.semantic_active)   # deve ser True
print(svc.search('tubarao').hits[0])
"
```

## Resultado das verificações

- Testes: 434 passed em ~52 s (incluindo os 26 novos).
- Ruff: zero erros.
- Latência (50 consultas, `semantic.enabled: true`):
  - Codificação da consulta — mediana 13,2 ms · p95 17,4 ms
  - Busca completa — mediana 14,9 ms · p95 **21,1 ms** ← bem abaixo dos 200 ms
- Modo offline (`HF_HUB_OFFLINE=1`): `semantic_active = True`, busca retornou 20 hits.
- Falha suave: com `embeddings_dir` apontando para pasta inexistente, `semantic_active = False` e WARNING no log.

## Pendências e riscos

- Ensaio no Colab com `semantic.enabled = true`: verificar tempo de carregamento do modelo (~2 GB de pesos não existem no Colab sem instalação) e confirmar que `requirements-app.txt` cobre todas as dependências.
- Teste de `HF_HUB_OFFLINE=1` no Colab com os pesos já salvos no drive.
- Inspeção manual de ~10 consultas comparando modos on/off.
- Aceitar D-092 a D-100 (atualmente `proposta`) após ensaio manual.
- 1 956 documentos truncados: avaliar se afeta a qualidade de busca nas demos.

## Teach-back (explicação do Rafael, com as próprias palavras)

_(a preencher pelo Rafael após ensaio)_

Pontos a cobrir:
- O que são embeddings e por que "entendem significado".
- Por que o RRF soma dois rankings em vez de médias de scores.
- Por que `hit.score` continua sendo o cosseno TF-IDF (Explicabilidade intacta).
