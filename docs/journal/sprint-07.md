# Sprint 07 — Explicabilidade (3 níveis)

- **Data:** 2026-11-06 · **Branch:** `sprint-06-07/interface-explicabilidade` · **Tag:** `sprint-07`

## O que foi feito

- `src/ir_movies/explain.py`: `highlight(text, contributions)` divide a sinopse em segmentos
  `(pedaço do texto, intensidade)`, com intensidade em `[0, 1]` proporcional à contribuição do
  termo que casou (D-051).

  Duas exigências moldaram o módulo:

  1. **nada se perde** — concatenar os segmentos reproduz a sinopse caractere a caractere, com
     acentos, caixa e pontuação. É teste obrigatório, e roda também sobre o texto real do acervo
     de brinquedo;
  2. **o casamento é por radical** — a sinopse passa pelo mesmo pré-processamento do índice
     (minúsculas, sem acento, stemming Snowball) só para *decidir* o que destacar; o segmento
     devolvido carrega o texto original. É o que faz "assustador" na pergunta destacar
     "assustadora" na sinopse, que é o que o índice de fato fez.

  O casamento é feito palavra por palavra, e não por posição no texto normalizado: remover
  acentos pode mudar o comprimento da string, e aí as posições não serviriam para recortar o
  texto original.

- **Nível 1** (`view.level1_html`): a sinopse com as palavras destacadas, em quatro faixas de cor
  crescentes com sublinhado crescente — num projetor, variação contínua de cor não se distingue.
- **Nível 2** (`view.level2_html`): uma barra horizontal por palavra, largura relativa à maior
  contribuição, **sempre** com o valor numérico ao lado, e o selo "palavra rara"/"palavra comum"
  conforme o limiar de `ui.rare_idf_threshold` (D-053). A tela nunca escreve "IDF": o selo é
  explicado como "raridade da palavra no acervo".
- **Nível 3** (`view.level3_html`): o passo a passo — sua pergunta; palavras ignoradas por serem
  comuns; palavras reduzidas ao radical (com a seta `palavra → radical`); palavras que não
  existem no acervo; a tabela `radical · peso na pergunta · peso no filme · produto`; e a soma
  dos produtos, que é a pontuação.
- Os três níveis ficam visíveis ao mesmo tempo, antes e depois da busca (D-010).
- `tests/test_explain.py`: 29 testes. As verificações dos níveis na tela estão em
  `tests/test_ui.py`, junto com o resto da interface.

## Decisões (IDs em `decisions.md`)

Registradas em `docs/decisions_trilha_C.md`.

- D-051 — Nível 1: intensidade do destaque linear sobre a maior contribuição (`proposta`)
- D-052 — Nível 2: barras horizontais com rótulo numérico obrigatório (`proposta`)
- D-053 — Limiar "palavra rara" × "palavra comum" em termos de IDF (`proposta`)
- D-054 — Pontuação com 3 casas decimais e vírgula; a soma exibida é a exata (`proposta`)

## Premissas assumidas

- **Escala do destaque relativa ao filme exibido**, não ao acervo: a leitura que a tela sustenta é
  "nesta sinopse, esta palavra pesou mais que aquela". Com escala absoluta, um filme de pontuação
  baixa apareceria todo pálido e não se explicaria nada.
- **Vírgula como separador decimal**, que é a convenção do português. `ui_spec.md` fixa as 3 casas
  e não fala do separador.
- **Limiar de raridade 3,3**, que é a tradução de "aparece em no máximo um filme em dez" para o
  acervo atual de 8.002 filmes. A conta está em D-053. O valor está no `config.yaml` porque
  depende do tamanho do acervo.
- O `Preprocessor` usado pelo destaque é construído a partir da mesma seção `text` do
  `config.yaml` que o índice usa. Não é o *mesmo objeto* do serviço: o contrato (D-090) não expõe
  o pré-processador. Mesma configuração, mesmo comportamento — ver o pedido de mudança abaixo.

## Desvios do plano

- `architecture.md` secao 3 previa `highlight(text, matched_stems, weights)`. A assinatura
  entregue é `highlight(text, contributions, text_cfg=None)`: recebe a lista de
  `TermContribution` que o serviço já devolve, em vez de dois argumentos derivados dela. Menos
  oportunidade de os dois chegarem fora de sincronia. `architecture.md` não pertence a esta
  frente; fica como pedido de mudança.

## Como verificar

```
python -m pytest tests/test_explain.py tests/test_ui.py -q
```

O teste que mais importa é `TestLossless`: para 11 textos diferentes, mais todas as sinopses do
acervo de brinquedo, `"".join(segmentos) == texto`.

Para a identidade entre os níveis, `TestLevelThreeNumbers` extrai o número da legenda da grade e
o número da soma do nível 3 do HTML gerado e compara os dois, e também compara os dois com a soma
das contribuições calculada pelo índice.

## Resultado das verificações

- `python -m pytest tests/test_explain.py tests/test_ui.py -q`: 97 testes, 0 falhas.
- `python -m pytest -q` (tudo): 218 testes, 0 falhas.
- Soma do nível 3 igual à pontuação da legenda, com 3 casas, para todos os resultados de uma
  consulta do acervo de brinquedo.
- Produto de cada linha da tabela igual a `peso na pergunta × peso no filme`, com tolerância
  de 1e-12.

## Pendências e riscos

- **Revisão dos textos com 2 ou 3 pessoas leigas:** não feita. É o item do plano que nenhum teste
  substitui. As frases a testar primeiro são as dos passos (b) e (c) do nível 3 ("palavras
  ignoradas por serem comuns", "palavras reduzidas ao radical") e o selo de raridade.
- **Legibilidade do destaque no projetor:** as quatro faixas de cor foram escolhidas no papel.
  Se não se distinguirem na parede, a saída é reduzir para três faixas — é um número no
  `config.yaml` e uma classe no CSS.
- **Arredondamento visível:** os produtos da tabela estão arredondados para 3 casas e a soma é a
  exata, então somar à mão as linhas pode dar 0,001 de diferença. A tela avisa. Se isso virar
  pergunta recorrente na feira, vale repensar (D-054 registra a alternativa e por que não foi
  escolhida).
- **Limiar de raridade:** calibrado para o acervo de 8.002 filmes. No acervo de brinquedo nenhum
  termo o alcança, então todas as palavras aparecem como "comum" nos testes — esperado, mas
  significa que o selo "palavra rara" só foi exercitado com valor de IDF passado à mão.

## Teach-back (explicação do Rafael, com as próprias palavras)
-
