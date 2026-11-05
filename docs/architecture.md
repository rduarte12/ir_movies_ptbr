# Arquitetura e contratos

> Contratos entre módulos, esquemas de dados e configuração. Mudanças aqui exigem decisão registrada em `decisions.md`.
> As assinaturas abaixo são **especificação**, não implementação.

## 1. Fluxo geral

```
[TMDB export de IDs] -> ordenar por popularity -> [TMDB /movie/{id}] -> filtros -> snapshot.parquet (+ meta)
                                  (notebook 01, local)

snapshot.parquet -> pré-processar -> TfidfIndex (em memória)
consulta bruta -> Rewriter -> pré-processar -> TfidfIndex.search -> hits -> Explicabilidade
                                  (notebook 02, Colab/local)           \-> QueryLogger (JSONL)
```

## 2. Estrutura do repositório

```
ir_movies_ptbr/
├── CLAUDE.md
├── README.md                  # Sprint 8
├── config.yaml
├── .env.example
├── requirements-app.txt       # notebook 02 (Colab)
├── requirements-collect.txt   # notebook 01
├── requirements-dev.txt       # pytest, ruff, jupytext, nbstripout
├── notebooks/
│   ├── 01_collect_tmdb.py / .ipynb
│   └── 02_search_app.py / .ipynb
├── src/ir_movies/
│   ├── config.py
│   ├── tmdb/            # ids.py, client.py
│   ├── collect/         # pipeline.py, filters.py, snapshot.py
│   ├── text/            # preprocess.py
│   ├── index/           # tfidf.py
│   ├── query/           # rewriter.py, service.py
│   ├── explain.py
│   ├── logging_jsonl.py
│   └── ui/              # app.py
├── tests/ (+ fixtures/)
├── data/ (snapshot versionado; raw/ e checkpoints/ ignorados)
├── logs/ (ignorado)
└── docs/
```

## 3. Contratos dos módulos

| Módulo | Função / classe | Entrada | Saída |
|---|---|---|---|
| `config` | `load_config(path)` | caminho do YAML | dicionário validado |
| `tmdb.ids` | `download_id_export(date)` / `load_candidates(path)` | data / arquivo | lista de `(id, popularity)` ordenada, sem `adult` |
| `tmdb.client` | `get_movie(id)` | id | JSON bruto (`language=pt-BR`, `append_to_response=credits,keywords`); retry com backoff; respeita limite configurado |
| `collect.filters` | `evaluate(raw)` | JSON bruto | `(aceito: bool, motivo_rejeicao: str \| None)` |
| `collect.pipeline` | `run(cfg)` | config | snapshot + meta; retomável por checkpoint |
| `text.preprocess` | `Preprocessor.tokens(text)` | texto | lista de radicais finais |
| `text.preprocess` | `Preprocessor.trace(text)` | texto | `PreprocessTrace`: tokens originais, ignorados (stopwords), radicais, mapa radical→formas de superfície |
| `index.tfidf` | `TfidfIndex.build(docs, preprocessor, cfg)` | textos dos documentos | índice (matriz esparsa L2-normalizada) |
| `index.tfidf` | `TfidfIndex.search(query, k)` | consulta já reescrita | `list[Hit(doc_id, score)]` desc, estável em empates (desempate por `doc_id`) |
| `index.tfidf` | `TfidfIndex.contributions(query, doc_id)` | consulta, documento | `list[TermContribution(stem, surface_forms, idf, q_weight, d_weight, contribution)]` |
| `query.rewriter` | `Rewriter.rewrite(raw)` (protocolo) | consulta bruta | consulta efetiva. `IdentityRewriter` na v1 |
| `query.service` | `SearchService.search(raw, k, session_id)` | consulta bruta | `SearchResult`: raw, effective, trace, hits, termos fora do acervo, latência |
| `explain` | `highlight(text, matched_stems, weights)` | sinopse + termos | segmentos `(texto, intensidade \| None)` |
| `logging_jsonl` | `QueryLogger.log_search(...)`, `.log_click(...)` | resultado / clique | linha JSONL (append) |
| `ui.app` | `build_app(service, snapshot)` | serviço + dados | objeto Gradio |

### Invariantes (devem ter teste)

1. `sum(contribution) == cosseno(consulta, documento)` (tolerância 1e-9), conferido contra `sklearn.metrics.pairwise.cosine_similarity`.
2. Termos da consulta fora do vocabulário **não** entram no vetor nem na norma; são listados à parte para a UI.
3. Mesma consulta + mesmo snapshot + mesma config = mesmo ranking (determinismo).
4. Consulta sem nenhum termo no vocabulário retorna lista vazia (a UI trata o caso).
5. O mesmo `Preprocessor` é usado para documentos e consultas.

## 4. Esquema do snapshot (`data/movies_ptbr_YYYYMMDD.parquet`)

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | int | id TMDB |
| `title` | str | título PT-BR |
| `original_title` | str | |
| `tagline` | str | pode ser vazio |
| `overview` | str | PT-BR, ≥ 5 palavras |
| `genres` | list[str] | nomes em PT-BR |
| `keywords` | list[str] | guardadas, não indexadas na v1 |
| `cast_top5` | list[str] | |
| `director` | str | pode ser vazio |
| `release_date` | str (ISO) | pode ser vazio |
| `runtime` | int | minutos, pode ser nulo |
| `vote_average` | float | |
| `vote_count` | int | ≥ 2 |
| `popularity` | float | no momento da coleta |
| `poster_path` | str | pode ser nulo (a UI usa placeholder) |

`data/snapshot_meta.json`: `snapshot_id` (ex.: `20261105`), data/hora UTC, endpoints e parâmetros, filtros aplicados, nº de candidatos testados, nº aceitos, rejeições por motivo, versão do código (hash do git), versões das bibliotecas.

URL de pôster: `https://image.tmdb.org/t/p/{tamanho}{poster_path}` (tamanho em `config.yaml`; confirmar tamanhos suportados na documentação).

## 5. Esquema do log (`logs/queries-YYYY-MM-DD.jsonl`)

Uma linha JSON por evento, UTF-8, append-only.

| Campo | Tipo | Observação |
|---|---|---|
| `event` | `"search"` \| `"click"` | |
| `ts` | str | UTC, ISO 8601 |
| `session_id` | str | aleatório por sessão do navegador; sem relação com pessoa |
| `app_version`, `snapshot_id` | str | rastreabilidade |
| `model` | str | `"tfidf"` |
| `rewriter` | str | `"identity"` |
| `raw_query`, `effective_query` | str | iguais na v1 |
| `n_query_tokens`, `n_oov_tokens` | int | |
| `n_results` | int | |
| `top_ids` | list[int] | top 10 |
| `latency_ms` | float | |
| `movie_id`, `rank` | int | só em `click` |

Nunca registrar IP, user-agent ou qualquer dado pessoal. Aviso discreto na UI.

## 6. `config.yaml` (chaves)

```
snapshot:   {target_size: 20000, min_overview_words: 5, min_vote_count: 2, exclude_adult: true}
tmdb:       {language: pt-BR, max_concurrency: <int>, retry: {...}, poster_size: <str>}
text:       {stemmer: snowball_pt, extra_stopwords: [...], strip_accents: true}
tfidf:      {ngram_range: [1,1], norm: l2, smooth_idf: true, sublinear_tf: false, min_df: 2}
search:     {top_k: 20}
logging:    {dir: logs, enabled: true}
ui:         {app_name: <str>}
```

Valores marcados como proposta em `decisions.md` (D-014, D-015) podem mudar; a fonte de verdade é o `config.yaml` commitado.

## 7. Ambientes

- **Local (notebook 01 e desenvolvimento):** `.env` com `TMDB_READ_ACCESS_TOKEN`.
- **Colab (notebook 02):** clona o repositório, instala `requirements-app.txt`, lê o snapshot. Não usa a API da TMDB (só o CDN de pôsteres).
- Python igual nos dois (Q-002).
