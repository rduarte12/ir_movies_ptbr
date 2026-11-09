# Buscador de filmes em português (PT-BR)

Buscador didático de filmes, feito para a feira de extensão do ICMC-USP. A pessoa descreve um
filme do seu jeito ("um tubarão assustador na praia", "robô que se apaixona") e o programa mostra
**quais filmes combinam mais** com a frase e, principalmente, **por que**: quais palavras casaram,
quanto cada uma pesou e como essas palavras viram um número.

> Este produto usa a API da TMDB mas não é endossado nem certificado pela TMDB.

## O que é

- **Modelo:** TF-IDF com similaridade do cosseno. É determinístico: a mesma frase, no mesmo
  acervo, dá sempre o mesmo resultado.
- **Pré-filtro semântico (opcional):** quando `semantic.enabled: true` em `config.yaml`, a busca
  passa por um passo extra antes do TF-IDF — a consulta é codificada por
  `paraphrase-multilingual-MiniLM-L12-v2` e os 40 filmes mais próximos em significado são usados
  como candidatos. Os dois rankings são fundidos por RRF. A pontuação e a seção de explicabilidade
  continuam sendo calculadas pelo TF-IDF. Com `false` (padrão), o comportamento é idêntico à v1.
- **Acervo:** filmes com sinopse em português, coletados da TMDB (veja [Dados](#dados)).
- **Explicabilidade:** a tela mostra, ao mesmo tempo e para o filme selecionado, três níveis:
  1. onde as palavras da busca aparecem na sinopse (destacadas);
  2. quanto cada palavra pesou na pontuação (barras);
  3. o passo a passo, das palavras ao número (palavras ignoradas, radicais, pesos e a soma que dá
     a pontuação).
- **Interface:** Gradio, em um notebook (Colab ou Jupyter local). Grade de pôsteres, detalhes do
  filme e a seção de explicabilidade. O desenho está em [`docs/ui_spec.md`](docs/ui_spec.md).
- **Fora desta versão:** BM25, modelos de linguagem generativos, login. Há o ponto de extensão
  para reescrever a consulta (`Rewriter`), com a implementação identidade (a consulta passa como
  veio).

### Estado de verificação

- Testes automáticos (`python -m pytest`): 434 passando.
- Latência (mediana/p95 com semântica ativa, 50 consultas): 14,9 ms / 21,1 ms — dentro do critério de 200 ms.
- **Pendente:** ensaio de 2 h no Colab, teste com pessoas leigas, verificação do plano B local do zero.

## Como rodar no Colab

O notebook do app é o `notebooks/02_search_app.ipynb`. Ele não usa a API da TMDB; só baixa os
pôsteres do CDN da TMDB.

1. Abra o notebook no Colab, pelo GitHub:
   `https://colab.research.google.com/github/rduarte12/ir_movies_ptbr/blob/main/notebooks/02_search_app.ipynb`
2. Em **Ambiente de execução > Executar tudo**. O notebook clona o repositório, instala
   `requirements-app.txt` (veja [Versões](#versões-e-dependências)), carrega o acervo e abre a
   interface. `torch` já vem pré-instalado no Colab.
3. Se `semantic.enabled: true` em `config.yaml` (padrão atual), na primeira execução o modelo
   semântico é baixado do Hugging Face (~500 MB, Colab tem internet). Os vetores do acervo já
   estão em `data/` (no repositório). O modelo é carregado uma vez por sessão do Colab.
4. Meta de tempo, de um ambiente novo do Colab até a tela pronta: até 5 minutos, sem passos
   manuais (meta de `docs/project_scope.md`).
5. O log de consultas fica no disco do Colab, que é apagado quando o ambiente é encerrado. Baixe o
   arquivo de `logs/` antes de encerrar (veja [Privacidade](#privacidade)).

Se o Colab cair durante uma demonstração, use o plano B local e o roteiro de contingência em
[`docs/rehearsal_checklist.md`](docs/rehearsal_checklist.md).

## Como rodar localmente (plano B)

Requisitos: **Python 3.13** (`>=3.13,<3.14`, a mesma versão do Colab) e **PyTorch** (veja abaixo).
Os exemplos usam um ambiente virtual (`venv`), que já vem com o Python.

**Windows (PowerShell):**

```powershell
git clone https://github.com/rduarte12/ir_movies_ptbr.git
cd ir_movies_ptbr
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
# torch (CPU) — precisa ser instalado antes do requirements-app.txt
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-app.txt
```

**Linux ou macOS:**

```bash
git clone https://github.com/rduarte12/ir_movies_ptbr.git
cd ir_movies_ptbr
python3.13 -m venv .venv
source .venv/bin/activate
# torch (CPU) — precisa ser instalado antes do requirements-app.txt
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-app.txt
```

Depois, abra o notebook `notebooks/02_search_app.ipynb` em um Jupyter (Notebook, JupyterLab ou
o editor que você usar) com o ambiente `.venv` como kernel, e execute todas as células.

Observações:

- **Jupyter não está em nenhum dos arquivos de requirements** do projeto. Instale à parte
  (por exemplo, `python -m pip install jupyterlab`) se ainda não o tiver. A versão não é fixada
  pelo projeto.
- **torch (PyTorch)** não está no `requirements-app.txt` porque o Colab já vem com ele (com GPU).
  No plano B local, o comando acima instala a versão CPU, que é suficiente para inferência.
- Se `semantic.enabled: true`, o modelo semântico é carregado na primeira execução. Os pesos são
  baixados do Hugging Face (~500 MB) e ficam em cache em `~/.cache/huggingface/`. Nas execuções
  seguintes o carregamento é instantâneo. Para rodar **sem internet** após o primeiro download:
  ```
  HF_HUB_OFFLINE=1 jupyter lab
  ```
- Na primeira execução, o pré-processamento baixa as *stopwords* do NLTK (pequeno, ~1 KB). Depois
  fica em cache. Para o plano B offline, faça uma execução prévia com internet.
- Os pôsteres vêm do CDN da TMDB. Sem internet, os pôsteres não aparecem (a busca continua
  funcionando, pois o acervo está no repositório).

### Variável `IR_MOVIES_NO_LAUNCH`

Quando vale exatamente `1`, o notebook monta a interface mas **não** abre o servidor. É o que
permite testar o notebook de forma automática. No uso normal, deixe a variável sem definir.

## Versões e dependências

Todas as bibliotecas têm versão exata fixada (`==`). Há três arquivos:

| Arquivo | Para que serve | Quem instala |
|---|---|---|
| `requirements-app.txt` | Notebook 02 (busca e interface): scikit-learn, numpy, nltk, Unidecode, pandas, pyarrow, PyYAML, python-dotenv, gradio, sentence-transformers, transformers | Colab e plano B local |
| `requirements-collect.txt` | Notebook 01 (coleta na TMDB): requests, tenacity, pandas, pyarrow, PyYAML, python-dotenv | Máquina local, só para recoletar os dados |
| `requirements-dev.txt` | Desenvolvimento: inclui os dois acima mais pytest, ruff, jupytext e nbstripout | Quem for alterar o código |

Python: `>=3.13,<3.14`. **torch não está listado** porque o Colab já o inclui; no plano B local,
instale separado (veja [Como rodar localmente](#como-rodar-localmente-plano-b)).

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
- **Vetores semânticos** em `data/`: `embeddings_sentence_transformers_paraphrase_multilingual_minilm_l12_v2_20261106.npy`
  (8.002 × 384, float32) e o JSON de metadados com a mesma base de nome. Usados quando
  `semantic.enabled: true`. Gerados com `scripts/build_embeddings.py` a partir do snapshot acima.
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
data/                    snapshot versionado (parquet + meta + vetores semânticos)
docs/                    escopo, arquitetura, interface, decisões, plano e diários
notebooks/               01 (coleta) e 02 (app), em par .py (jupytext) e .ipynb
scripts/
  make_mini_snapshot.py  gera acervo mínimo para os testes (30 filmes)
  build_embeddings.py    gera vetores semânticos a partir do snapshot (exige torch)
  measure_latency.py     mede latência de busca (50 consultas, mediana e p95)
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
