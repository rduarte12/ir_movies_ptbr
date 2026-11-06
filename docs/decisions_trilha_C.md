# Decisões — interface de busca e Explicabilidade (Sprints 6 e 7)

Faixa reservada a esta frente por D-090: **D-050 a D-069**.
Formato igual ao de `docs/decisions.md`. Status inicial `proposta`, até confirmação do autor.
Campo de origem: `**Origem:**` — R = autor do projeto; C = proposta técnica.

Este arquivo é incorporado a `docs/decisions.md` na integração das Sprints 5 a 8.

---

### D-050 · 2026-11-06 · Nome público do app: `FilmUSP` (resolve Q-005)
- **Contexto:** Q-005 (nome público do app) estava aberta desde a Sprint 0; `config.yaml`
  trazia `ui.app_name: "Buscador de Filmes"` marcado como provisório.
- **Decisão:** o nome público é **`FilmUSP`**. Gravado em `config.yaml` (`ui.app_name`) e lido
  pelo cabeçalho da tela; o código não repete o nome em lugar nenhum.
- **Consequência:** `ui_spec.md` secao 1.1 ("nome do app + frase") fica resolvido; o cabeçalho
  mostra `FilmUSP` e a frase "Descreva um filme do seu jeito e veja como o buscador pensa."
- **Origem:** R · **Status:** aceita

### D-051 · 2026-11-06 · Nível 1: intensidade do destaque linear sobre a maior contribuição
- **Contexto:** `ui_spec.md` secao 1.5 pede "cor mais forte = contribuiu mais", sem fixar a escala.
  Duas opções: escala **linear** (proporcional à contribuição) ou **por posto** (1º, 2º, 3º lugar).
- **Decisão:** `explain.highlight` devolve uma intensidade contínua em `[0, 1]`, igual a
  `contribuição / maior contribuição do filme`. A escala é **relativa ao filme exibido**, não ao
  acervo: a leitura que a tela sustenta é "nesta sinopse, esta palavra pesou mais que aquela".
- **Renderização:** a intensidade contínua é agrupada em `ui.highlight_levels` faixas de cor
  (4, por padrão) na hora de gerar o HTML. Faixas discretas porque, num projetor, variação
  contínua de cor não é distinguível; 4 faixas são.
- **Por que não por posto:** o posto esconde a diferença de tamanho. Com dois termos de
  contribuição 0,30 e 0,29, o destaque por posto sugere uma diferença que não existe.
- **Degenerado:** se todas as contribuições forem zero, toda palavra que casa recebe intensidade
  `0.0` — casou, mas não somou nada. Honesto e visível.
- **Origem:** C · **Status:** proposta

### D-052 · 2026-11-06 · Nível 2: barras horizontais com rótulo numérico obrigatório
- **Decisão:** uma barra por palavra da pergunta que casou com o filme, ordenada por contribuição
  decrescente (a ordem que `TfidfIndex.contributions` já devolve). A largura é
  `contribuição / maior contribuição`, em porcentagem; ao lado da barra, sempre, o valor numérico
  da contribuição com a mesma formatação da pontuação (D-054).
- **Motivo do rótulo:** `ui_spec.md` secao 3 exige que nada dependa só de cor. O rótulo também
  serve a quem olha de longe e não distingue comprimentos parecidos.
- **Rótulo da palavra:** a primeira forma de superfície (`TermContribution.surface_forms`), isto é
  a palavra como a pessoa escreveu (sem acento e em minúsculas, por causa do pré-processamento),
  e não o radical. O radical aparece no nível 3, onde é explicado.
- **Origem:** C · **Status:** proposta

### D-053 · 2026-11-06 · Limiar "palavra rara" × "palavra comum" em termos de IDF
- **Contexto:** `ui_spec.md` secao 1.5 pede um selo "palavra rara"/"palavra comum" por palavra,
  "conforme o IDF", sem fixar o corte. A interface não conhece o tamanho do acervo (o contrato
  D-090 não expõe isso), então o corte não pode ser calculado na hora.
- **Decisão:** parâmetro `ui.rare_idf_threshold` no `config.yaml`, valor inicial **3.3**.
  Palavra com `idf >= 3.3` recebe o selo "palavra rara"; abaixo disso, "palavra comum".
- **Derivação do 3.3:** com `smooth_idf: true` (D-015), o IDF do scikit-learn é
  `ln((1 + N) / (1 + df)) + 1`. Para "aparece em no máximo 10% do acervo" (`df <= 0.1 N`), com
  `N = 8002` filmes do snapshot atual, o corte é `ln(8003 / 801,2) + 1 = 3,30`. O número é,
  portanto, a tradução de uma regra que se explica em voz alta na feira: *rara = aparece em no
  máximo um filme em dez*.
- **Consequência conhecida:** o corte depende do tamanho do acervo. Uma recoleta que mude `N`
  muda o significado do 3,3; por isso o valor está em `config.yaml`, com a conta registrada aqui,
  e não embutido no código. No corpus de brinquedo de 5 filmes nenhum termo alcança 3,3 (o IDF
  máximo lá é `ln(6/2) + 1 = 2,10`), o que é esperado: o limiar é calibrado para o acervo real.
- **Alternativa descartada:** classificar relativamente, comparando as palavras da própria
  pergunta entre si. Seria enganoso — numa pergunta com duas palavras raras, uma delas receberia
  o selo "comum" sem ser comum.
- **Jargão:** o selo nunca escreve "IDF". A tela diz "raridade da palavra no acervo"
  (`ui_spec.md` secao 3).
- **Origem:** C · **Status:** proposta

### D-054 · 2026-11-06 · Pontuação com 3 casas decimais e vírgula; a soma exibida é a exata
- **Decisão:** toda pontuação e toda contribuição aparecem com `ui.score_decimals` casas
  decimais (3, conforme `ui_spec.md` secao 3) e **vírgula** como separador decimal, que é a
  convenção do português. Uma função só (`ui.format.format_score`) formata os números dos três
  níveis e da legenda da grade, para que a convenção não possa divergir entre eles.
- **Soma do nível 3:** o total exibido é a soma dos produtos em **precisão cheia**, arredondada na
  exibição — não a soma dos valores já arredondados. É o que mantém a identidade exigida por
  `ui_spec.md` secao 3: o total do nível 3 é, caractere a caractere, a pontuação da legenda.
- **Limitação assumida:** por isso, somar à mão os produtos arredondados da tabela pode dar
  0,001 de diferença em relação ao total. A tela avisa, em uma linha, que os valores estão
  arredondados para 3 casas. A alternativa (exibir o total como soma dos arredondados) quebraria
  a identidade com a legenda, que é a invariante que a Explicabilidade existe para mostrar.
- **Origem:** C · **Status:** proposta

### D-055 · 2026-11-06 · Componentes do Gradio: `Blocks` + `Gallery` de 5 colunas + `HTML`
- **Decisão:** `gr.Blocks` (não `gr.Interface`, que não permite este layout);
  `gr.Gallery(columns=5, allow_preview=False)` para a grade de pôsteres, com a legenda de cada
  item e o evento `.select` para a escolha do filme; `gr.HTML` para o painel de detalhes, os três
  níveis da Explicabilidade, as mensagens de estado e o rodapé.
- **Por que `gr.HTML` nos blocos didáticos:** barras com largura proporcional, destaque por faixa
  de cor e tabela com cabeçalho exigem controle de marcação que `gr.Markdown` não dá. O contraste
  e o tamanho de fonte pedidos para projeção ficam em um bloco de CSS só (`ui/styles.py`).
- **Por que `Gallery` e não 20 botões com imagem:** a grade é o único componente que já traz
  posição clicada (`gr.SelectData.index`), colunas configuráveis e número variável de itens sem
  recriar componentes. O número de resultados vem do serviço (`k=None` usa `search.top_k`), e a
  interface não precisa saber quantos são de antemão.
- **Versão:** `gradio==6.31.0`, já fixada em `requirements-app.txt` desde a Sprint 0 (D-021);
  esta decisão apenas confirma que o layout foi construído contra ela.
- **Origem:** C · **Status:** proposta

### D-056 · 2026-11-06 · Pôster ausente: arquivo SVG local embutido pelo Gradio
- **Contexto:** `poster_path` é `None` em parte do acervo (2 casos no snapshot atual) e
  `ui_spec.md` secao 2 pede "placeholder + título".
- **Decisão:** um arquivo SVG de texto em `src/ir_movies/ui/assets/no_poster.svg`, nas proporções
  de um pôster (2:3), com fundo escuro e a palavra "Sem pôster". O Gradio lê SVG local e o embute
  na página como `data:` URI, então o placeholder **não** depende de rede nem de pasta servida.
- **Por que não baixar nem gerar imagem:** o projeto não baixa pôsteres (usa o CDN da TMDB) e
  um SVG é texto — versionável, legível em revisão e sem binário no repositório.
- **Tamanho do pôster:** segue `tmdb.poster_size` (`w342`), seção que esta frente não possui e
  não alterou. A URL é `https://image.tmdb.org/t/p/{tamanho}{poster_path}`
  (`architecture.md` secao 4).
- **Origem:** C · **Status:** proposta

### D-057 · 2026-11-06 · `ui` dividido em textos, formatação, visão e montagem
- **Decisão:** `src/ir_movies/ui/` com cinco módulos de responsabilidade única:
  `texts.py` (todo texto de interface, em PT-BR), `format.py` (números, legendas, URL de pôster),
  `styles.py` (o CSS), `view.py` (funções que recebem serviço + configuração e devolvem o
  conteúdo da tela) e `app.py` (`build_app`: cria os componentes e liga os eventos, nada mais).
- **Motivo:** o conteúdo da tela — mensagens de estado, os três níveis, a legenda — é testável
  como função pura. Se ele morasse dentro dos manipuladores de evento do Gradio, só seria
  verificável abrindo o navegador, e a Explicabilidade é justamente a parte que não pode ser
  aceita "de olho".
- **`build_app` nunca chama `.launch()`** (convenção `IR_MOVIES_NO_LAUNCH` de D-090).
- **Origem:** C · **Status:** proposta

### D-058 · 2026-11-06 · `session_id` por carregamento de página; só o clique explícito é registrado
- **Decisão:** a interface gera um identificador aleatório (`uuid4`, hexadecimal) a cada
  carregamento de página, guardado em `gr.State`, e o passa ao serviço em `search` e `log_click`.
  Não há nada da pessoa nele: é um número sorteado, que separa uma visita da seguinte.
- **Decisão correlata:** o filme mostrado por padrão (o 1º resultado, `ui_spec.md` secao 1.4)
  **não** gera `log_click`. Só a escolha explícita de um pôster registra clique. Caso contrário
  todo resultado em 1º lugar apareceria como clicado, e o log de cliques não mediria nada.
- **Origem:** C · **Status:** proposta

### D-059 · 2026-11-06 · Estados da tela derivados do rastreio, e erro inesperado contido
- **Decisão:** os estados de `ui_spec.md` secao 2 são decididos nesta ordem, a partir do
  `SearchResult` (nunca de exceção, pela regra 1 de D-090):
  1. `trace.original_tokens` vazio → "consulta vazia" (cobre texto em branco e só pontuação);
  2. `trace.stems` vazio e `trace.stopped` não vazio → "só palavras comuns";
  3. sem resultados, havendo radicais → "nenhuma palavra no acervo";
  4. com resultados e `oov_terms` não vazio → sem mensagem; os termos aparecem no nível 3(d);
  5. `poster_path is None` → placeholder (D-056);
  6. qualquer exceção inesperada → a mensagem genérica, e o detalhe técnico vai para o log do
     servidor por `logging.exception`, nunca para a tela.
- **Textos:** copiados literalmente de `ui_spec.md` secao 2 para `ui/texts.py`. Os testes repetem
  o literal da especificação em vez de importar a constante: assim uma mudança silenciosa no
  texto falha o teste, em lugar de passar por comparar a constante consigo mesma.
- **Origem:** C · **Status:** proposta

### D-060 · 2026-11-06 · Parâmetros de apresentação e exemplos clicáveis no `config.yaml`
- **Decisão:** a seção `ui` do `config.yaml` passa a ter, além de `app_name`:
  `grid_columns` (5), `score_decimals` (3), `highlight_levels` (4), `rare_idf_threshold` (3.3),
  `max_examples` e `examples` (as perguntas clicáveis, com as duas de `ui_spec.md` secao 1.2).
- **Motivo:** nenhum número mágico no código, e quem conduz a feira pode trocar os exemplos sem
  abrir arquivo de código. O limite de 300 caracteres da caixa de texto **não** entra aqui: vem de
  `MAX_QUERY_CHARS`, do contrato, porque o serviço também o aplica e os dois têm de concordar.
- **Origem:** C · **Status:** proposta

### D-061 · 2026-11-06 · Notebook 02: serviço por injeção e lançamento condicional
- **Decisão:** o notebook 02 recebe o serviço de busca por injeção numa célula marcada, monta a
  tela com `build_app(service, cfg)` e só chama `.launch()` quando `IR_MOVIES_NO_LAUNCH != "1"`
  (D-090). A célula de setup funciona no Colab (clone do repositório e instalação de
  `requirements-app.txt`) e localmente (nada a instalar), decidindo por tentar importar
  `google.colab`.
- **Parâmetros de `launch`:** `share=True` (no Colab é o que dá um endereço acessível; localmente
  é inofensivo) e `inline=False`, para a tela abrir em aba própria — numa feira, projetar a aba
  cheia é melhor que a moldura dentro do notebook.
- **Célula final (Q-001):** quando `google.colab` existe, compacta `logs/` e oferece o download;
  fora do Colab, apenas informa onde os arquivos estão. Nada quebra em nenhum dos dois casos.
- **Origem:** C · **Status:** proposta
