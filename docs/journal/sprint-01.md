# Sprint 01 — Coleta: IDs e cliente TMDB

- **Data:** 2026-11-05 · **Branch:** `sprint01/tmdb-client` · **Tag:** `sprint-01`

## O que foi feito
- Verificação da documentação oficial da TMDB: URL do export diário, campos do JSONL, ausência de autenticação, rate limits (~40 req/s)
- `config.py`: `load_config()` lê YAML e valida chaves obrigatórias; resolve `config.yaml` a partir da raiz do projeto (funciona de qualquer diretório)
- `tmdb/ids.py`: `download_id_export()` baixa o export gzipped com fallback para o dia anterior; `load_candidates()` filtra adult, ordena por popularidade
- `tmdb/client.py`: `TmdbClient.get_movie()` com Bearer token, retry via tenacity (backoff exponencial em 429/5xx/conexão), rate-limit configurável (20 req/s padrão)
- Fixture de teste `export_sample.jsonl.gz` (6 entradas, mix adult/não-adult)
- 19 testes novos (config: 5, ids: 6, client: 8), todos sem rede
- Notebook 01 com células de orquestração: setup, download export, candidatos, busca de 50 filmes, exibição de 3 exemplos
- `config.yaml`: adicionado `rate_limit_rps: 20`

## Decisões (IDs em `decisions.md`)
- D-022 — Formato e download do export diário de IDs da TMDB (`proposta`)
- D-023 — Política de retry e rate-limit do cliente TMDB (`proposta`)

## Premissas assumidas
- Nenhuma. URL do export e campos foram verificados com download real; rate limits conferidos na documentação oficial.

## Desvios do plano
- `load_config()` precisou resolver o caminho a partir da raiz do projeto (via `PROJECT_ROOT`) em vez de aceitar path relativo — o notebook roda de `notebooks/`, não da raiz. Corrigido após o primeiro teste manual.

## Como verificar
- `python -m pytest` — 21 testes passam sem rede
- `python -m ruff check src/ tests/ notebooks/` — sem erros
- `python -m jupytext --sync notebooks/*.py` — sincronização sem erros
- Com `.env` preenchido: rodar notebook 01 → baixa 50 filmes e exibe 3 exemplos

## Resultado das verificações
- pytest: 21 passed (0.33s)
- ruff: All checks passed
- jupytext: sincronizado sem alterações
- Notebook: executado com sucesso, 50 filmes baixados, 3 exemplos exibidos

## Pendências e riscos
- D-022 e D-023 ainda como `proposta` — aguardam confirmação do Rafael
- Export da TMDB sem autenticação hoje, mas a documentação avisa que pode mudar no futuro
- O erro pré-existente em `scripts/fetch_fixture.py` (linha longa, ruff E501) não foi corrigido — está fora do escopo da sprint

## Teach-back (explicação do Rafael, com as próprias palavras)
- Por que sobre-buscar candidatos: porque os filtros de qualidade (sinopse com ≥5 palavras, votos ≥ 2) dependem dos detalhes do filme, que só obtemos chamando a API. É melhor ter menos filmes de qualidade do que encher o acervo com lixo. O `target_size` é um teto, não uma meta obrigatória.
