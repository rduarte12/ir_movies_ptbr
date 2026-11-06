# Sprint 05 — Serviço de consulta, reescritor e log

- **Data:** 2026-11-06 · **Branch:** `sprint-05/servico-log` · **Tag:** `sprint-05`

## O que foi feito
- `IdentityRewriter` em `src/ir_movies/query/rewriter.py`: devolve a consulta sem alterar; é o ponto de extensão de D-009.
- `src/ir_movies/query/snapshot_loader.py`: acha o parquet pelo `snapshot_id` de `data/snapshot_meta.json`, aplica as normalizações de D-090 e devolve `LoadedSnapshot` (filmes e textos indexados, mesma ordem). `document_text` replica a convenção de D-013.
- `SearchService` em `src/ir_movies/query/service.py`: implementa `SearchServiceProtocol` inteiro; monta pré-processador e `TfidfIndex` a partir do `config.yaml`; `from_config()` é o caminho de produção.
- `QueryLogger` em `src/ir_movies/logging_jsonl.py`: um arquivo por dia (UTC), append, UTF-8, uma linha JSON por evento, com os campos de `architecture.md` secao 5; `new_session_id()` para a interface.
- Testes novos: `tests/test_query_rewriter.py`, `tests/test_query_snapshot_loader.py`, `tests/test_query_service.py`, `tests/test_logging_jsonl.py`. As classes de regra de `tests/test_contract.py` são reaproveitadas contra o serviço real.
- Comentários nas seções `search` e `logging` de `config.yaml` (valores inalterados).

## Decisões (IDs em `docs/decisions.md`)
- D-030 — Resolução de Q-001: log no disco do Colab, baixado à mão (`proposta`)
- D-031 — Formato do `session_id` (`proposta`)
- D-032 — Onde a latência é medida (`proposta`)
- D-033 — Log desligado e falhas de escrita (`proposta`)
- D-034 — Resolução do snapshot, caminhos e normalizações (`proposta`)
- D-035 — Detalhes do esquema do log (`proposta`)
- D-036 — Montagem do `SearchService` por injeção (`proposta`)
- D-037 — Entradas fora do esperado em `search` (`proposta`)

## Premissas assumidas
- O evento `click` carrega só o contexto fixo mais `movie_id` e `rank`; os campos de consulta existem apenas no evento `search` (D-035).
- `n_query_tokens` conta radicais distintos, para `n_oov_tokens <= n_query_tokens` (D-035).
- Quem gera o `session_id` é a interface, uma vez por visita ao navegador (D-031).
- `logging.dir` relativo é resolvido a partir da raiz do projeto, não do diretório de trabalho (D-034).
- O acervo aceito no snapshot atual (8.002 filmes) é lido de `snapshot_meta.json` nos testes; uma recoleta muda o número sem quebrar os testes.

## Desvios do plano
- Nenhum. O carregador ficou em módulo próprio (`snapshot_loader.py`), como previsto na divisão de arquivos da sprint.

## Como verificar
```
python -m pytest -q
python -m ruff check .
python -m pytest tests/test_query_rewriter.py tests/test_query_service.py tests/test_logging_jsonl.py -q
```
Resultado esperado: nenhuma falha; linter sem erros.

## Resultado das verificações
- `pytest`: 251 passed (121 anteriores + 130 novos).
- `ruff check .`: All checks passed.
- Arquivos desta sprint passam em `ruff format --check`.
- Mutações feitas à mão (e revertidas) em 10 pontos do código (truncagem, `top_k`, mapeamento `doc_id` -> `movie_id`, condição de `session_id`, corte de `top_ids`, flag de log desligado, modo de abertura do arquivo, contagem de radicais, normalização de `runtime`, ordem de `document_text`): cada uma derrubou ao menos um teste.
- Latência medida pelo serviço no snapshot real nas consultas de inspeção: de 0,6 a 2,8 ms por busca.

## Pendências e riscos
- Não verificado: o log no Colab (disco efêmero, download manual de D-030). Só roda de fato na Sprint 6/8.
- Não verificado: comportamento sob vários usuários simultâneos no Gradio; há um `Lock` na escrita, testado com 40 threads em disco local.
- Se o ambiente do Colab cair antes do download, o log do dia se perde (consequência aceita em D-030).
- `docs/decisions.md` ainda lista Q-001 como aberta; atualizar quando D-030 for confirmada.

## Teach-back (explicação do Rafael, com as próprias palavras)
-
