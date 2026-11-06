# Sprint 04 — Índice TF-IDF, busca e contribuições

- **Data:** 2026-11-06 · **Branch:** `sprint03/preprocessamento`
- **Sessão do Claude Code:** background job (mesma sessão da Sprint 3)

## O que foi feito
- Implementado `TfidfIndex` com `build()`, `search()`, `contributions()`, `oov_terms()` em `src/ir_movies/index/tfidf.py`
- Dataclasses `Hit(doc_id, score)` e `TermContribution(stem, surface_forms, idf, q_weight, d_weight, contribution)`
- 19 testes em `tests/test_tfidf.py` cobrindo os 5 invariantes de `architecture.md`
- Medição de latência e memória com o snapshot real (8.002 filmes)
- Inspeção manual de 10 consultas (resultados abaixo)

## Decisões (IDs em `decisions.md`)
- Nenhuma decisão nova. Q-004 já resolvida (min_df=1, sem extra_stopwords).

## Premissas assumidas
- `TfidfIndex.build(docs, preprocessor, cfg)` recebe textos já concatenados (D-013: title + tagline + overview + genres); a concatenação é responsabilidade do chamador
- `doc_id` nos resultados é a posição no array de docs (0-indexed); o chamador mapeia para o ID do filme

## Desvios do plano
- Nenhum

## Como verificar
```
python -m pytest tests/test_tfidf.py -v   # 19 testes (5 invariantes)
python -m pytest                           # 87 testes totais
python -m ruff check src/ir_movies/index/  # sem erros
```

## Resultado das verificações
- 19/19 testes do TF-IDF passando (5 invariantes)
- 87/87 testes totais passando (sem regressão)
- Linter sem erros

## Medições com o snapshot real

| Métrica | Valor |
|---|---|
| Filmes no snapshot | 8.002 |
| Vocabulário | 20.273 termos |
| Tempo de construção | 2.44 s |
| Memória (matriz esparsa) | 3.4 MB |
| Latência média (10 consultas) | 1.6 ms |
| Latência máxima | 2.1 ms |
| Latência mínima | 1.1 ms |
| Meta de latência (project_scope) | ≤ 200 ms |

## Inspeção de 10 consultas

| # | Consulta | Top 1 | Score | OOV | Obs. |
|---|---|---|---|---|---|
| 1 | "um tubarão assustador na praia" | Tubarão 3 | 0.639 | — | Top 3 são os filmes do Tubarão; bom |
| 2 | "robô que se apaixona" | Eu, Robô | 0.488 | — | A.I. em 3º; faz sentido |
| 3 | "guerra nas estrelas" | Stardust: O Mistério da Estrela | 0.359 | — | Star Wars não aparece no top 1 (sinopse PT-BR provavelmente não contém "guerra" + "estrelas" juntos) |
| 4 | "comédia romântica em Paris" | Paixão de Escritório | 0.348 | — | Resultados razoáveis |
| 5 | "super-herói que salva o mundo" | Pequenos Grandes Heróis | 0.514 | — | Bons resultados de heróis |
| 6 | "filme de terror com fantasmas" | Fantasma e CIA | 0.344 | — | "filme" pesa pouco (alta frequência → IDF baixo) |
| 7 | "aventura na selva amazônica" | Na Selva | 0.400 | — | Boiúna em 2º (Amazonas); bom |
| 8 | "drama sobre família brasileira" | Ver Ouvir | 0.310 | — | Scores mais baixos; termos comuns |
| 9 | "animação japonesa com dragões" | Dragões: O Presente do Fúria da Noite | 0.355 | — | Como Treinar seu Dragão em 2º |
| 10 | "investigação de crime misterioso" | Sombras de um Crime | 0.341 | — | Bom |

**Observações gerais:**
- Nenhuma consulta teve termos OOV — vocabulário cobre bem consultas em linguagem natural
- Consulta 3 ("guerra nas estrelas") mostra limitação esperada de TF-IDF: a tradução literal do conceito pode não estar na sinopse dos filmes Star Wars
- Consulta 6: "filme" tem IDF baixo, então contribui pouco — comportamento correto
- Latência consistentemente < 3 ms, muito abaixo da meta de 200 ms

## Pendências e riscos
- Nenhuma pendência da Sprint 4

## Teach-back (explicação do Rafael, com as próprias palavras)
- (a preencher pelo Rafael)
- Tema: como o score de cosseno é calculado e por que a soma das contribuições o reproduz
