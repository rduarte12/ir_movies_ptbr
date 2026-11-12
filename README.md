# FilmUSP — buscador de filmes em português que mostra como pensa

Projeto de demonstração para a feira de extensão do ICMC-USP. A pessoa descreve um filme do seu
jeito ("um tubarão assustador na praia", "robô que se apaixona") e o FilmUSP mostra **quais
filmes combinam mais** com a frase e, principalmente, **por que**: quais palavras casaram, quanto
cada uma pesou e como essas palavras viram um número.

**Autores:** Rafael Duarte, João Pedro Caetano e Lucas Waldrighi.

[![Abrir no Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/rduarte12/ir_movies_ptbr/blob/main/notebooks/02_search_app.ipynb)
· Apresentação: <https://rmduarte.com.br/feira/filmusp/>

> Este produto usa a API da TMDB mas não é endossado nem certificado pela TMDB.

## Como rodar no Google Colab (recomendado)

1. Clique em **Abrir no Colab**, acima. Abre o notebook `notebooks/02_search_app.ipynb`.
2. No menu, **Ambiente de execução → Executar tudo**. Não precisa de GPU, login nem chave de API.
3. Espere de 3 a 5 minutos na primeira vez. O notebook baixa este repositório, instala as
   bibliotecas que faltam no Colab (`requirements-colab.txt`) e baixa o modelo de linguagem
   (cerca de 470 MB).
4. Na célula 4 aparece um link `https://….gradio.live`. Clique nele para abrir o app. O link
   funciona enquanto o notebook estiver aberto.

A célula 3 faz uma busca de teste e imprime os 5 primeiros filmes, para conferir que tudo
funciona antes de abrir a tela.

## Como funciona

A busca tem duas partes, e a tela explica a parte das palavras em detalhe.

1. **Sentido.** Um modelo de linguagem
   ([paraphrase-multilingual-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2),
   versão fixada no `config.yaml`) transforma cada sinopse num vetor de características com 384
   números. Esses vetores foram calculados uma única vez e estão em `data/`. A frase da pessoa
   vira outro vetor, e os 100 filmes de sentido mais próximo (cosseno) viram candidatos.
2. **Palavras.** Entre os candidatos, um índice TF-IDF compara as palavras da frase com as da
   sinopse (minúsculas, sem acento, sem palavras comuns, reduzidas à raiz). A nota de cada filme é
   o cosseno entre os vetores TF-IDF, com os pesos de raridade calculados no acervo inteiro.
3. **Combinação.** A ordem final junta as duas listas por *Reciprocal Rank Fusion* (RRF, k = 5).
   A nota mostrada na tela continua sendo a do TF-IDF, para a explicação fechar a conta.

Tudo é determinístico: a mesma frase, no mesmo acervo, dá sempre o mesmo resultado. Se o modelo
de linguagem não carregar, o FilmUSP continua funcionando só com o TF-IDF.

**Explicabilidade.** Para o filme selecionado, a tela mostra três níveis ao mesmo tempo:

1. onde as palavras da busca aparecem na sinopse (destacadas);
2. quanto cada palavra pesou na pontuação (barras);
3. o passo a passo, das palavras ao número (palavras ignoradas, raízes, pesos e a soma que dá a
   pontuação).

O desenho da tela está em [`docs/ui_spec.md`](docs/ui_spec.md) e os contratos entre as partes em
[`docs/architecture.md`](docs/architecture.md).

## Como rodar localmente (plano B)

Requisito: **Python 3.13** (`>=3.13,<3.14`) e o PyTorch para CPU, que não está nos arquivos de
requirements (instale pela página oficial do PyTorch, para o seu sistema).

**Windows (PowerShell):**

```powershell
git clone https://github.com/rduarte12/ir_movies_ptbr.git
cd ir_movies_ptbr
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-app.txt
```

**Linux ou macOS:**

```bash
git clone https://github.com/rduarte12/ir_movies_ptbr.git
cd ir_movies_ptbr
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-app.txt
```

Depois, abra `notebooks/02_search_app.ipynb` num Jupyter com o ambiente `.venv` como kernel e
execute todas as células. O Jupyter não está nos arquivos de requirements; instale à parte se
precisar (por exemplo, `python -m pip install jupyterlab`).

**Uso sem internet (feira):** na primeira execução, com internet, o projeto baixa a lista de
palavras comuns do NLTK e o modelo de linguagem; os dois ficam em cache na máquina. Depois disso,
defina `HF_HUB_OFFLINE=1` para rodar sem internet. Os pôsteres vêm do servidor de imagens da TMDB;
sem internet eles não aparecem, mas a busca continua funcionando.

**Variável `IR_MOVIES_NO_LAUNCH`:** quando vale exatamente `1`, o notebook monta a interface mas
não abre o servidor. É o que os testes automáticos usam. No uso normal, deixe sem definir.

## Versões e dependências

| Arquivo | Para que serve |
|---|---|
| `requirements-colab.txt` | Colab: só o que o ambiente do Colab não traz ou traz em versão incompatível (gradio, Unidecode, sentence-transformers, transformers). numpy, pandas, scikit-learn, nltk, pyarrow e torch vêm do próprio Colab. |
| `requirements-app.txt` | Plano B local (notebook 02), com todas as versões fixadas (`==`). |
| `requirements-collect.txt` | Notebook 01 (coleta na TMDB), só para recoletar os dados. |
| `requirements-dev.txt` | Desenvolvimento: os dois anteriores mais pytest, ruff, jupytext, nbstripout e qrcode. |

Python local: `>=3.13,<3.14`. No Colab, vale o Python do próprio Colab; o código também roda no
Python 3.12. O PyTorch não é fixado pelo projeto (os vetores foram gerados com a versão
registrada em `data/embeddings_*.json`).

## Dados

- **Origem:** [TMDB](https://www.themoviedb.org/) (The Movie Database), pela API oficial, com
  `language=pt-BR`.
- **Seleção:** os filmes mais populares do export diário de IDs da TMDB (exceto conteúdo adulto)
  são consultados; ficam os que têm sinopse em português com pelo menos 5 palavras e pelo menos
  2 votos.
- **Acervo versionado** em `data/`: `movies_ptbr_20261106.parquet` e `snapshot_meta.json`
  (`snapshot_id` `20261106`), com **8.002 filmes**. O `snapshot_meta.json` registra filtros,
  contagens e rejeições por motivo.
- **Vetores de características** em `data/embeddings_*.npy` (8.002 × 384, float32) e
  `data/embeddings_*.json` (modelo, revisão, versões das bibliotecas). Para gerar de novo:
  `python scripts/build_embeddings.py`.
- **Texto indexado:** título + tagline + sinopse + gêneros (o mesmo texto nas duas partes da
  busca).
- **Pôsteres:** não são guardados no repositório; a interface usa as URLs do servidor de imagens
  da TMDB.
- **Recoletar (opcional, exige conta na TMDB):** instale `requirements-collect.txt`, copie
  `.env.example` para `.env`, preencha `TMDB_READ_ACCESS_TOKEN` e execute
  `notebooks/01_collect_tmdb.ipynb`. O `.env` nunca é versionado. Uma nova coleta gera um novo
  `snapshot_id` e exige gerar os vetores de novo.

## Apresentação

A apresentação interativa do projeto está publicada em <https://rmduarte.com.br/feira/filmusp/>.
O código-fonte, os dados que ela usa e a versão em PDF ficam em [`site/`](site/README.md), com as
instruções para gerar de novo.

## Privacidade

**As buscas são registradas de forma anônima.** Cada busca e cada clique em um filme viram uma
linha em `logs/queries-AAAA-MM-DD.jsonl` com: horário (UTC), um identificador aleatório por visita
ao app (sem relação com a pessoa), o texto da busca, quantidade de resultados, os ids dos
primeiros filmes e o tempo da busca. **Nenhum dado pessoal é guardado**: nem endereço IP, nem
identificação do navegador, nem nome. A pasta `logs/` não vai para o Git. Os campos completos
estão em [`docs/architecture.md`](docs/architecture.md) (seção 5).

## Testes e qualidade

Com o ambiente de desenvolvimento (`python -m pip install -r requirements-dev.txt`):

```
python -m pytest                            # testes automáticos
python -m ruff check .                      # lint
python -m ruff format .                     # formatação
python -m jupytext --sync notebooks/*.py    # sincroniza .py <-> .ipynb
```

## Estrutura do repositório

```
config.yaml              parâmetros (nada de números mágicos no código)
data/                    acervo e vetores de características, versionados
docs/                    escopo, arquitetura, interface, decisões, plano e diários
notebooks/               01 (coleta) e 02 (app), em par .py (jupytext) e .ipynb
scripts/                 vetores, acervo mínimo de testes, latência e apresentação
site/                    apresentação interativa (fonte, dados, HTML final e PDF)
src/ir_movies/           a lógica: coleta, pré-processamento, índices, busca, explicação, interface
tests/                   testes e fixtures
```

Documentação de projeto: [`docs/project_scope.md`](docs/project_scope.md) (escopo),
[`docs/architecture.md`](docs/architecture.md) (contratos), [`docs/ui_spec.md`](docs/ui_spec.md)
(interface), [`docs/decisions.md`](docs/decisions.md) (decisões) e
[`docs/execution_plan.md`](docs/execution_plan.md) (plano por sprints).

## Licença

MIT. Veja o arquivo [`LICENSE`](LICENSE).

## Atribuição

Os dados de filmes e os pôsteres vêm da TMDB.

Este produto usa a API da TMDB mas não é endossado nem certificado pela TMDB.
