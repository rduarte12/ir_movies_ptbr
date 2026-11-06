# Registro de decisões

Formato: `D-NNN · data · título`. Status: `aceita` | `proposta` (aguarda confirmação do Rafael) | `revogada` (por D-NNN).
Regra: decisão `aceita` não se edita; para mudar, nova entrada com `Revoga: D-NNN`.
Faixas de IDs das Sprints 5 a 8 (D-090): 030–049 serviço e log, 050–069 interface e
explicabilidade, 070–089 entrega e verificação, 090 em diante contrato e integração.
Lacunas na numeração são esperadas: cada faixa foi reservada antes de se saber quantas
decisões cada frente exigiria.
Campo de origem: `**Decidido por:**` nas entradas antigas, `**Origem:**` nas novas.
R = autor do projeto; C = proposta técnica (sempre `proposta` até confirmação do autor).

---

### D-001 · 2026-11-05 · Objetivo e contexto
- **Decisão:** buscador didático de filmes PT-BR para a feira de extensão do ICMC-USP, demo de ~2h no notebook do autor.
- **Decidido por:** R · **Status:** aceita

### D-002 · 2026-11-05 · Acervo: qualquer filme com sinopse em PT-BR
- **Contexto:** "em português" pode significar língua original ou sinopse traduzida.
- **Decisão:** usar `language=pt-BR` e incluir filmes de qualquer origem (inclui Hollywood), desde que haja sinopse em PT-BR.
- **Alternativas:** só `original_language=pt` (descartada: acervo pequeno e de nicho).
- **Decidido por:** R · **Status:** aceita

### D-003 · 2026-11-05 · Seleção por popularidade a partir do export diário de IDs
- **Decisão:** obter IDs pelo export diário da TMDB, ordenar por `popularity` e percorrer em ordem, buscando detalhes, **até aceitar 20.000 filmes** (ou esgotar candidatos). Registrar no `snapshot_meta.json` quantos candidatos foram testados e quantos rejeitados por motivo.
- **Motivo:** os filtros (D-004) dependem de campos só disponíveis nos detalhes; é preciso sobre-buscar.
- **A verificar:** formato e disponibilidade atual do export na documentação da TMDB (Sprint 1).
- **Decidido por:** R (20 mil, popularidade) / C (mecânica de sobre-busca) · **Status:** aceita

### D-004 · 2026-11-05 · Filtros de qualidade
- **Decisão:** manter filme se `overview` (PT-BR) tem ≥ 5 palavras **e** `vote_count ≥ 2`.
- **Decidido por:** R · **Status:** aceita
- **Adendo (proposta, C):** excluir também `adult=true`, por causa do público (inclui ensino médio). **Status do adendo:** aceita

### D-005 · 2026-11-05 · Modelo da v1: apenas TF-IDF + cosseno
- **Decisão:** sem BM25, sem embeddings. Motivo: público leigo + determinismo + explicabilidade exata. BM25 pode entrar em versão futura.
- **Decidido por:** R · **Status:** aceita

### D-006 · 2026-11-05 · Estrutura: dois notebooks finos + pacote `src/`
- **Decisão:** `01_collect_tmdb` (local) e `02_search_app` (Colab). Lógica em `src/ir_movies/`. Notebooks em par jupytext (`.py` percent ↔ `.ipynb`); `.ipynb` commitado (Colab abre pelo GitHub), com saídas removidas (nbstripout).
- **Motivo:** editar o `.py` é mais seguro que editar o `.ipynb`, e os diffs ficam legíveis.
- **Decidido por:** R (dois notebooks) / C (jupytext, nbstripout) · **Status:** aceita (dois notebooks) · **proposta** (jupytext/nbstripout)

### D-007 · 2026-11-05 · Colab + Gradio, plano B local
- **Decisão:** buscador roda no Colab com Gradio (limitações de layout aceitas). O mesmo notebook deve rodar em Jupyter local.
- **Decidido por:** R · **Status:** aceita

### D-008 · 2026-11-05 · Log de consultas em JSONL, anônimo
- **Decisão:** um arquivo por dia em `logs/` (não versionado). Campos em `architecture.md`. Sem IP nem identificador pessoal; `session_id` aleatório. Aviso discreto na UI.
- **Decidido por:** R · **Status:** aceita
- **Questão aberta Q-001:** persistência do log no Colab (disco efêmero).

### D-009 · 2026-11-05 · Ponto de extensão para reescrita de consulta (LLM)
- **Decisão:** pipeline `consulta bruta → Rewriter → pré-processamento → modelo`. v1 usa `IdentityRewriter`. Log guarda `raw_query` e `effective_query`. LLM **não** é implementado agora.
- **Consequência futura:** com LLM o sistema deixa de ser determinístico; exigirá toggle, cache e exibição da consulta reescrita.
- **Decidido por:** R · **Status:** aceita

### D-010 · 2026-11-05 · Explicabilidade: 3 níveis sempre visíveis
- **Decisão:** seção "Explicabilidade" mostra os 3 níveis ao mesmo tempo.
- **Conteúdo dos níveis:** (1) palavras destacadas na sinopse; (2) barras de contribuição por palavra; (3) passo a passo (tokens → ignoradas → radicais → pesos → cosseno).
- **Decidido por:** R (existência e visibilidade) · **Status:** aceita · conteúdo exato dos níveis: **proposta (C)**

### D-011 · 2026-11-05 · Licença MIT
- **Decisão:** já presente no repositório.
- **Decidido por:** R · **Status:** aceita

### D-012 · 2026-11-05 · Idiomas
- **Decisão:** identificadores e arquivos em inglês; docstrings, comentários, docs e UI em PT-BR.
- **Decidido por:** C · **Status:** aceita

### D-013 · 2026-11-05 · Texto indexado
- **Decisão:** `title + tagline + overview + genres`, concatenados. Sem keywords e sem elenco na v1 (keywords da TMDB estão em inglês; elenco traz nomes próprios). Sem peso por campo na v1.
- **Possível experimento futuro:** inclusão de busca por autores e/ou key words -> dada uma query, a LLM decidi keywords.
- **Decidido por:** C · **Modificado por:** R **Status:** aceita

### D-014 · 2026-11-05 · Pré-processamento PT-BR
- **Decisão:** minúsculas → remoção de acentos (`unidecode`) → tokenização por regex de palavras → stopwords do NLTK PT (**também normalizadas sem acento**) + stopwords de consulta configuráveis (ex.: "qual", "filme") → stemmer **Snowball PT**.
- **Pendente:** comparar RSLP × Snowball na Sprint 3 em exemplos reais e registrar a escolha final. Radicais aparecerão na UI, então legibilidade conta.
- **Decidido por:** C · **Status:** aceita

### D-015 · 2026-11-05 · Hiperparâmetros iniciais do TF-IDF
- **Decisão:** `TfidfVectorizer` com `ngram_range=(1,1)`, `norm="l2"`, `smooth_idf=True`, `sublinear_tf=False`, `min_df=1` (ajustar após inspecionar vocabulário). Valores em `config.yaml`.
- **Nota:** com normalização L2 em consulta e documento, cosseno = produto escalar, e a contribuição por termo é `q_t · d_t`.
- **Decidido por:** C · **Status:** aceita

### D-016 · 2026-11-05 · Snapshot em parquet, versionado
- **Decisão:** `data/movies_ptbr_YYYYMMDD.parquet` + `data/snapshot_meta.json` no git (sem Git LFS).
- **Decidido por:** C · **Status:** aceita

### D-017 · 2026-11-05 · Segredos
- **Decisão:** token de leitura da TMDB em `.env` (`TMDB_READ_ACCESS_TOKEN`), enviado em header `Authorization: Bearer`. `.env.example` versionado. As ferramentas de desenvolvimento não leem `.env`
  (regra de permissão local).
- **Decidido por:** C · **Status:** aceita

### D-018 · 2026-11-05 · Processo de desenvolvimento por sprints
- **Decisão:** uma sprint por rodada de trabalho; planejar antes de implementar; branch e PR por sprint; commits pequenos; diário por sprint; tag `sprint-NN`; `git add/commit/push` exigem aprovação.
- **Decidido por:** C · **Status:** aceita

### D-019 · 2026-11-05 · Versão do Python: 3.13 (igual ao Colab)
- **Contexto:** Q-002 pede fixar a mesma versão do Colab. O Colab tem 3.13.18; localmente o winget instalou 3.13.17 (última disponível).
- **Decisão:** `requires-python = ">=3.13,<3.14"` no `pyproject.toml`. Aceita qualquer 3.13.x — diferenças de patch não afetam compatibilidade de bibliotecas.
- **Alternativa descartada:** fixar o micro exato (3.13.18) — impraticável, pois o winget não tem essa versão ainda.
- **Decidido por:** R (Colab como referência) / C (faixa `>=3.13,<3.14`) · **Status:** aceita

### D-020 · 2026-11-05 · Gerenciador de ambiente: venv (stdlib)
- **Decisão:** usar `py -3.13 -m venv .venv`. Sem ferramentas externas (conda, uv, virtualenv).
- **Motivo:** já vem com o Python, funciona igual no Windows e Linux, zero dependências extras. No Colab não é necessário (ambiente já isolado).
- **Decidido por:** C · **Status:** aceita

### D-021 · 2026-11-05 · Dependências com versão fixada e separação em 3 arquivos
- **Decisão:** todas as dependências com `==` (versão exata). Três arquivos:
  - `requirements-app.txt` — o que o Colab instala para o notebook 02 (busca + UI): scikit-learn, numpy, nltk, Unidecode, pandas, pyarrow, PyYAML, python-dotenv, gradio.
  - `requirements-collect.txt` — o que a máquina local instala para o notebook 01 (coleta): requests, tenacity, pandas, pyarrow, PyYAML, python-dotenv.
  - `requirements-dev.txt` — inclui os dois acima (`-r`) + pytest, ruff, jupytext, nbstripout.
- **Cliente HTTP:** `requests` (escolha do Rafael) + `tenacity` para retry com backoff.
- **Procedimento de pinagem:** instalar sem versão fixa, anotar as versões via `pip freeze`, escrever nos arquivos.
- **Decidido por:** R (requests, 3 arquivos) / C (separação e procedimento) · **Status:** aceita

### D-022 · 2026-11-05 · Formato e download do export diário de IDs da TMDB
- **Contexto:** D-003 pede obter IDs pelo export diário. Verificado na documentação oficial (https://developer.themoviedb.org/docs/daily-id-exports) e confirmado com download real em 2026-11-05.
- **Decisão:**
  - URL: `http://files.tmdb.org/p/exports/movie_ids_MM_DD_YYYY.json.gz`
  - Formato: gzipped JSONL. Campos por linha: `{"adult":bool, "id":int, "original_title":str, "popularity":float, "video":bool}`
  - Sem autenticação (a documentação avisa que pode mudar no futuro).
  - Disponível a partir de ~8:00 UTC diariamente; retenção de 3 meses.
  - Salvamento local: `data/raw/movie_ids_YYYY-MM-DD.json.gz` (não versionado).
- **Verificado:** URL funcional (status 200), esquema conferido com 5 linhas reais.
- **Decidido por:** C · **Status:** aceita

### D-023 · 2026-11-05 · Política de retry e rate-limit do cliente TMDB
- **Contexto:** a documentação da TMDB (https://developer.themoviedb.org/docs/rate-limiting) indica limite superior de ~40 req/s e pede respeitar HTTP 429.
- **Decisão:**
  - Retry via `tenacity`: backoff exponencial, `max_attempts` e `backoff_factor` em `config.yaml`.
  - Retry em: HTTP 429 (Too Many Requests), 5xx (erro de servidor), erros de conexão (`ConnectionError`, `Timeout`).
  - Não fazer retry em 404 (filme não existe) — propagar a exceção.
  - Rate limit: `time.sleep(1/rate_limit_rps)` entre chamadas. Valor padrão: `rate_limit_rps: 20` (conservador, ~metade do limite real).
  - Sem concorrência no Sprint 1 (cliente sequencial). `max_concurrency` será usado pelo pipeline na Sprint 2.
- **Verificado:** rate limit documentado como ~40 req/s sem limites formais publicados.
- **Decidido por:** C · **Status:** aceita

### D-024 · 2026-11-05 · Formato do checkpoint incremental
- **Contexto:** o pipeline (Sprint 2) precisa retomar a coleta sem re-buscar filmes já processados na API.
- **Decisão:**
  - `data/checkpoints/accepted_movies.jsonl` — JSON bruto completo de cada filme aceito (uma linha por filme).
  - `data/checkpoints/progress.jsonl` — `{"id": int, "status": "accepted"|"rejected"|"error", "reason": str|null}` por candidato processado.
  - Retomada: carrega os dois arquivos; pula candidatos cujo ID já aparece em `progress.jsonl`.
  - Flush a cada N candidatos processados (`snapshot.checkpoint_interval` em `config.yaml`, padrão 500).
- **Motivo:** `progress.jsonl` fornece estatísticas de rejeição para `snapshot_meta.json`; `accepted_movies.jsonl` evita re-fetch.
- **Decidido por:** C · **Status:** aceita

### D-025 · 2026-11-05 · Validações do snapshot
- **Decisão:** após escrever o parquet, verificar:
  - Contagem de linhas == nº de aceitos
  - Sem IDs duplicados
  - Nenhum `overview` nulo ou com < 5 palavras
  - Todo `vote_count >= 2`
  - Colunas obrigatórias nunca nulas: `id`, `title`, `overview`
  - Colunas que admitem nulo: `poster_path`, `tagline`, `runtime`, `director`, `release_date`
- **Registrar no meta:** contagem por motivo de rejeição, distribuição de tamanho de sinopse (mín/mediana/máx palavras), tamanho do arquivo em disco.
- **Decidido por:** C · **Status:** aceita

### D-026 · 2026-11-05 · Pipeline de coleta sequencial
- **Contexto:** D-023 mencionava `max_concurrency` para Sprint 2, mas a concorrência com threads adiciona complexidade (rate-limiter compartilhado, tratamento de erro em threads) sem ganho significativo para uma coleta que roda uma vez.
- **Decisão:** pipeline sequencial usando `TmdbClient` diretamente. `max_concurrency` em `config.yaml` fica como placeholder para versão futura.
- **Motivo:** código mais simples e explicável (teach-back); a taxa de 20 req/s sequencial já é suficiente (~30–60 min para o corpus).
- **Decidido por:** C · **Status:** aceita

### D-027 · 2026-11-06 · target_size = candidatos a buscar, não aceitos (Revoga: D-003)
- **Contexto:** D-003 dizia "até aceitar 20.000 filmes". A intenção original do Rafael sempre foi **buscar os detalhes dos 20.000 candidatos mais populares** e depois filtrar. O parquet terá ≤ 20.000 linhas (quantas passarem nos filtros).
- **Decisão:** `target_size` define quantos candidatos consultar na API (os top N por popularidade). Os filtros (D-004) rodam sobre esses N. O corpus final tem tantas linhas quantas passarem.
- **Decidido por:** R · **Status:** aceita

### D-028 · 2026-11-06 · Tokenização: hífens separam, números mantidos
- **Contexto:** D-014 diz "tokenização por regex de palavras" sem detalhar hífens e números.
- **Decisão:** regex `[a-z0-9]+` após normalização (minúsculas + unidecode). Hífens separam tokens ("bem-estar" → ["bem", "estar"]). Números são mantidos ("2001" vira token).
- **Motivo:** simplifica a regex, compatível com unigrama; números podem ser relevantes em títulos de filmes.
- **Decidido por:** R · **Status:** aceita

### D-029 · 2026-11-06 · Comparação RSLP × Snowball: Snowball confirmado (Q-003)
- **Contexto:** Q-003 pedia comparar os stemmers. Comparação feita em 35 palavras reais do corpus e consultas típicas.
- **Decisão:** Snowball PT. Diferenças em 10/35 palavras. Snowball produz radicais mais legíveis (aparecem na UI, nível 3): "amor" fica "amor" (RSLP: "am"), "astronauta" fica "astronaut" (RSLP: "astron"), "amar" fica "amar" (RSLP: "am").
- **Tradeoff:** RSLP agrupa mais agressivamente (pode casar mais sinônimos), mas perde legibilidade. Para um demo didático, legibilidade é prioritária.
- **Decidido por:** R · **Status:** aceita

### D-090 · 2026-11-06 · Contrato do serviço de busca, para trabalho em paralelo
- **Contexto:** as Sprints 5 (serviço e log), 6–7 (interface e explicabilidade) e 8 (entrega)
  seriam feitas em sequência. Em sequência, a interface só começa depois de o serviço terminar.
- **Decisão:** fixar antes de tudo um contrato em `src/ir_movies/query/types.py` e trabalhar as
  três frentes em paralelo, cada uma na sua branch:
  - `Movie`, `MovieHit`, `SearchResult` (dados), `Rewriter`, `QueryLoggerProtocol` e
    `SearchServiceProtocol` (protocolos), `MODEL_NAME`, `MAX_QUERY_CHARS`.
  - A interface depende **somente** de `SearchServiceProtocol` e recebe o serviço por injeção:
    não conhece o índice TF-IDF nem o log. O clique é registrado por `service.log_click`.
  - A interface não lê `config.yaml` para saber `top_k` nem `snapshot_id`: pede ao serviço
    (`k=None` usa `search.top_k`). Continua lendo os parâmetros de apresentação (`ui.*`,
    `tmdb.poster_size`).
  - `SearchResult` carrega identificadores e números; os dados de exibição vêm de
    `get_movie(movie_id)`, como `architecture.md` secao 3 já previa.
  - Cinco regras obrigatórias, documentadas no protocolo e testadas em `tests/test_contract.py`:
    (1) consulta vazia, só com palavras comuns ou sem palavra no acervo devolve lista vazia sem
    levantar exceção, com o rastreio preenchido; (2) a consulta é truncada em 300 caracteres pelo
    próprio serviço; (3) a soma das contribuições por termo é igual à pontuação (tolerância 1e-9);
    (4) a busca só registra no log quando recebe `session_id`; (5) determinismo do ranking.
  - Normalizações do carregador, para a interface ter uma regra só: `runtime` e `poster_path`
    viram `None` quando ausentes (o snapshot usa `0` e vazio); `tagline`, `director` e
    `release_date` ficam como string vazia.
  - O carregador resolve o parquet pelo `snapshot_id` de `data/snapshot_meta.json`, em vez de ter
    o nome do arquivo embutido no código: uma recoleta futura não quebra código nem teste.
  - `app_version` vem de `ir_movies.__version__` (não de `importlib.metadata`: no Colab o pacote
    é clonado, não instalado).
- **Convenção `IR_MOVIES_NO_LAUNCH`:** `build_app` monta e devolve o objeto Gradio e **nunca**
  chama `.launch()`. Só o notebook 02 lança, e só quando a variável de ambiente não vale
  exatamente `"1"`. É o que permite testar o notebook sem abrir servidor.
- **`tests/fakes.py`:** implementação de referência do contrato sobre o corpus de brinquedo,
  usando o índice e o pré-processamento **reais**, com log em memória. A interface é construída e
  testada contra ela antes de o serviço real existir. Pontuações inventadas não serviriam: a
  explicabilidade é construída sobre o invariante "soma das contribuições = cosseno", e a tela
  seria montada contra um invariante que não vale.
- **Alternativa descartada:** manter as sprints em sequência. Mais simples de coordenar, bem mais
  lento, e a interface seria escrita sem nunca ter sido exercitada contra um buscador de verdade.
- **Origem:** C · **Status:** aceita

### D-091 · 2026-11-06 · Correção de forma: neutralidade nos documentos versionados
- **Contexto:** 12 linhas de arquivos já versionados citavam ferramentas externas de
  desenvolvimento, em violação à regra de neutralidade do projeto. Entraram antes de os hooks
  locais existirem, e os hooks só inspecionam linhas **adicionadas** — nenhum commit futuro as
  pegaria.
- **Decisão:** reescrever essas linhas trocando apenas a formulação, em
  `.gitignore`, `docs/architecture.md`, `docs/decisions.md`, `docs/execution_plan.md` e os cinco
  diários de `sprint-00` a `sprint-04`.
- **Alcance:** é correção de **forma**. O conteúdo das decisões afetadas (D-006, D-017, D-018)
  permanece inalterado; nenhum status muda. Por isso não se aplica a regra de não editar decisão
  `aceita`, e não há revogação.
- **Critério aplicado à palavra "sessão":** removida quando se referia à rodada de trabalho com
  ferramenta externa; mantida quando nomeia um conceito real do domínio (sessão do navegador em
  `architecture.md`, sessão do Colab em `project_scope.md` e `execution_plan.md`).
- **Mudança que não é só de forma, registrada à parte:** as duas linhas do `.gitignore` que
  ignoravam a pasta de configuração local de ferramenta foram removidas, não reescritas. Reescrever
  só o comentário deixaria o caminho da pasta no arquivo, e o objetivo não seria atingido. A
  exclusão já está em `.git/info/exclude` (local), e citar arquivos de processo em arquivo
  versionado é justamente o que a regra de neutralidade proíbe.
- **Origem:** R (autorização) / C (levantamento e redação) · **Status:** aceita

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
- **Origem:** R (resposta a Q-001) / C (redação) · **Status:** aceita

### D-031 · 2026-11-06 · Formato do `session_id`
- **Decisão:** 16 caracteres hexadecimais aleatórios, gerados por `secrets.token_hex(8)`, pela
  função `new_session_id()` de `ir_movies.logging_jsonl`. Quem cria o identificador é a
  interface, uma vez por visita ao navegador; o serviço e o logger apenas o recebem e o gravam.
- **Motivo:** 64 bits aleatórios bastam para distinguir visitas numa demo, não carregam hora,
  máquina nem pessoa (ao contrário de UUID v1) e são curtos para ler no arquivo.
- **Alternativa descartada:** UUID v4 completo (36 caracteres, sem ganho prático aqui).
- **Origem:** C · **Status:** aceita

### D-032 · 2026-11-06 · Onde a latência é medida
- **Decisão:** `latency_ms` cobre do início de `search` até a montagem do `SearchResult`
  (reescrita, pré-processamento com rastreio, busca no índice, termos fora do vocabulário e
  criação dos `MovieHit`), medido com `time.perf_counter()`. Fora da medida: a construção do
  índice, a carga do snapshot e a escrita da linha de log (o relógio é lido antes do log).
- **Motivo:** o número serve para comparar buscas entre si e mostrar ao público quanto custa
  buscar; incluir E/S de disco misturaria outra grandeza.
- **Origem:** C · **Status:** aceita

### D-033 · 2026-11-06 · Comportamento do log desligado e de falhas de escrita
- **Decisão:** com `logging.enabled: false`, o `QueryLogger` não cria o diretório nem o arquivo
  e `log_search` e `log_click` não fazem nada. Com o log ligado, o diretório é criado na primeira
  escrita (não na construção). Se a escrita falhar (`OSError`), o erro vai para o `logging` da
  biblioteca padrão como aviso e a busca segue normalmente.
- **Motivo:** o log é observação, não função do buscador: disco cheio ou pasta sem permissão não
  pode derrubar a demonstração. Criar o diretório só ao escrever garante que "desligado" não
  deixa rastro no disco.
- **Origem:** C · **Status:** aceita

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
- **Origem:** C · **Status:** aceita

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
- **Origem:** C · **Status:** aceita

### D-036 · 2026-11-06 · Montagem do `SearchService` por injeção
- **Decisão:** `SearchService(snapshot, cfg, *, rewriter=None, logger=None, app_version=None)`
  recebe o acervo já carregado e o dicionário de configuração; `rewriter` padrão é
  `IdentityRewriter`, `logger` padrão é `QueryLogger.from_config`, `app_version` padrão é
  `ir_movies.__version__` (D-090). `SearchService.from_config()` faz o caminho de produção
  (lê `config.yaml`, carrega o snapshot e monta tudo). O pré-processador e o `TfidfIndex` são
  sempre construídos a partir de `text` e `tfidf` do `config.yaml`.
- **Motivo:** o mesmo construtor serve ao app (acervo real) e aos testes (acervo de brinquedo,
  log em `tmp_path`), sem ramos de teste no código de produção.
- **Origem:** C · **Status:** aceita

### D-037 · 2026-11-06 · Entradas fora do esperado em `search`
- **Decisão:** `raw_query` nulo é tratado como `""`. `k` negativo é tratado como 0 (lista
  vazia); `k=None` usa `search.top_k`. O truncamento em `MAX_QUERY_CHARS` (300) é feito antes do
  reescritor, de modo que `raw_query` no resultado e no log já vem truncado.
- **Motivo:** a regra 1 do contrato proíbe exceção por causa da consulta; `k` vem da interface,
  mas um valor inválido não deve produzir fatiamento negativo silencioso no índice.
- **Origem:** C · **Status:** aceita

### D-050 · 2026-11-06 · Nome público do app: `FilmUSP` (resolve Q-005)
- **Contexto:** Q-005 (nome público do app) estava aberta desde a Sprint 0; `config.yaml`
  trazia `ui.app_name: "Buscador de Filmes"` marcado como provisório.
- **Decisão:** o nome público é **`FilmUSP`**. Gravado em `config.yaml` (`ui.app_name`) e lido
  pelo cabeçalho da tela; o código não repete o nome em lugar nenhum.
- **Consequência:** `ui_spec.md` secao 1.1 ("nome do app + frase") fica resolvido; o cabeçalho
  mostra `FilmUSP` e a frase "Descreva um filme do seu jeito e veja como o buscador pensa."
- **Origem:** R · **Status:** aceita

### D-051 · 2026-11-06 · Nível 1: intensidade do destaque linear sobre a maior contribuição
- **Contexto:** `ui_spec.md` secao 1.5 pede "cor mais forte = contribuiu mais", sem fixar a escala.
  Duas opções: escala **linear** (proporcional à contribuição) ou **por posto** (1º, 2º, 3º lugar).
- **Decisão:** `explain.highlight` devolve uma intensidade contínua em `[0, 1]`, igual a
  `contribuição / maior contribuição do filme`. A escala é **relativa ao filme exibido**, não ao
  acervo: a leitura que a tela sustenta é "nesta sinopse, esta palavra pesou mais que aquela".
- **Renderização:** a intensidade contínua é agrupada em `ui.highlight_levels` faixas de cor
  (4, por padrão) na hora de gerar o HTML. Faixas discretas porque, num projetor, variação
  contínua de cor não é distinguível; 4 faixas são.
- **Por que não por posto:** o posto esconde a diferença de tamanho. Com dois termos de
  contribuição 0,30 e 0,29, o destaque por posto sugere uma diferença que não existe.
- **Degenerado:** se todas as contribuições forem zero, toda palavra que casa recebe intensidade
  `0.0` — casou, mas não somou nada. Honesto e visível.
- **Origem:** C · **Status:** aceita

### D-052 · 2026-11-06 · Nível 2: barras horizontais com rótulo numérico obrigatório
- **Decisão:** uma barra por palavra da pergunta que casou com o filme, ordenada por contribuição
  decrescente (a ordem que `TfidfIndex.contributions` já devolve). A largura é
  `contribuição / maior contribuição`, em porcentagem; ao lado da barra, sempre, o valor numérico
  da contribuição com a mesma formatação da pontuação (D-054).
- **Piso de largura de 2%:** uma contribuição muito pequena renderizaria uma barra de largura
  quase zero, indistinguível de barra nenhuma — e "não tem barra" se lê como "esta palavra não
  contou", o que seria falso. Então a largura tem piso de 2% (`ui.format.MIN_BAR_WIDTH_PERCENT`).
  O piso não engana: o número ao lado da barra é o valor real, e é ele que manda (ver o rótulo
  obrigatório acima). Acima do piso, a largura é exatamente a razão com a maior contribuição.
- **Motivo do rótulo:** `ui_spec.md` secao 3 exige que nada dependa só de cor. O rótulo também
  serve a quem olha de longe e não distingue comprimentos parecidos.
- **Rótulo da palavra:** a primeira forma de superfície (`TermContribution.surface_forms`), isto é
  a palavra como a pessoa escreveu (sem acento e em minúsculas, por causa do pré-processamento),
  e não o radical. O radical aparece no nível 3, onde é explicado.
- **Origem:** C · **Status:** aceita

### D-053 · 2026-11-06 · Limiar "palavra rara" × "palavra comum" em termos de IDF
- **Contexto:** `ui_spec.md` secao 1.5 pede um selo "palavra rara"/"palavra comum" por palavra,
  "conforme o IDF", sem fixar o corte. A interface não conhece o tamanho do acervo (o contrato
  D-090 não expõe isso), então o corte não pode ser calculado na hora.
- **Decisão:** parâmetro `ui.rare_idf_threshold` no `config.yaml`, valor inicial **3.3**.
  Palavra com `idf >= 3.3` recebe o selo "palavra rara"; abaixo disso, "palavra comum".
- **Derivação do 3.3:** com `smooth_idf: true` (D-015), o IDF do scikit-learn é
  `ln((1 + N) / (1 + df)) + 1`. Para "aparece em no máximo 10% do acervo" (`df <= 0.1 N`), com
  `N = 8002` filmes do snapshot atual, o corte é `ln(8003 / 801,2) + 1 = 3,30`. O número é,
  portanto, a tradução de uma regra que se explica em voz alta na feira: *rara = aparece em no
  máximo um filme em dez*.
- **Consequência conhecida:** o corte depende do tamanho do acervo. Uma recoleta que mude `N`
  muda o significado do 3,3; por isso o valor está em `config.yaml`, com a conta registrada aqui,
  e não embutido no código. No corpus de brinquedo de 5 filmes nenhum termo alcança 3,3 (o IDF
  máximo lá é `ln(6/2) + 1 = 2,10`), o que é esperado: o limiar é calibrado para o acervo real.
- **Alternativa descartada:** classificar relativamente, comparando as palavras da própria
  pergunta entre si. Seria enganoso — numa pergunta com duas palavras raras, uma delas receberia
  o selo "comum" sem ser comum.
- **Jargão:** o selo nunca escreve "IDF". A tela diz "raridade da palavra no acervo"
  (`ui_spec.md` secao 3).
- **Origem:** C · **Status:** aceita

### D-054 · 2026-11-06 · Pontuação com 3 casas decimais e vírgula; a soma exibida é a exata
- **Decisão:** toda pontuação e toda contribuição aparecem com `ui.score_decimals` casas
  decimais (3, conforme `ui_spec.md` secao 3) e **vírgula** como separador decimal, que é a
  convenção do português. Uma função só (`ui.format.format_score`) formata os números dos três
  níveis e da legenda da grade, para que a convenção não possa divergir entre eles.
- **Soma do nível 3:** o total exibido é a soma dos produtos em **precisão cheia**, arredondada na
  exibição — não a soma dos valores já arredondados. É o que mantém a identidade exigida por
  `ui_spec.md` secao 3: o total do nível 3 é, caractere a caractere, a pontuação da legenda.
- **Limitação assumida:** por isso, somar à mão os produtos arredondados da tabela pode dar
  0,001 de diferença em relação ao total. A tela avisa, em uma linha, que os valores estão
  arredondados para 3 casas. A alternativa (exibir o total como soma dos arredondados) quebraria
  a identidade com a legenda, que é a invariante que a Explicabilidade existe para mostrar.
- **Origem:** C · **Status:** aceita

### D-055 · 2026-11-06 · Componentes do Gradio: `Blocks` + `Gallery` de 5 colunas + `HTML`
- **Decisão:** `gr.Blocks` (não `gr.Interface`, que não permite este layout);
  `gr.Gallery(columns=5, allow_preview=False)` para a grade de pôsteres, com a legenda de cada
  item e o evento `.select` para a escolha do filme; `gr.HTML` para o painel de detalhes, os três
  níveis da Explicabilidade, as mensagens de estado e o rodapé.
- **Por que `gr.HTML` nos blocos didáticos:** barras com largura proporcional, destaque por faixa
  de cor e tabela com cabeçalho exigem controle de marcação que `gr.Markdown` não dá. O contraste
  e o tamanho de fonte pedidos para projeção ficam em um bloco de CSS só (`ui/styles.py`).
- **Por que `Gallery` e não 20 botões com imagem:** a grade é o único componente que já traz
  posição clicada (`gr.SelectData.index`), colunas configuráveis e número variável de itens sem
  recriar componentes. O número de resultados vem do serviço (`k=None` usa `search.top_k`), e a
  interface não precisa saber quantos são de antemão.
- **Versão:** `gradio==6.31.0`, já fixada em `requirements-app.txt` desde a Sprint 0 (D-021);
  esta decisão apenas confirma que o layout foi construído contra ela.
- **Origem:** C · **Status:** aceita

### D-056 · 2026-11-06 · Pôster ausente: arquivo SVG local embutido pelo Gradio
- **Contexto:** `poster_path` é `None` em parte do acervo (2 casos no snapshot atual) e
  `ui_spec.md` secao 2 pede "placeholder + título".
- **Decisão:** um arquivo SVG de texto em `src/ir_movies/ui/assets/no_poster.svg`, nas proporções
  de um pôster (2:3), com fundo escuro e a palavra "Sem pôster". O Gradio lê SVG local e o embute
  na página como `data:` URI, então o placeholder **não** depende de rede nem de pasta servida.
- **Por que não baixar nem gerar imagem:** o projeto não baixa pôsteres (usa o CDN da TMDB) e
  um SVG é texto — versionável, legível em revisão e sem binário no repositório.
- **Tamanho do pôster:** segue `tmdb.poster_size` (`w342`), seção que esta frente não possui e
  não alterou. A URL é `https://image.tmdb.org/t/p/{tamanho}{poster_path}`
  (`architecture.md` secao 4).
- **Origem:** C · **Status:** aceita

### D-057 · 2026-11-06 · `ui` dividido em textos, formatação, visão e montagem
- **Decisão:** `src/ir_movies/ui/` com cinco módulos de responsabilidade única:
  `texts.py` (todo texto de interface, em PT-BR), `format.py` (números, legendas, URL de pôster),
  `styles.py` (o CSS), `view.py` (funções que recebem serviço + configuração e devolvem o
  conteúdo da tela) e `app.py` (`build_app`: cria os componentes e liga os eventos, nada mais).
- **Motivo:** o conteúdo da tela — mensagens de estado, os três níveis, a legenda — é testável
  como função pura. Se ele morasse dentro dos manipuladores de evento do Gradio, só seria
  verificável abrindo o navegador, e a Explicabilidade é justamente a parte que não pode ser
  aceita "de olho".
- **`build_app` nunca chama `.launch()`** (convenção `IR_MOVIES_NO_LAUNCH` de D-090).
- **Assinatura:** `build_app(service, cfg)`. `architecture.md` secao 3 previa
  `build_app(service, snapshot)`, de quando a interface receberia os dados do filme direto. D-090
  mudou isso: os dados vêm de `service.get_movie`, e o segundo argumento passou a ser a
  configuração, de onde saem os parâmetros de apresentação. A tabela do `architecture.md` ficou
  para trás; o arquivo não pertence a esta frente, então o acerto vai como pedido de mudança.
- **Identificadores do DOM:** cada componente que recebe conteúdo tem `elem_id` próprio
  (`fu-message`, `fu-results`, `fu-details-panel`, `fu-level-1`, `fu-level-2`, `fu-level-3`), e o
  `Blocks` tem `ir-movies-app` — neutro, porque o nome público do app vive no `config.yaml` e não
  se repete no código (D-050). Além de servirem ao CSS, são o que permite um teste afirmar que
  **cada valor devolvido pelo manipulador chega ao componente certo**, e não só que a quantidade
  de valores confere. Cada bloco de conteúdo carrega também uma classe que só ele tem
  (`fu-details-block`, `fu-block-level1` a `fu-block-level3`), presente em todos os estados.
- **Origem:** C · **Status:** aceita

### D-058 · 2026-11-06 · `session_id` por carregamento de página; só o clique explícito é registrado
- **Decisão:** a interface gera um identificador aleatório (`uuid4`, hexadecimal) a cada
  carregamento de página, guardado em `gr.State`, e o passa ao serviço em `search` e `log_click`.
  Não há nada da pessoa nele: é um número sorteado, que separa uma visita da seguinte.
- **Decisão correlata:** o filme mostrado por padrão (o 1º resultado, `ui_spec.md` secao 1.4)
  **não** gera `log_click`. Só a escolha explícita de um pôster registra clique. Caso contrário
  todo resultado em 1º lugar apareceria como clicado, e o log de cliques não mediria nada.
- **Origem:** C · **Status:** aceita

### D-059 · 2026-11-06 · Estados da tela derivados do rastreio, e erro inesperado contido
- **Decisão:** os estados de `ui_spec.md` secao 2 são decididos nesta ordem, a partir do
  `SearchResult` (nunca de exceção, pela regra 1 de D-090):
  1. `trace.original_tokens` vazio → "consulta vazia" (cobre texto em branco e só pontuação);
  2. `trace.stems` vazio e `trace.stopped` não vazio → "só palavras comuns";
  3. sem resultados, havendo radicais → "nenhuma palavra no acervo";
  4. com resultados e `oov_terms` não vazio → sem mensagem; os termos aparecem no nível 3(d);
  5. `poster_path is None` → placeholder (D-056);
  6. qualquer exceção inesperada → a mensagem genérica, e o detalhe técnico vai para o log do
     servidor por `logging.exception`, nunca para a tela.
- **Textos:** copiados literalmente de `ui_spec.md` secao 2 para `ui/texts.py`. Os testes repetem
  o literal da especificação em vez de importar a constante: assim uma mudança silenciosa no
  texto falha o teste, em lugar de passar por comparar a constante consigo mesma.
- **Origem:** C · **Status:** aceita

### D-060 · 2026-11-06 · Parâmetros de apresentação e exemplos clicáveis no `config.yaml`
- **Decisão:** a seção `ui` do `config.yaml` passa a ter, além de `app_name`:
  `grid_columns` (5), `score_decimals` (3), `highlight_levels` (4), `rare_idf_threshold` (3.3),
  `max_examples` e `examples` (as perguntas clicáveis, com as duas de `ui_spec.md` secao 1.2).
- **Motivo:** nenhum número mágico no código, e quem conduz a feira pode trocar os exemplos sem
  abrir arquivo de código. O limite de 300 caracteres da caixa de texto **não** entra aqui: vem de
  `MAX_QUERY_CHARS`, do contrato, porque o serviço também o aplica e os dois têm de concordar.
- **Origem:** C · **Status:** aceita

### D-061 · 2026-11-06 · Notebook 02: serviço por injeção e lançamento condicional
- **Decisão:** o notebook 02 recebe o serviço de busca por injeção numa célula marcada, monta a
  tela com `build_app(service, cfg)` e só chama `.launch()` quando `IR_MOVIES_NO_LAUNCH != "1"`
  (D-090). A célula de setup funciona no Colab (clone do repositório e instalação de
  `requirements-app.txt`) e localmente (nada a instalar), decidindo por tentar importar
  `google.colab`.
- **Parâmetros de `launch`:** `share=True` (no Colab é o que dá um endereço acessível; localmente
  é inofensivo) e `inline=False`, para a tela abrir em aba própria — numa feira, projetar a aba
  cheia é melhor que a moldura dentro do notebook.
- **Célula final (Q-001):** quando `google.colab` existe, compacta `logs/` e oferece o download;
  fora do Colab, apenas informa onde os arquivos estão. Nada quebra em nenhum dos dois casos.
- **Origem:** C · **Status:** aceita

### D-062 · 2026-11-06 · A nota da TMDB é a única exceção à convenção de 3 casas
- **Contexto:** `ui_spec.md` secao 3 manda mostrar "sempre a pontuação com 3 casas decimais e a
  mesma convenção em todos os níveis". O painel de detalhes mostra também a **nota da TMDB**, que
  não é pontuação de busca: é a média de avaliação do filme, numa escala de 0 a 10.
- **Decisão:** a convenção de 3 casas (D-054) vale para **pontuação e contribuição** — os números
  que a Explicabilidade explica. A nota da TMDB aparece com **1 casa decimal** e vírgula
  (`6,1`), seguida do número de votos, que é o que a torna interpretável. `6,100` não é como
  ninguém escreve nota de filme, e a precisão extra seria falsa: a própria TMDB publica uma casa.
- **Por que não há confusão:** os dois números nunca aparecem no mesmo bloco. O painel de
  detalhes não mostra pontuação nenhuma; a pontuação vive na legenda da grade e nos três níveis.
- **Rastreabilidade:** a exceção está fixada em teste
  (`test_the_tmdb_rating_is_the_only_exception_in_the_details_panel`), que exige que **todo**
  número decimal do painel de detalhes tenha exatamente uma casa. Se um dia a pontuação entrar
  no painel, o teste cai e a decisão volta à mesa.
- **Origem:** C · **Status:** aceita

### D-070 · 2026-11-06 · Critério determinístico de seleção do acervo mínimo de testes
- **Contexto:** os testes de fumaça do notebook 02 e da interface precisam de um acervo pequeno que
  carregue em segundos, mas que exercite os estados que a interface trata (`ui_spec.md` secao 2):
  filme sem pôster, sem tagline, sem duração, sem direção. Um sorteio com semente não garante que
  esses casos entrem; um corte "os N mais populares" não garante nenhum deles (os dois filmes sem
  pôster do snapshot real não estão entre os 30 mais populares).
- **Decisão:** o acervo mínimo tem **30 filmes** (teto absoluto: 50) e é montado por regras, sem
  aleatoriedade. Ordem canônica de desempate: `(-popularity, id)`. Regras, em ordem de prioridade:
  1. todos os filmes sem pôster (`poster_path` nulo), até 3 (o snapshot real tem 2);
  2. os 3 mais populares sem tagline e com pôster;
  3. o mais popular com duração 0 (o snapshot usa 0 para duração desconhecida);
  4. o mais popular sem direção (`director` vazio);
  5. os 2 melhores resultados TF-IDF, calculados com o índice e o pré-processamento reais sobre o
     snapshot completo, para cada consulta de exemplo de `ui_spec.md` (secao 1.2): assim as
     consultas de exemplo que aparecem na tela devolvem resultado no acervo mínimo;
  6. os mais populares ainda não escolhidos, até completar 30.
- **Motivo:** cada regra tem um motivo verificável por teste (`tests/test_mini_snapshot.py`); a
  seleção é reproduzível por qualquer pessoa a partir do snapshot real.
- **Alternativa descartada:** amostra aleatória com semente fixa. Reprodutível, mas depende da
  versão do pandas/numpy para ser a mesma amostra, e não garante os estados de borda.
- **Limitação:** os limites (30, 3, 3, 1, 1, 2) são constantes no topo do script, e não chaves do
  `config.yaml`, porque o script gera uma fixture de teste, não faz parte do pipeline do produto.
  Se o Rafael preferir tudo em `config.yaml`, é uma mudança mecânica.
- **Origem:** C · **Status:** aceita

### D-071 · 2026-11-06 · Formato, determinismo e isolamento do acervo mínimo
- **Decisão:**
  - Mesmo formato do snapshot real: `movies_ptbr_<snapshot_id>.parquet` + `snapshot_meta.json`,
    em `tests/fixtures/mini_snapshot/`. O `snapshot_id` é **herdado** do snapshot de origem
    (resolvido por `data/snapshot_meta.json`, nunca embutido no script), para que o carregador do
    serviço, que resolve o parquet pelo `snapshot_id` (D-090), funcione igual nos dois diretórios.
  - O `snapshot_meta.json` do mini-acervo copia o da origem e ajusta o que deixou de ser verdade:
    `accepted`, `candidates_tested`, `rejections_by_reason`, `overview_word_count`,
    `file_size_bytes`; acrescenta o bloco `derived_from` (identifica a origem e o script).
    `created_utc` é herdado da origem: o script não lê o relógio.
  - Determinismo: sem aleatoriedade, sem relógio; JSON com `indent=2`, `ensure_ascii=False`, fim
    de linha `\n`. Gerar duas vezes produz bytes idênticos (teste), e a fixture versionada é conferida contra a gerada na hora (teste; o parquet byte a byte, o JSON pelo conteúdo, porque o controle de versão pode converter fim de linha): se alguém mudar o script ou a origem sem regerar a
    fixture, o teste falha.
  - Isolamento: o script só escreve na pasta de destino (padrão `tests/fixtures/mini_snapshot/`,
    ou a dada em `--dest`) e só lê `data/`. Um teste prova que `data/` não muda.
  - A fixture passa em `validate_snapshot` (D-025) e é validada pelo próprio script antes de gravar.
- **Risco aceito:** a igualdade byte a byte do parquet depende das versões fixadas de pyarrow e
  pandas (D-021). Se as versões mudarem, o teste de igualdade com a fixture versionada pode exigir
  regerar o arquivo.
- **Origem:** C · **Status:** aceita

### D-072 · 2026-11-06 · Como o notebook 02 é executado no teste de fumaça
- **Contexto:** o teste deve provar que "Run all" não quebra e que nenhum servidor abre. Um
  executor de notebook (`nbclient`, `nbconvert`, `papermill`) exigiria dependência nova em
  `requirements-dev.txt`, e as versões estão fixadas (D-021).
- **Decisão:** usar só o `jupytext` (já em `requirements-dev.txt`):
  1. copiar para uma pasta temporária um mini-projeto: `src/` (sem `__pycache__`),
     `config.yaml`, `notebooks/02_search_app.py` e o mini-acervo em `data/`. Como
     `PROJECT_ROOT` é derivado da localização do pacote, o notebook enxerga o mini-acervo como
     se fosse o `data/` do projeto e grava logs na pasta temporária, nunca no `logs/` real;
  2. rodar um subprocesso Python novo (`PYTHONPATH` apontando para a cópia, `IR_MOVIES_NO_LAUNCH=1`,
     diretório de trabalho `notebooks/`, como no Jupyter);
  3. o subprocesso lê o `.py` com `jupytext.read` e executa as células de código, em ordem, num
     único espaço de nomes (equivale a "Run all"). Linhas que começam com `%` ou `!` (magics do
     IPython, p. ex. `%pip install`) são ignoradas, e células em que **todas** as linhas são
     assim ficam vazias: a instalação de dependências é passo do Colab, não do teste;
  4. antes de executar, o subprocesso troca `gradio.Blocks.launch` por uma função que levanta
     erro: se alguma célula tentar abrir servidor, o teste falha. Esta é a prova de "nenhum
     servidor aberto" (e não a ausência de erro).
  - O teste afirma: código de saída 0, que ao menos uma célula de código foi executada
    (`CELLS_EXECUTED >= 1`; não compara com o total de células), que ao menos um `gradio.Blocks`
    foi criado, e que `launch` nunca foi chamado. Tempo limite do subprocesso: 180 s.
  - O teste executa o `.py`, e o README manda abrir o `.ipynb`; a equivalência dos dois é
    garantida por teste de sincronia à parte (D-077).
- **Alternativa descartada:** `nbclient`/`nbconvert`: dependência nova. Se o Rafael autorizar, o
  teste pode migrar para o executor padrão sem mudar o que ele afirma.
- **Limitação:** não é um kernel Jupyter de verdade; magics e comandos de shell são ignorados.
  O ensaio real no Colab (roteiro em `docs/rehearsal_checklist.md`) continua necessário.
- **Origem:** C · **Status:** aceita

### D-073 · 2026-11-06 · O teste de fumaça nasce com `skip` e é ativado na integração
- **Contexto:** a interface (`ui/app.py`) e o notebook 02 são entregues por outra frente, em
  paralelo (D-090). Na data desta decisão, `notebooks/02_search_app.py` não tem células de código.
- **Decisão:** o teste é escrito completo e fica com `@pytest.mark.skip(reason=...)`, com motivo
  explícito: depende da entrega da interface e do notebook 02, e é ativado na integração. Ativar
  é remover a linha do decorador. Não usar `xfail` (ocultaria uma falha real depois da
  integração) nem `try/except ImportError` silencioso (o teste passaria sem testar nada).
- **Origem:** C · **Status:** aceita

### D-074 · 2026-11-06 · Estrutura do README
- **Decisão:** o `README.md` é a cara pública do projeto e o roteiro de reprodução do zero. Ordem:
  1. o que é (e o que não é: sem BM25, embeddings ou modelos de linguagem na v1);
  2. como usar no Colab (clona, instala `requirements-app.txt`, abre o notebook 02);
  3. como rodar localmente (plano B): venv, instalação, Jupyter;
  4. versões e para que serve cada arquivo de requirements;
  5. dados: origem (TMDB), esquema resumido, como o snapshot foi gerado, como recoletar;
  6. privacidade: log de consultas anônimo;
  7. testes e estrutura do repositório;
  8. licença;
  9. atribuição TMDB (frase exata, ao final e também referenciada na seção de dados).
  Pontos de atenção, escritos no README de forma explícita: o Jupyter não está fixado em nenhum
  dos três arquivos de requirements (o README manda instalá-lo à parte, sem versão fixada); a
  primeira execução do pré-processamento baixa as *stopwords* do NLTK (exige internet uma vez); o
  endereço do repositório nos comandos é uma premissa não verificada.
  O README descreve o comportamento **documentado** (`ui_spec.md`, `architecture.md`); onde algo
  ainda não foi verificado de ponta a ponta (execução no Colab, interface), diz isso em um
  bloco "Estado de verificação", que deve ser reduzido pelo autor após o ensaio.
- **Texto obrigatório (testado em `tests/test_readme.py`):** a frase "Este produto usa a API da
  TMDB mas não é endossado nem certificado pela TMDB" e o aviso "As buscas são registradas de
  forma anônima".
- **Origem:** C · **Status:** aceita

### D-075 · 2026-11-06 · Roteiro de ensaio: formato e conteúdo
- **Decisão:** `docs/rehearsal_checklist.md` é um roteiro operacional com caixas de seleção e
  tabelas de anotação, em cinco partes: (A) preparação; (B) ensaio de 2 h contínuas no Colab,
  com medições a cada 15 min e registro de desconexões; (C) teste do plano B local; (D) teste de
  textos com 2 ou 3 pessoas leigas, com roteiro de tarefas e critérios de aprovação; (E) o que
  fazer se o Colab cair durante a feira. Cada passo é uma ação com resultado observável.
  Critérios de aprovação numéricos vêm de `project_scope.md` secao 5 (≤ 5 min para "Run all",
  ≤ 200 ms por busca, 2 h sem queda). O documento é ferramenta de trabalho: o Rafael preenche as
  tabelas e leva as conclusões para o diário.
- **Origem:** C · **Status:** aceita

### D-076 · 2026-11-06 · Itens da Sprint 8 que dependem de ação humana
- **Decisão:** na Sprint 8, só ficam marcados em `execution_plan.md` os itens verificáveis por
  comando nesta entrega. Ficam **desmarcados**: ensaio de 2 h no Colab, teste do plano B local
  (exigem o notebook 02 pronto e a máquina do autor), revisão final de `.gitignore`/segredos/`docs/`
  (depende da integração das três frentes) e a tag `v1.0` (publicação é do Rafael; criar tag
  está fora do que se faz neste fluxo). O item do README só é marcado com a ressalva de que o
  critério "reproduzível do zero" depende de um ensaio de instalação feito pelo autor.
- **Origem:** C · **Status:** aceita

### D-077 · 2026-11-06 · Teste de sincronia entre o `.py` e o `.ipynb` dos notebooks
- **Contexto:** o teste de fumaça (D-072) executa `notebooks/02_search_app.py`, mas o README manda
  abrir o `.ipynb` no Colab e no Jupyter. Sem verificação de sincronia, o teste provaria um
  arquivo que o usuário não executa.
- **Decisão:** `tests/test_notebook_sync.py` lê cada par com `jupytext` e compara, célula a
  célula, o tipo e o texto-fonte (sem saídas, metadados nem contadores de execução). Se o `.py`
  e o `.ipynb` divergirem, o teste falha e indica `python -m jupytext --sync notebooks/*.py`.
  Vale para todos os `notebooks/*.py`.
- **Alternativa descartada:** executar também o `.ipynb` no teste de fumaça. Exigiria um executor
  de notebook (dependência nova, D-072) para provar o mesmo que a sincronia já garante.
- **Consequência:** na integração, quem alterar o notebook 02 deve rodar o `--sync`; do contrário
  este teste falha.
- **Origem:** C · **Status:** aceita

---

## Questões abertas

| ID | Questão | Quando resolver |
|---|---|---|
| Q-001 | Como persistir o log quando rodar no Colab (baixar ao final? espelhar no Drive?) | Sprint 5 | Resolvida: D-030 — o log fica no disco do Colab e o autor o baixa à mão
| Q-002 | Versão do Python (igual à do Colab) | Sprint 0 | Resolvida: D-019 — Python >=3.13,<3.14
| Q-003 | RSLP × Snowball | Sprint 3 | Usar Snowball
| Q-004 | `min_df` e stopwords de consulta ("filme", "filmes"...) | Sprint 4 | min_df=1 e remover stopwords tradicionais (manter filme, filmes, film e etc...)
| Q-005 | Nome público do app | Sprint 6 | Resolvida: D-050 — nome `FilmUSP`
