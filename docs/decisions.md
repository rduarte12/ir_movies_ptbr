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
- **Decidido por:** C · **Status:** aceito

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
- **Decidido por:** C · **Status:** Aceito

### D-016 · 2026-11-05 · Snapshot em parquet, versionado
- **Decisão:** `data/movies_ptbr_YYYYMMDD.parquet` + `data/snapshot_meta.json` no git (sem Git LFS).
- **Decidido por:** C · **Status:** Aceito

### D-017 · 2026-11-05 · Segredos
- **Decisão:** token de leitura da TMDB em `.env` (`TMDB_READ_ACCESS_TOKEN`), enviado em header `Authorization: Bearer`. `.env.example` versionado. As ferramentas de desenvolvimento não leem `.env`
  (regra de permissão local).
- **Decidido por:** C · **Status:** aceita

### D-018 · 2026-11-05 · Processo de desenvolvimento por sprints
- **Decisão:** uma sprint por rodada de trabalho; planejar antes de implementar; branch e PR por sprint; commits pequenos; diário por sprint; tag `sprint-NN`; `git add/commit/push` exigem aprovação.
- **Decidido por:** C · **Status:** proposta

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
- **Decidido por:** C · **Status:** proposta

### D-023 · 2026-11-05 · Política de retry e rate-limit do cliente TMDB
- **Contexto:** a documentação da TMDB (https://developer.themoviedb.org/docs/rate-limiting) indica limite superior de ~40 req/s e pede respeitar HTTP 429.
- **Decisão:**
  - Retry via `tenacity`: backoff exponencial, `max_attempts` e `backoff_factor` em `config.yaml`.
  - Retry em: HTTP 429 (Too Many Requests), 5xx (erro de servidor), erros de conexão (`ConnectionError`, `Timeout`).
  - Não fazer retry em 404 (filme não existe) — propagar a exceção.
  - Rate limit: `time.sleep(1/rate_limit_rps)` entre chamadas. Valor padrão: `rate_limit_rps: 20` (conservador, ~metade do limite real).
  - Sem concorrência no Sprint 1 (cliente sequencial). `max_concurrency` será usado pelo pipeline na Sprint 2.
- **Verificado:** rate limit documentado como ~40 req/s sem limites formais publicados.
- **Decidido por:** C · **Status:** proposta

### D-024 · 2026-11-05 · Formato do checkpoint incremental
- **Contexto:** o pipeline (Sprint 2) precisa retomar a coleta sem re-buscar filmes já processados na API.
- **Decisão:**
  - `data/checkpoints/accepted_movies.jsonl` — JSON bruto completo de cada filme aceito (uma linha por filme).
  - `data/checkpoints/progress.jsonl` — `{"id": int, "status": "accepted"|"rejected"|"error", "reason": str|null}` por candidato processado.
  - Retomada: carrega os dois arquivos; pula candidatos cujo ID já aparece em `progress.jsonl`.
  - Flush a cada N candidatos processados (`snapshot.checkpoint_interval` em `config.yaml`, padrão 500).
- **Motivo:** `progress.jsonl` fornece estatísticas de rejeição para `snapshot_meta.json`; `accepted_movies.jsonl` evita re-fetch.
- **Decidido por:** C · **Status:** proposta

### D-025 · 2026-11-05 · Validações do snapshot
- **Decisão:** após escrever o parquet, verificar:
  - Contagem de linhas == nº de aceitos
  - Sem IDs duplicados
  - Nenhum `overview` nulo ou com < 5 palavras
  - Todo `vote_count >= 2`
  - Colunas obrigatórias nunca nulas: `id`, `title`, `overview`
  - Colunas que admitem nulo: `poster_path`, `tagline`, `runtime`, `director`, `release_date`
- **Registrar no meta:** contagem por motivo de rejeição, distribuição de tamanho de sinopse (mín/mediana/máx palavras), tamanho do arquivo em disco.
- **Decidido por:** C · **Status:** proposta

### D-026 · 2026-11-05 · Pipeline de coleta sequencial
- **Contexto:** D-023 mencionava `max_concurrency` para Sprint 2, mas a concorrência com threads adiciona complexidade (rate-limiter compartilhado, tratamento de erro em threads) sem ganho significativo para uma coleta que roda uma vez.
- **Decisão:** pipeline sequencial usando `TmdbClient` diretamente. `max_concurrency` em `config.yaml` fica como placeholder para versão futura.
- **Motivo:** código mais simples e explicável (teach-back); a taxa de 20 req/s sequencial já é suficiente (~30–60 min para o corpus).
- **Decidido por:** C · **Status:** proposta

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
- **Origem:** C · **Status:** proposta

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
- **Origem:** R (autorização) / C (levantamento e redação) · **Status:** proposta

---

## Questões abertas

| ID | Questão | Quando resolver |
|---|---|---|
| Q-001 | Como persistir o log quando rodar no Colab (baixar ao final? espelhar no Drive?) | Sprint 5 | Salvar no colab. EU baixo o arquivo depois manualmente
| Q-002 | Versão do Python (igual à do Colab) | Sprint 0 | Resolvida: D-019 — Python >=3.13,<3.14
| Q-003 | RSLP × Snowball | Sprint 3 | Usar Snowball
| Q-004 | `min_df` e stopwords de consulta ("filme", "filmes"...) | Sprint 4 | min_df=1 e remover stopwords tradicionais (manter filme, filmes, film e etc...)
| Q-005 | Nome público do app | Sprint 6 | A ser decedido
