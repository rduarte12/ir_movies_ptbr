# Especificação da interface

> Gradio, tela de notebook/projetor, claro e legível a distância. Textos em PT-BR e em linguagem simples (termo técnico entre parênteses). Nome do app: Q-005.

## 1. Layout (de cima para baixo)

1. **Cabeçalho:** nome do app + frase: "Descreva um filme do seu jeito e veja como o buscador pensa."
2. **Busca:** caixa de texto (máx. 300 caracteres), botão "Buscar", exemplos clicáveis (ex.: "um tubarão assustador na praia", "robô que se apaixona").
3. **Resultados:** grade de pôsteres (5 colunas, `top_k` = 20). Legenda: `Título (ano) · pontuação`. Sem pôster → imagem placeholder.
4. **Detalhes do filme selecionado** (por padrão, o 1º resultado): pôster, título, título original, ano, duração, gêneros, nota TMDB, direção, elenco, sinopse.
5. **Explicabilidade** (sempre visível, os 3 níveis ao mesmo tempo, para o filme selecionado):
   - **1 · Onde suas palavras aparecem:** a sinopse com as palavras que casaram destacadas; cor mais forte = contribuiu mais.
   - **2 · Quanto cada palavra pesou:** barras horizontais por palavra da pergunta (contribuição à pontuação). Selo "palavra rara"/"palavra comum" conforme o IDF.
   - **3 · Das palavras ao número (passo a passo):**
     a) sua pergunta; b) palavras ignoradas por serem comuns ("de", "o", "qual"…); c) palavras reduzidas ao radical ("assustador" → "assust"); d) palavras que **não existem** no acervo; e) tabela: radical · peso na pergunta · peso no filme · produto; f) soma dos produtos = pontuação (cosseno).
6. **Rodapé:** atribuição TMDB ("Este produto usa a API da TMDB mas não é endossado nem certificado pela TMDB"), aviso "As buscas são registradas de forma anônima", versão do app e `snapshot_id`.

## 2. Estados e mensagens

| Situação | Mensagem (proposta) |
|---|---|
| Consulta vazia | "Escreva algo sobre o filme que você procura." |
| Só palavras ignoradas | "Todas as suas palavras são comuns demais para ajudar a busca. Tente incluir assuntos, objetos ou lugares." |
| Nenhuma palavra no acervo | "Nenhuma das suas palavras aparece nas sinopses. Tente outras palavras ou sinônimos." (momento didático) |
| Alguns termos fora do acervo | Listados no nível 3(d), sem bloquear o resultado |
| Sem pôster | Placeholder + título |
| Erro inesperado | "Algo deu errado. Tente de novo." (detalhe técnico só no log do servidor) |

## 3. Regras de conteúdo

- Mostrar sempre a pontuação com 3 casas decimais e a mesma convenção em todos os níveis.
- Os números do nível 3 devem bater exatamente com a pontuação da legenda (invariante 1 de `architecture.md`).
- Sem jargão sem explicação: "IDF" aparece como "raridade da palavra no acervo".
- Contraste alto e fonte grande para projeção; nada depende só de cor (barras têm rótulo numérico).

## 4. Fora desta versão

Toggle de modelos, campo de reescrita por LLM, filtros por gênero/ano, login.
