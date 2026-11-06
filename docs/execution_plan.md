# Plano de execução — Sprints

> Uma sprint por rodada de trabalho. Cada sprint: planejar → aprovar → implementar → verificar → registrar.
> Ao concluir: marcar o checklist, preencher `docs/journal/sprint-NN.md`, registrar decisões novas, commit/PR, tag `sprint-NN`.
> "Teach-back" = o que o Rafael deve conseguir explicar com as próprias palavras antes de fechar a sprint.

---

## Sprint 0 — Ambiente e esqueleto

**Depende de:** nada. **Decisões a registrar:** versão do Python (Q-002), gerenciador de ambiente, versões fixadas.

- [x] Descobrir a versão do Python do Colab e fixar a mesma localmente
- [x] Criar ambiente virtual; criar `requirements-app.txt`, `requirements-collect.txt`, `requirements-dev.txt` com versões fixadas
- [x] `pyproject.toml` mínimo (config de ruff, pytest, pacote `src/ir_movies` instalável em modo editável)
- [x] Criar estrutura de pastas de `architecture.md` (módulos vazios com docstring)
- [x] `config.yaml` inicial; `.env.example`; `.gitattributes` (`* text=auto`, evita ruído de CRLF no Windows)
- [x] Salvar 1 resposta real de `/movie/{id}` em `tests/fixtures/` (sem token) e um corpus de brinquedo para TF-IDF
- [x] Configurar jupytext e nbstripout; confirmar os comandos do projeto
- [x] Teste "fumaça" (`pytest` passa com 1 teste trivial)

**Critério de conclusão:** `python -m pytest`, `ruff check` e `jupytext --sync` rodam sem erro num ambiente limpo.
**Teach-back:** por que há 3 arquivos de requirements; o que o jupytext faz.

## Sprint 1 — Coleta: IDs e cliente TMDB

**Depende de:** 0. **Decisões:** formato do export, política de retry/concorrência.

- [ ] Ler a documentação oficial da TMDB (export de IDs, detalhes de filme, limites de taxa) e registrar o que foi verificado
- [ ] `tmdb.ids`: baixar/ler export, excluir `adult`, ordenar por `popularity`
- [ ] `tmdb.client`: `get_movie(id)` com Bearer token, `language=pt-BR`, `append_to_response=credits,keywords`, retry com backoff
- [ ] Testes com HTTP simulado e com a fixture real (sem rede)
- [ ] Notebook 01: células de listagem de candidatos (amostra pequena, ex.: 50 filmes)

**Critério de conclusão:** com o token no `.env`, o notebook baixa 50 filmes e exibe 3 exemplos; testes passam sem rede.
**Teach-back:** por que sobre-buscar candidatos (D-003).

## Sprint 2 — Coleta: filtros, checkpoint e snapshot

**Depende de:** 1. **Decisões:** adulto (adendo D-004), formato final do parquet (D-016).

- [ ] `collect.filters`: ≥ 5 palavras na sinopse, `vote_count ≥ 2`, `adult=false`; motivo de rejeição por filme
- [ ] `collect.pipeline`: busca detalhes dos top 20.000 candidatos e filtra (D-027); checkpoint incremental e retomada
- [ ] `collect.snapshot`: escreve parquet e `snapshot_meta.json` (esquema de `architecture.md`)
- [ ] Verificações de dados: contagem após cada filtro, nulos por coluna, IDs duplicados, distribuição do tamanho das sinopses, tamanho do arquivo
- [ ] Rodar a coleta completa localmente; commitar o snapshot (se ≤ 50 MB)

**Critério de conclusão:** parquet com ≤ 20.000 linhas (quantas passarem nos filtros) passando nas verificações, meta preenchido, retomada testada interrompendo a coleta.
**Teach-back:** o que está em `snapshot_meta.json` e por que.

## Sprint 3 — Pré-processamento PT-BR

**Depende de:** 0 (pode usar a fixture). **Decisões:** RSLP × Snowball (Q-003), stopwords de consulta.

- [x] `Preprocessor.tokens` e `.trace` conforme D-014 (stopwords normalizadas sem acento)
- [x] Testes: acentos, hífen, números, caixa, stopwords, perguntas completas
- [x] Comparar RSLP × Snowball em ~30 palavras/frases reais; registrar a escolha

**Critério de conclusão:** testes passam; a decisão sobre o stemmer está registrada com exemplos.
**Teach-back:** o que é stemming e o que ele erra em português.

## Sprint 4 — Índice TF-IDF, busca e contribuições

**Depende de:** 2 e 3. **Decisões:** `min_df`, stopwords de consulta (Q-004).

- [x] `TfidfIndex.build` / `.search` conforme D-015
- [x] `TfidfIndex.contributions` e testes dos **invariantes 1–5** de `architecture.md`
- [x] Teste em corpus de brinquedo com valores calculados à mão
- [x] Medir latência e tamanho em memória com os 20 mil filmes; olhar manualmente 10 consultas e anotar observações no diário

**Critério de conclusão:** invariantes passam; latência ≤ meta do escopo; 10 consultas inspecionadas e anotadas.
**Teach-back:** como o score de cosseno é calculado e por que a soma das contribuições o reproduz.

## Sprint 5 — Pipeline de consulta, Rewriter e log

**Depende de:** 4. **Decisões:** persistência do log no Colab (Q-001).

- [x] `Rewriter` (protocolo) + `IdentityRewriter`
- [x] `SearchService.search` (reescrita → índice → resultado com trace e termos fora do vocabulário)
- [x] `QueryLogger` com esquema de `architecture.md`; testes (inclui: nada de IP, uma linha por evento)
- [x] Decidir e registrar como o log sai do Colab

**Critério de conclusão:** teste de ponta a ponta (consulta → resultado → linha de log) passa.
**Teach-back:** onde um LLM entraria e o que mudaria (determinismo).

## Sprint 6 — Notebook 02: interface de busca

**Depende de:** 5. **Decisões:** nome do app (Q-005), tamanho do pôster, versão do Gradio.

- [x] Célula de setup para Colab e local (clone, instalação, carga do snapshot)
- [x] Busca + exemplos clicáveis + grade de resultados + painel de detalhes (conforme `ui_spec.md`)
- [x] Estados: consulta vazia, sem resultados, sem pôster
- [ ] Rodar no Colab com a versão fixada do Gradio — **pendência manual** (ver `docs/journal/sprint-06.md`)

**Critério de conclusão:** "Run all" numa sessão nova do Colab abre a interface e permite buscar e clicar.
**Teach-back:** o caminho de uma consulta, da caixa de texto ao pôster na tela.

## Sprint 7 — Explicabilidade (3 níveis)

**Depende de:** 6 e 4. **Decisões:** visual das barras, escala de intensidade do destaque.

- [x] Nível 1: sinopse com destaque proporcional à contribuição (`explain.highlight`)
- [x] Nível 2: barras de contribuição por palavra
- [x] Nível 3: passo a passo (tokens → ignoradas → radicais → pesos → soma = score)
- [ ] Textos em linguagem simples conforme `ui_spec.md`; revisar com 2–3 pessoas leigas — textos escritos; a revisão com pessoas é **pendência manual** (ver `docs/journal/sprint-07.md`)

**Critério de conclusão:** para qualquer filme clicado, os 3 níveis aparecem e os números do nível 3 batem com o score exibido.
**Teach-back:** por que "palavra rara pesa mais" (IDF) aparece na tela.

## Sprint 8 — Ensaio, README e entrega v1

**Depende de:** todas.

- [ ] Ensaio de 2h contínuas no Colab (anotar desconexões e lentidão)
- [ ] Testar o plano B local (Jupyter)
- [ ] `README.md`: o que é, como rodar (local e Colab), versões, origem dos dados, **atribuição TMDB**, aviso de log anônimo
- [ ] Revisar `.gitignore`, segredos e `docs/`
- [ ] Tag `v1.0`

**Critério de conclusão:** repositório reproduzível do zero seguindo só o README.
