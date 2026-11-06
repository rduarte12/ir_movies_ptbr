# Buscador de filmes em português (PT-BR)

Buscador didático de filmes, feito para a feira de extensão do ICMC-USP. A pessoa descreve um
filme do seu jeito ("um tubarão assustador na praia", "robô que se apaixona") e o programa mostra
**quais filmes combinam mais** com a frase e, principalmente, **por que**: quais palavras casaram,
quanto cada uma pesou e como essas palavras viram um número.

> Este produto usa a API da TMDB mas não é endossado nem certificado pela TMDB.

## O que é

- **Modelo:** TF-IDF com similaridade do cosseno. É determinístico: a mesma frase, no mesmo
  acervo, dá sempre o mesmo resultado.
- **Acervo:** filmes com sinopse em português, coletados da TMDB (veja [Dados](#dados)).
- **Explicabilidade:** a tela mostra, ao mesmo tempo e para o filme selecionado, três níveis:
  1. onde as palavras da busca aparecem na sinopse (destacadas);
  2. quanto cada palavra pesou na pontuação (barras);
  3. o passo a passo, das palavras ao número (palavras ignoradas, radicais, pesos e a soma que dá
     a pontuação).
- **Interface:** Gradio, em um notebook (Colab ou Jupyter local). Grade de pôsteres, detalhes do
  filme e a seção de explicabilidade. O desenho está em [`docs/ui_spec.md`](docs/ui_spec.md).
- **Fora desta versão:** BM25, embeddings, busca híbrida, modelos de linguagem, login. Há apenas
  o ponto de extensão para reescrever a consulta (`Rewriter`), com a implementação identidade
  (a consulta passa como veio).

### Estado de verificação

Esta seção descreve o que **ainda não foi verificado de ponta a ponta**. O autor deve apagá-la ou
reduzi-la depois de fazer o ensaio descrito em
[`docs/rehearsal_checklist.md`](docs/rehearsal_checklist.md).

- Os testes automáticos (`python -m pytest`) cobrem coleta, pré-processamento, índice TF-IDF,
  contrato do serviço de busca e o acervo mínimo de testes.
- **Não verificado:** execução do notebook 02 no Colab, ensaio de 2 horas contínuas, execução
  local pelo plano B e teste dos textos da tela com pessoas leigas.
- O comportamento da interface descrito aqui segue `docs/ui_spec.md` e `docs/architecture.md`.

## Como rodar no Colab

O notebook do app é o `notebooks/02_search_app.ipynb`. Ele não usa a API da TMDB; só baixa os
pôsteres do CDN da TMDB.

1. Abra o notebook no Colab, pelo GitHub:
   `https://colab.research.google.com/github/rduarte12/ir_movies_ptbr/blob/main/notebooks/02_search_app.ipynb`
2. Em **Ambiente de execução > Executar tudo**. Conforme o desenho em
   [`docs/architecture.md`](docs/architecture.md) (seção 7), o notebook clona o repositório,
   instala `requirements-app.txt` (veja [Versões](#versões-e-dependências)), carrega o acervo e
   abre a interface.
3. Meta de tempo, de um ambiente novo do Colab até a tela pronta: até 5 minutos, sem passos
   manuais (meta de `docs/project_scope.md`; **ainda não medida**).
4. O log de consultas fica no disco do Colab, que é apagado quando o ambiente é encerrado. Baixe o
   arquivo de `logs/` antes de encerrar (veja [Privacidade](#privacidade)).

Se o Colab cair durante uma demonstração, use o plano B local e o roteiro de contingência em
[`docs/rehearsal_checklist.md`](docs/rehearsal_checklist.md).

## Como rodar localmente (plano B)

Requisito: **Python 3.13** (`>=3.13,<3.14`, a mesma versão do Colab). Os exemplos usam um
ambiente virtual (`venv`), que já vem com o Python.

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

Depois, abra o notebook `notebooks/02_search_app.ipynb` em um Jupyter (Notebook, JupyterLab ou
o editor que você usar) com o ambiente `.venv` como kernel, e execute todas as células.

Observações:

- **Jupyter não está em nenhum dos arquivos de requirements** do projeto. Instale à parte
  (por exemplo, `python -m pip install jupyterlab`) se ainda não o tiver. A versão não é fixada
  pelo projeto.
- Na primeira execução, o pré-processamento baixa a lista de palavras comuns (*stopwords*) do
  NLTK. Isso exige internet **uma vez**; depois fica em cache na máquina. Para o plano B em um
  local sem internet, faça uma execução prévia com internet.
- Os pôsteres vêm do CDN da TMDB. Sem internet, os pôsteres não aparecem (a busca continua
  funcionando, porque o acervo está no repositório).

### Variável `IR_MOVIES_NO_LAUNCH`

Quando vale exatamente `1`, o notebook monta a interface mas **não** abre o servidor. É o que
permite testar o notebook de forma automática. No uso normal, deixe a variável sem definir.

## Versões e dependências

Todas as bibliotecas têm versão exata fixada (`==`). Há três arquivos:

| Arquivo | Para que serve | Quem instala |
|---|---|---|
| `requirements-app.txt` | Notebook 02 (busca e interface): scikit-learn, numpy, nltk, Unidecode, pandas, pyarrow, PyYAML, python-dotenv, gradio | Colab e plano B local |
| `requirements-collect.txt` | Notebook 01 (coleta na TMDB): requests, tenacity, pandas, pyarrow, PyYAML, python-dotenv | Máquina local, só para recoletar os dados |
| `requirements-dev.txt` | Desenvolvimento: inclui os dois acima mais pytest, ruff, jupytext e nbstripout | Quem for alterar o código |

Python: `>=3.13,<3.14`.

## Dados

- **Origem:** [TMDB](https://www.themoviedb.org/) (The Movie Database), pela API oficial, com
  `language=pt-BR`.
- **Seleção:** os 20 mil filmes mais populares do export diário de IDs da TMDB (exceto conteúdo
  adulto) são consultados; ficam os que têm sinopse em português com pelo menos 5 palavras e pelo
  menos 2 votos.
- **Snapshot versionado** em `data/`: `movies_ptbr_20261106.parquet` e `snapshot_meta.json`
  (`snapshot_id` `20261106`). Tem **8.002 filmes** e é o que o notebook 02 lê; a lista de colunas
  está em [`docs/architecture.md`](docs/architecture.md) (seção 4). O `snapshot_meta.json`
  registra filtros, contagens e rejeições por motivo.
- **Texto indexado:** título + tagline + sinopse + gêneros.
- **Pôsteres:** não são baixados nem guardados no repositório; a interface usa as URLs do CDN da
  TMDB.
- **Recoletar (opcional, exige conta na TMDB):** instale `requirements-collect.txt`, copie
  `.env.example` para `.env` e preencha `TMDB_READ_ACCESS_TOKEN` com o seu token de leitura,
  depois execute `notebooks/01_collect_tmdb.ipynb`. O arquivo `.env` nunca é versionado. Uma nova
  coleta gera um novo `snapshot_id`.

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
python -m pytest              # testes automáticos (sem rede, depois do primeiro download das stopwords)
python -m ruff check .        # lint
python -m ruff format .        # formatação
python -m jupytext --sync notebooks/*.py   # sincroniza .py <-> .ipynb
```

Para gerar de novo o acervo mínimo usado nos testes (30 filmes, derivado do snapshot real):

```
python scripts/make_mini_snapshot.py
```

## Estrutura do repositório

```
config.yaml              parâmetros (nada de números mágicos no código)
data/                    snapshot versionado (parquet + meta)
docs/                    escopo, arquitetura, interface, decisões, plano e diários
notebooks/               01 (coleta) e 02 (app), em par .py (jupytext) e .ipynb
scripts/                 utilitários (acervo mínimo de testes)
src/ir_movies/           a lógica: coleta, pré-processamento, índice, busca, explicação, interface
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
