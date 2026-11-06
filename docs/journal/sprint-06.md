# Sprint 06 — Notebook 02: interface de busca

- **Data:** 2026-11-06 · **Branch:** `sprint-06-07/interface-explicabilidade` · **Tag:** `sprint-06`

## O que foi feito

- Seção `ui` do `config.yaml`: `app_name: "FilmUSP"` (resolve Q-005), colunas da grade,
  casas decimais da pontuação, faixas de destaque, limiar de raridade e exemplos clicáveis.
- `src/ir_movies/ui/` dividido em cinco módulos (D-057): `texts.py` (todo texto de tela, em
  PT-BR), `format.py` (números, legendas, URL de pôster), `styles.py` (CSS para projeção),
  `view.py` (conteúdo da tela como funções puras) e `app.py` (`build_app`).
- `build_app(service, cfg)` monta o layout de `ui_spec.md` secao 1: cabeçalho com nome e frase;
  caixa de busca de até 300 caracteres com botão e exemplos clicáveis; grade de pôsteres em
  5 colunas com legenda `Título (ano) · pontuação`; painel do filme selecionado (1º resultado
  por padrão); a seção Explicabilidade com os três níveis ao mesmo tempo; rodapé com atribuição
  da TMDB, aviso de log anônimo, versão do app e identificador do acervo.
- Os seis estados de `ui_spec.md` secao 2, com os textos copiados da especificação.
- Pôster ausente: um SVG local que o Gradio embute na página (D-056). Nenhuma imagem é baixada;
  os pôsteres existentes vêm do CDN da TMDB, no tamanho de `tmdb.poster_size`.
- `notebooks/02_search_app.py` (par jupytext): setup para Colab e local, serviço por injeção num
  ponto marcado, `build_app`, lançamento condicional por `IR_MOVIES_NO_LAUNCH` e a célula final
  opcional que compacta `logs/` para download no Colab.
- `tests/test_ui.py`: 104 testes, incluindo os que chamam os manipuladores de evento que
  `build_app` registrou no Gradio. Eles conferem que o clique num pôster chega ao `log_click` com
  o `rank` certo e que **cada valor devolvido pelo manipulador chega ao componente certo** — não
  só que a quantidade de valores confere. Cada bloco de conteúdo carrega uma classe que só ele
  tem, e a conferência exige que nenhum bloco contenha a marca de outro; um teste aplica trocas
  de ordem de propósito e exige que a conferência falhe.

A tela fala somente com `SearchServiceProtocol` e com a configuração (D-090): não conhece o
índice TF-IDF nem o arquivo de log. O clique é registrado por `service.log_click`, com `rank`
começando em 1 — o mesmo número que a legenda mostra.

## Decisões (IDs em `decisions.md`)

Registradas em `docs/decisions_trilha_C.md`, para incorporação na faixa D-050 a D-069.

- D-050 — Nome público do app: `FilmUSP` (resolve Q-005) (`aceita`)
- D-055 — Componentes do Gradio: `Blocks` + `Gallery` de 5 colunas + `HTML` (`proposta`)
- D-056 — Pôster ausente: arquivo SVG local embutido pelo Gradio (`proposta`)
- D-057 — `ui` dividido em textos, formatação, visão e montagem (`proposta`)
- D-058 — `session_id` por carregamento de página; só o clique explícito é registrado (`proposta`)
- D-059 — Estados da tela derivados do rastreio, e erro inesperado contido (`proposta`)
- D-060 — Parâmetros de apresentação e exemplos clicáveis no `config.yaml` (`proposta`)
- D-061 — Notebook 02: serviço por injeção e lançamento condicional (`proposta`)

## Premissas assumidas

- O serviço real (`SearchService`, Sprint 5) é construído como `SearchService(cfg)`. A assinatura
  não pôde ser conferida: o arquivo não existia nesta branch. A interface não depende dela — só o
  notebook, numa linha marcada.
- `launch(share=True, inline=False)`: `share` é o que dá um endereço acessível no Colab e
  `inline=False` abre a tela em aba própria, melhor para projetar. Não foi exercitado no Colab.
- O nome `FilmUSP` vai no `config.yaml` e em nenhum outro lugar do código. **Correção:** na
  primeira versão o `elem_id` do `Blocks` e duas regras do CSS traziam `filmusp-app`, o que
  contrariava D-050. Trocados por `ir-movies-app`, que é identificador técnico e não nome
  público.
- `tmdb.poster_size` segue `w342`, intocado: a seção não pertence a esta frente.

## Desvios do plano

- `requirements-app.txt` não mudou: `gradio==6.31.0` já estava fixado desde a Sprint 0 (D-021), e
  a interface não exigiu dependência nova.
- O CSS entra como um bloco de estilo na própria página, e não pelo parâmetro `css` do
  `gr.Blocks`: no Gradio 6 esse parâmetro só é lido dentro de `launch()`, que `build_app` nunca
  chama (D-055).
- **Assinatura de `build_app`:** `architecture.md` secao 3 prevê `build_app(service, snapshot)`;
  o entregue é `build_app(service, cfg)`, que é o que D-090 determina — os dados do filme vêm de
  `service.get_movie`, e o segundo argumento traz os parâmetros de apresentação. Registrado em
  D-057 e aberto como pedido de mudança no `architecture.md`, que não pertence a esta frente.

## Como verificar

```
python -m pytest -q
python -m ruff check .
python -m pytest tests/test_explain.py tests/test_ui.py -q
python -m jupytext --sync notebooks/02_search_app.py ; git status --porcelain
```

Montar a tela sem abrir servidor:

```
IR_MOVIES_NO_LAUNCH=1 python -c "import sys; sys.path.insert(0,'tests'); \
  from fakes import FakeSearchService; from ir_movies.ui.app import build_app; \
  from ir_movies.config import load_config; \
  print(type(build_app(FakeSearchService.from_toy(), load_config())).__name__)"
```

## Resultado das verificações

- `python -m pytest -q`: 254 testes, 0 falhas (121 herdados + 29 de `test_explain.py` +
  104 de `test_ui.py`).
- `python -m ruff check .`: All checks passed.
- `ruff format --check` nos arquivos desta frente: sem diferenças.
- `build_app` devolve `gradio.Blocks` com `is_running = False` e `local_url = None`; um teste
  substitui `Blocks.launch` por uma função que falha, para provar que `build_app` não a chama.
- Notebook executado localmente até a Parte 3, com serviço injetado e `IR_MOVIES_NO_LAUNCH=1`:
  monta a tela e não abre servidor.

## Pendências e riscos

- **Aparência real da tela:** não foi vista. Nenhum teste aqui renderiza HTML; eles conferem o
  conteúdo e os números. Contraste, tamanho de fonte, altura da grade e o comportamento do
  pôster ausente precisam de um olhar humano, de preferência no projetor da feira.
- **Colab:** o notebook não foi executado no Colab. Clone, instalação, `share=True` e o tempo de
  carga do snapshot são desconhecidos na prática.
- **Serviço real:** a interface foi construída contra `FakeSearchService`. O contrato é um
  protocolo e `tests/test_contract.py` roda as mesmas regras contra a implementação de
  referência, mas a primeira execução com o `SearchService` real ainda não aconteceu.
- **Legenda da grade:** a legenda do `gr.Gallery` é renderizada pelo próprio componente. Se
  aparecer pequena ou cortada no projetor, a alternativa é desenhar a grade em HTML — mudança de
  componente, não de conteúdo, e exige nova decisão.
- **Exemplos clicáveis:** os dois primeiros vêm de `ui_spec.md`; os outros dois foram escritos
  para o corpus de brinquedo e podem não ter bom resultado no acervo real. Conferir e trocar no
  `config.yaml` antes da feira.

## Teach-back (explicação do Rafael, com as próprias palavras)
-
