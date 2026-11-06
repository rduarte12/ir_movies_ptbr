# Registro de decisões

Formato: `D-NNN · data · título`. Status: `aceita` | `proposta` (aguarda confirmação do Rafael) | `revogada` (por D-NNN).
Regra: decisão `aceita` não se edita; para mudar, nova entrada com `Revoga: D-NNN`.
"Decidido por": Rafael (R) ou Claude (C, sempre `proposta` até confirmação).

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
- **Adendo (proposta, C):** excluir também `adult=true`, por causa do público (inclui ensino médio). **Status do adendo:** proposta

### D-005 · 2026-11-05 · Modelo da v1: apenas TF-IDF + cosseno
- **Decisão:** sem BM25, sem embeddings. Motivo: público leigo + determinismo + explicabilidade exata. BM25 pode entrar em versão futura.
- **Decidido por:** R · **Status:** aceita

### D-006 · 2026-11-05 · Estrutura: dois notebooks finos + pacote `src/`
- **Decisão:** `01_collect_tmdb` (local) e `02_search_app` (Colab). Lógica em `src/ir_movies/`. Notebooks em par jupytext (`.py` percent ↔ `.ipynb`); `.ipynb` commitado (Colab abre pelo GitHub), com saídas removidas (nbstripout).
- **Motivo:** a IA edita `.py` com segurança e os diffs ficam legíveis.
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
- **Decisão:** token de leitura da TMDB em `.env` (`TMDB_READ_ACCESS_TOKEN`), enviado em header `Authorization: Bearer`. `.env.example` versionado. O Claude Code não lê `.env` (regra de permissão).
- **Decidido por:** C · **Status:** aceita

### D-018 · 2026-11-05 · Processo de desenvolvimento com IA
- **Decisão:** uma sprint por sessão; planejar antes de implementar; branch e PR por sprint; commits pequenos; diário por sprint; tag `sprint-NN`; `git add/commit/push` exigem aprovação.
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

---

## Questões abertas

| ID | Questão | Quando resolver |
|---|---|---|
| Q-001 | Como persistir o log quando rodar no Colab (baixar ao final? espelhar no Drive?) | Sprint 5 | Salvar no colab. EU baixo o arquivo depois manualmente
| Q-002 | Versão do Python (igual à do Colab) | Sprint 0 | Resolvida: D-019 — Python >=3.13,<3.14
| Q-003 | RSLP × Snowball | Sprint 3 | Usar Snowball
| Q-004 | `min_df` e stopwords de consulta ("filme", "filmes"...) | Sprint 4 | min_df=1 e remover stopwords tradicionais (manter filme, filmes, film e etc...)
| Q-005 | Nome público do app | Sprint 6 | A ser decedido
