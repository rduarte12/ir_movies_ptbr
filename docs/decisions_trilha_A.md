# Decisões da Sprint 5 (serviço de busca, reescritor e log)

Faixa reservada: D-030 a D-049 (ver cabeçalho de `docs/decisions.md`). Todas as entradas
abaixo estão como `proposta`, aguardando confirmação do autor. Formato e regras iguais às de
`docs/decisions.md`: `**Origem:**` é R (autor do projeto) ou C (proposta técnica).

---

### D-030 · 2026-11-06 · Resolução de Q-001: o log fica no disco do Colab e o autor o baixa à mão
- **Contexto:** o disco do Colab é efêmero; Q-001 perguntava se o log seria baixado ao final ou
  espelhado no Drive.
- **Decisão:** o `QueryLogger` escreve só em `logging.dir` (padrão `logs/`), no disco local da
  máquina onde o app roda. No Colab, o autor baixa `logs/queries-*.jsonl` manualmente ao fim da
  demo, antes de encerrar o ambiente. Nenhum espelhamento no Drive e nenhum código de upload.
- **Motivo:** foi a resposta registrada para Q-001; evita pedir permissão de Drive ao público da
  feira e mantém o log sem dado pessoal sob controle de uma pessoa só.
- **Consequência:** se o ambiente do Colab cair antes do download, o log do dia se perde.
  Aceito para uma demo de ~2h. O notebook (Sprint 6) deve lembrar o autor do download.
- **Origem:** R (resposta a Q-001) / C (redação) · **Status:** proposta

### D-031 · 2026-11-06 · Formato do `session_id`
- **Decisão:** 16 caracteres hexadecimais aleatórios, gerados por `secrets.token_hex(8)`, pela
  função `new_session_id()` de `ir_movies.logging_jsonl`. Quem cria o identificador é a
  interface, uma vez por visita ao navegador; o serviço e o logger apenas o recebem e o gravam.
- **Motivo:** 64 bits aleatórios bastam para distinguir visitas numa demo, não carregam hora,
  máquina nem pessoa (ao contrário de UUID v1) e são curtos para ler no arquivo.
- **Alternativa descartada:** UUID v4 completo (36 caracteres, sem ganho prático aqui).
- **Origem:** C · **Status:** proposta

### D-032 · 2026-11-06 · Onde a latência é medida
- **Decisão:** `latency_ms` cobre do início de `search` até a montagem do `SearchResult`
  (reescrita, pré-processamento com rastreio, busca no índice, termos fora do vocabulário e
  criação dos `MovieHit`), medido com `time.perf_counter()`. Fora da medida: a construção do
  índice, a carga do snapshot e a escrita da linha de log (o relógio é lido antes do log).
- **Motivo:** o número serve para comparar buscas entre si e mostrar ao público quanto custa
  buscar; incluir E/S de disco misturaria outra grandeza.
- **Origem:** C · **Status:** proposta

### D-033 · 2026-11-06 · Comportamento do log desligado e de falhas de escrita
- **Decisão:** com `logging.enabled: false`, o `QueryLogger` não cria o diretório nem o arquivo
  e `log_search` e `log_click` não fazem nada. Com o log ligado, o diretório é criado na primeira
  escrita (não na construção). Se a escrita falhar (`OSError`), o erro vai para o `logging` da
  biblioteca padrão como aviso e a busca segue normalmente.
- **Motivo:** o log é observação, não função do buscador: disco cheio ou pasta sem permissão não
  pode derrubar a demonstração. Criar o diretório só ao escrever garante que "desligado" não
  deixa rastro no disco.
- **Origem:** C · **Status:** proposta

### D-034 · 2026-11-06 · Convenção de resolução do snapshot e de caminhos
- **Decisão:** o carregador lê `snapshot_id` de `<data_dir>/snapshot_meta.json` e abre
  `<data_dir>/movies_ptbr_<snapshot_id>.parquet`. O nome do arquivo não aparece em código nem em
  testes de produção. `data_dir` e `logging.dir` relativos são resolvidos a partir da raiz do
  projeto, não do diretório de trabalho, para o app funcionar igual no Colab e no Jupyter local.
  Se o meta ou o parquet faltar, levanta `FileNotFoundError` com o caminho procurado.
- **Normalizações** (as de D-090): `runtime` 0 ou nulo vira `None`; `poster_path` nulo ou vazio
  vira `None`; `tagline`, `director` e `release_date` nulos viram `""`. Os arrays do parquet
  viram `list` de `str` (o contrato declara `list[str]`).
- **Texto indexado:** `document_text(movie)` = título, tagline, sinopse e gêneros unidos por um
  espaço (D-013), idêntico ao de `tests/fakes.py`. Como o resultado é só concatenação, um
  teste confere as duas implementações para não divergirem.
- **Origem:** C · **Status:** proposta

### D-035 · 2026-11-06 · Detalhes do esquema do log (`architecture.md` secao 5)
- **Decisão:**
  - Linha `search`: `event`, `ts`, `session_id`, `app_version`, `snapshot_id`, `model`,
    `rewriter`, `raw_query`, `effective_query`, `n_query_tokens`, `n_oov_tokens`, `n_results`,
    `top_ids`, `latency_ms`. Linha `click`: `event`, `ts`, `session_id`, `app_version`,
    `snapshot_id`, `model`, `rewriter`, `movie_id`, `rank`. O esquema só situa `movie_id` e
    `rank` no clique; os demais campos de consulta não existem nesse evento.
  - `ts`: UTC, ISO 8601 com milissegundos e sufixo `+00:00`. O arquivo do dia usa a data UTC do
    mesmo instante, para o nome do arquivo e o `ts` nunca discordarem.
  - `n_query_tokens`: número de radicais **distintos** da consulta depois do pré-processamento;
    `n_oov_tokens`: quantos desses não existem no acervo. Assim `n_oov_tokens <= n_query_tokens`
    e a razão entre os dois é interpretável.
  - `n_results`: `len(hits)` devolvido (já limitado por `k`). `top_ids`: até 10 `movie_id`.
  - Arquivo aberto em modo append, UTF-8, `ensure_ascii=False`, fim de linha `\n` em qualquer
    sistema, uma escrita por evento sob um `threading.Lock` (o Gradio atende em threads).
  - O `QueryLogger` não tem parâmetro nem campo para IP, user-agent, host ou e-mail.
- **Origem:** C · **Status:** proposta

### D-036 · 2026-11-06 · Montagem do `SearchService` por injeção
- **Decisão:** `SearchService(snapshot, cfg, *, rewriter=None, logger=None, app_version=None)`
  recebe o acervo já carregado e o dicionário de configuração; `rewriter` padrão é
  `IdentityRewriter`, `logger` padrão é `QueryLogger.from_config`, `app_version` padrão é
  `ir_movies.__version__` (D-090). `SearchService.from_config()` faz o caminho de produção
  (lê `config.yaml`, carrega o snapshot e monta tudo). O pré-processador e o `TfidfIndex` são
  sempre construídos a partir de `text` e `tfidf` do `config.yaml`.
- **Motivo:** o mesmo construtor serve ao app (acervo real) e aos testes (acervo de brinquedo,
  log em `tmp_path`), sem ramos de teste no código de produção.
- **Origem:** C · **Status:** proposta

### D-037 · 2026-11-06 · Entradas fora do esperado em `search`
- **Decisão:** `raw_query` nulo é tratado como `""`. `k` negativo é tratado como 0 (lista
  vazia); `k=None` usa `search.top_k`. O truncamento em `MAX_QUERY_CHARS` (300) é feito antes do
  reescritor, de modo que `raw_query` no resultado e no log já vem truncado.
- **Motivo:** a regra 1 do contrato proíbe exceção por causa da consulta; `k` vem da interface,
  mas um valor inválido não deve produzir fatiamento negativo silencioso no índice.
- **Origem:** C · **Status:** proposta
