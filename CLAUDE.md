# CLAUDE.md — ir_movies_ptbr

Buscador didático de filmes em PT-BR (dados da TMDB) para a feira de extensão do ICMC-USP.
Modelo da v1: **TF-IDF + cosseno**, com a seção **Explicabilidade** em 3 níveis.
Demo de ~2h no notebook do autor (Rafael), via Gradio no Colab (plano B: Jupyter local).

**Leia antes de qualquer tarefa:** `docs/project_scope.md`, `docs/execution_plan.md` (sprint atual) e `docs/decisions.md`.
Contratos entre módulos: `docs/architecture.md`. Interface: `docs/ui_spec.md`.

## Regras de ouro (rastreabilidade)

1. Toda escolha não trivial (biblioteca, hiperparâmetro, formato, estrutura) vira entrada em `docs/decisions.md` **antes** de implementar. IDs sequenciais `D-NNN`. Status inicial `proposta` até o Rafael confirmar.
2. Ambiguidade: pergunte, ou registre a premissa como `proposta`. Nunca decida em silêncio.
3. Decisão `aceita` não é editada. Para mudar, crie nova entrada com `Revoga: D-NNN`.
4. Fim de sprint: preencher `docs/journal/sprint-NN.md` (modelo em `docs/journal/_template.md`) e marcar o checklist em `docs/execution_plan.md`.
5. Não amplie o escopo. Fora da v1: BM25, embeddings, LLM (só a interface `Rewriter` com `IdentityRewriter`).
6. Não invente o comportamento da API da TMDB: use `tests/fixtures/` e a documentação oficial. Se não puder verificar, diga que não verificou.

## Fluxo de trabalho

- Uma sprint por sessão. Comece em **modo de planejamento**: proponha arquivos, premissas, decisões novas e como verificar; espere aprovação.
- Passos pequenos, rodando os testes a cada passo. O critério de conclusão da sprint deve ser verificável por comando.
- Commits pequenos, mensagem `sprint-NN: resumo (D-NNN)`. `git add/commit/push` exigem aprovação do Rafael.
- Ao final, explique em linguagem simples o que foi feito: o Rafael precisa entender e defender o código.

## Convenções

- Versão do Python fixada na Sprint 0 (registrada em decisão). Mesma versão do Colab.
- Identificadores e nomes de arquivo em **inglês**; docstrings, comentários, docs e textos da UI em **PT-BR**.
- Lógica em `src/ir_movies/`. Notebooks são finos (só orquestram), em par jupytext (`.py` percent ↔ `.ipynb`). Edite o `.py`.
- Parâmetros só em `config.yaml` (sem números mágicos). Semente fixa se houver aleatoriedade.
- Dependências com versão fixada em `requirements-app.txt`, `requirements-collect.txt`, `requirements-dev.txt`.
- Lint e formatação: ruff. Testes: pytest.

## Comandos (confirmar na Sprint 0)

```
python -m pytest
python -m ruff check .
python -m ruff format .
python -m jupytext --sync notebooks/*.py
```

## Segredos e dados

- Nunca ler, exibir ou commitar `.env` (`TMDB_READ_ACCESS_TOKEN`). Modelo em `.env.example`.
- `logs/` nunca vai ao git (privacidade). `data/` com o snapshot final vai ao git; `data/raw/` e `data/checkpoints/` não.
- Atribuição TMDB obrigatória no README e no rodapé do app.

## Não faça

- Não baixe pôsteres: use as URLs do CDN da TMDB.
- Não registre IP nem qualquer dado pessoal nos logs.
- Não reabra decisões `aceita`; proponha revogação.
