# Sprint 00 — Ambiente e esqueleto

- **Data:** 2026-11-05 · **Branch:** `sprint0/setup` · **Tag:** `sprint-00`
- **Sessão do Claude Code:** primeira sessão

## O que foi feito
- Instalado Python 3.13.17 via winget (compatível com 3.13.18 do Colab)
- Criado venv com `py -3.13 -m venv .venv`
- Criados `pyproject.toml` (ruff, pytest, pacote editável), `.gitattributes` (`* text=auto` + filtro nbstripout)
- Criados 3 arquivos de requirements com versões fixadas (descobertas via `pip freeze`)
- Criado `config.yaml` com valores das decisões aceitas
- Criado esqueleto `src/ir_movies/` com 20 módulos vazios (docstrings PT-BR)
- Criados 2 notebooks jupytext (`01_collect_tmdb.py`, `02_search_app.py`) com `.ipynb` gerados
- Configurado nbstripout (filtro git registrado)
- Criados testes de fumaça (2 testes: import do pacote + import de todos os submódulos)
- Criado corpus de brinquedo (`tests/fixtures/toy_corpus.json`, 5 filmes fictícios PT-BR)
- Baixada fixture real da TMDB (`tests/fixtures/movie_278.json`, filme 278 — Um Sonho de Liberdade)
- Criado script auxiliar `scripts/fetch_fixture.py` para baixar fixtures da TMDB
- Criados `data/.gitkeep` e `logs/.gitkeep`; ajustado `.gitignore` para permitir `logs/.gitkeep`

## Decisões (IDs em `decisions.md`)
- D-019 — Versão do Python: >=3.13,<3.14 (`aceita`)
- D-020 — Gerenciador de ambiente: venv stdlib (`aceita`)
- D-021 — Dependências com versão fixada, 3 arquivos, requests+tenacity (`aceita`)

## Premissas assumidas
- Python 3.13.17 (winget) é compatível com 3.13.18 (Colab) para efeitos de bibliotecas
- Versões das bibliotecas descobertas via `pip install` sem pin + `pip freeze` (não havia como saber as versões de Nov 2026 antecipadamente)

## Desvios do plano
- Nenhum desvio significativo

## Como verificar
```
py -3.13 -m venv .venv_teste
.venv_teste\Scripts\activate
pip install -r requirements-dev.txt
pip install -e .
python -m pytest
python -m ruff check .
python -m jupytext --sync notebooks\01_collect_tmdb.py notebooks\02_search_app.py
```
Resultado esperado: 2 testes passam, ruff sem erros, jupytext sem erros.

## Resultado das verificações
- `pytest`: 2 passed (0.07s)
- `ruff check .`: All checks passed
- `ruff format --check .`: 34 files already formatted
- `jupytext --sync`: notebooks unchanged (já sincronizados)
- `nbstripout --status`: installed in repository

## Pendências e riscos
- Gradio 6.31.0 precisa ser testada no Colab (Sprint 6) — pode haver conflito de versão
- Cada clone do repo precisa rodar `nbstripout --install` uma vez (documentar no README, Sprint 8)

## Teach-back (explicação do Rafael, com as próprias palavras)
- *Por que 3 arquivos de requirements:* ...
- *O que o jupytext faz:* ...
