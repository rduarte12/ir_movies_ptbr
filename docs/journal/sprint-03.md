# Sprint 03 — Pré-processamento PT-BR

- **Data:** 2026-11-06 · **Branch:** `sprint03/preprocessamento`
- **Sessão do Claude Code:** background job

## O que foi feito
- Implementado `Preprocessor` com `tokens(text)` e `trace(text)` em `src/ir_movies/text/preprocess.py`
- Dataclass `PreprocessTrace` com: `original_tokens`, `stopped`, `stems`, `stem_to_surface`
- Pipeline: minúsculas → unidecode → regex `[a-z0-9]+` → stopwords NLTK PT (normalizadas sem acento) → Snowball PT
- 14 testes em `tests/test_preprocess.py`: caixa, acentos, hífens, números, stopwords, stopwords acentuadas, consultas completas, trace, determinismo
- Comparação RSLP × Snowball em 35 palavras: 10 diferenças; Snowball produz radicais mais legíveis
- Exportações em `text/__init__.py`

## Decisões (IDs em `decisions.md`)
- D-028 — Tokenização: hífens separam, números mantidos (`aceita`)
- D-029 — Comparação RSLP × Snowball: Snowball confirmado (`aceita`)

## Premissas assumidas
- NLTK stopwords PT são suficientes como base; `extra_stopwords` vazio (TF-IDF penaliza via IDF)
- Download do NLTK (`stopwords`) feito silenciosamente no construtor do `Preprocessor`

## Desvios do plano
- Nenhum

## Como verificar
```
python -m pytest tests/test_preprocess.py -v   # 14 testes passam
python -m ruff check src/ir_movies/text/        # sem erros
python -m pytest                                # 68 testes passam (sem regressão)
```

## Resultado das verificações
- 14/14 testes de pré-processamento passando
- 68/68 testes totais passando
- Linter sem erros

## Pendências e riscos
- Nenhuma pendência da Sprint 3

## Teach-back (explicação do Rafael, com as próprias palavras)
- (a preencher pelo Rafael)
- Tema: o que é stemming e o que ele erra em português (ex.: "amor" e "amar" convergem no Snowball; "casa" substantivo e "casa" verbo também; "bom"/"boa" podem não convergir)
