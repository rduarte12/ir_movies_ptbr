# Decisões da Sprint 8 (entrega e verificação) — faixa D-070 a D-089

> Todas com status `proposta` até o Rafael confirmar. Quando confirmadas, as entradas devem ser
> transcritas para `docs/decisions.md`, que é o registro oficial. Formato igual ao de `decisions.md`.
> Campo de origem: R = autor do projeto; C = proposta técnica.

---

### D-070 · 2026-11-06 · Critério determinístico de seleção do acervo mínimo de testes
- **Contexto:** os testes de fumaça do notebook 02 e da interface precisam de um acervo pequeno que
  carregue em segundos, mas que exercite os estados que a interface trata (`ui_spec.md` secao 2):
  filme sem pôster, sem tagline, sem duração, sem direção. Um sorteio com semente não garante que
  esses casos entrem; um corte "os N mais populares" não garante nenhum deles (os dois filmes sem
  pôster do snapshot real não estão entre os 30 mais populares).
- **Decisão:** o acervo mínimo tem **30 filmes** (teto absoluto: 50) e é montado por regras, sem
  aleatoriedade. Ordem canônica de desempate: `(-popularity, id)`. Regras, em ordem de prioridade:
  1. todos os filmes sem pôster (`poster_path` nulo), até 3 (o snapshot real tem 2);
  2. os 3 mais populares sem tagline e com pôster;
  3. o mais popular com duração 0 (o snapshot usa 0 para duração desconhecida);
  4. o mais popular sem direção (`director` vazio);
  5. os 2 melhores resultados TF-IDF, calculados com o índice e o pré-processamento reais sobre o
     snapshot completo, para cada consulta de exemplo de `ui_spec.md` (secao 1.2): assim as
     consultas de exemplo que aparecem na tela devolvem resultado no acervo mínimo;
  6. os mais populares ainda não escolhidos, até completar 30.
- **Motivo:** cada regra tem um motivo verificável por teste (`tests/test_mini_snapshot.py`); a
  seleção é reproduzível por qualquer pessoa a partir do snapshot real.
- **Alternativa descartada:** amostra aleatória com semente fixa. Reprodutível, mas depende da
  versão do pandas/numpy para ser a mesma amostra, e não garante os estados de borda.
- **Limitação:** os limites (30, 3, 3, 1, 1, 2) são constantes no topo do script, e não chaves do
  `config.yaml`, porque o script gera uma fixture de teste, não faz parte do pipeline do produto.
  Se o Rafael preferir tudo em `config.yaml`, é uma mudança mecânica.
- **Origem:** C · **Status:** proposta

### D-071 · 2026-11-06 · Formato, determinismo e isolamento do acervo mínimo
- **Decisão:**
  - Mesmo formato do snapshot real: `movies_ptbr_<snapshot_id>.parquet` + `snapshot_meta.json`,
    em `tests/fixtures/mini_snapshot/`. O `snapshot_id` é **herdado** do snapshot de origem
    (resolvido por `data/snapshot_meta.json`, nunca embutido no script), para que o carregador do
    serviço, que resolve o parquet pelo `snapshot_id` (D-090), funcione igual nos dois diretórios.
  - O `snapshot_meta.json` do mini-acervo copia o da origem e ajusta o que deixou de ser verdade:
    `accepted`, `candidates_tested`, `rejections_by_reason`, `overview_word_count`,
    `file_size_bytes`; acrescenta o bloco `derived_from` (identifica a origem e o script).
    `created_utc` é herdado da origem: o script não lê o relógio.
  - Determinismo: sem aleatoriedade, sem relógio; JSON com `indent=2`, `ensure_ascii=False`, fim
    de linha `\n`. Gerar duas vezes produz bytes idênticos (teste), e a fixture versionada é conferida contra a gerada na hora (teste; o parquet byte a byte, o JSON pelo conteúdo, porque o controle de versão pode converter fim de linha): se alguém mudar o script ou a origem sem regerar a
    fixture, o teste falha.
  - Isolamento: o script só escreve na pasta de destino (padrão `tests/fixtures/mini_snapshot/`,
    ou a dada em `--dest`) e só lê `data/`. Um teste prova que `data/` não muda.
  - A fixture passa em `validate_snapshot` (D-025) e é validada pelo próprio script antes de gravar.
- **Risco aceito:** a igualdade byte a byte do parquet depende das versões fixadas de pyarrow e
  pandas (D-021). Se as versões mudarem, o teste de igualdade com a fixture versionada pode exigir
  regerar o arquivo.
- **Origem:** C · **Status:** proposta

### D-072 · 2026-11-06 · Como o notebook 02 é executado no teste de fumaça
- **Contexto:** o teste deve provar que "Run all" não quebra e que nenhum servidor abre. Um
  executor de notebook (`nbclient`, `nbconvert`, `papermill`) exigiria dependência nova em
  `requirements-dev.txt`, e as versões estão fixadas (D-021).
- **Decisão:** usar só o `jupytext` (já em `requirements-dev.txt`):
  1. copiar para uma pasta temporária um mini-projeto: `src/` (sem `__pycache__`),
     `config.yaml`, `notebooks/02_search_app.py` e o mini-acervo em `data/`. Como
     `PROJECT_ROOT` é derivado da localização do pacote, o notebook enxerga o mini-acervo como
     se fosse o `data/` do projeto e grava logs na pasta temporária, nunca no `logs/` real;
  2. rodar um subprocesso Python novo (`PYTHONPATH` apontando para a cópia, `IR_MOVIES_NO_LAUNCH=1`,
     diretório de trabalho `notebooks/`, como no Jupyter);
  3. o subprocesso lê o `.py` com `jupytext.read` e executa as células de código, em ordem, num
     único espaço de nomes (equivale a "Run all"). Linhas que começam com `%` ou `!` (magics do
     IPython, p. ex. `%pip install`) são ignoradas, e células em que **todas** as linhas são
     assim ficam vazias: a instalação de dependências é passo do Colab, não do teste;
  4. antes de executar, o subprocesso troca `gradio.Blocks.launch` por uma função que levanta
     erro: se alguma célula tentar abrir servidor, o teste falha. Esta é a prova de "nenhum
     servidor aberto" (e não a ausência de erro).
  - O teste afirma: código de saída 0, que ao menos uma célula de código foi executada
    (`CELLS_EXECUTED >= 1`; não compara com o total de células), que ao menos um `gradio.Blocks`
    foi criado, e que `launch` nunca foi chamado. Tempo limite do subprocesso: 180 s.
  - O teste executa o `.py`, e o README manda abrir o `.ipynb`; a equivalência dos dois é
    garantida por teste de sincronia à parte (D-077).
- **Alternativa descartada:** `nbclient`/`nbconvert`: dependência nova. Se o Rafael autorizar, o
  teste pode migrar para o executor padrão sem mudar o que ele afirma.
- **Limitação:** não é um kernel Jupyter de verdade; magics e comandos de shell são ignorados.
  O ensaio real no Colab (roteiro em `docs/rehearsal_checklist.md`) continua necessário.
- **Origem:** C · **Status:** proposta

### D-073 · 2026-11-06 · O teste de fumaça nasce com `skip` e é ativado na integração
- **Contexto:** a interface (`ui/app.py`) e o notebook 02 são entregues por outra frente, em
  paralelo (D-090). Na data desta decisão, `notebooks/02_search_app.py` não tem células de código.
- **Decisão:** o teste é escrito completo e fica com `@pytest.mark.skip(reason=...)`, com motivo
  explícito: depende da entrega da interface e do notebook 02, e é ativado na integração. Ativar
  é remover a linha do decorador. Não usar `xfail` (ocultaria uma falha real depois da
  integração) nem `try/except ImportError` silencioso (o teste passaria sem testar nada).
- **Origem:** C · **Status:** proposta

### D-074 · 2026-11-06 · Estrutura do README
- **Decisão:** o `README.md` é a cara pública do projeto e o roteiro de reprodução do zero. Ordem:
  1. o que é (e o que não é: sem BM25, embeddings ou modelos de linguagem na v1);
  2. como usar no Colab (clona, instala `requirements-app.txt`, abre o notebook 02);
  3. como rodar localmente (plano B): venv, instalação, Jupyter;
  4. versões e para que serve cada arquivo de requirements;
  5. dados: origem (TMDB), esquema resumido, como o snapshot foi gerado, como recoletar;
  6. privacidade: log de consultas anônimo;
  7. testes e estrutura do repositório;
  8. licença;
  9. atribuição TMDB (frase exata, ao final e também referenciada na seção de dados).
  Pontos de atenção, escritos no README de forma explícita: o Jupyter não está fixado em nenhum
  dos três arquivos de requirements (o README manda instalá-lo à parte, sem versão fixada); a
  primeira execução do pré-processamento baixa as *stopwords* do NLTK (exige internet uma vez); o
  endereço do repositório nos comandos é uma premissa não verificada.
  O README descreve o comportamento **documentado** (`ui_spec.md`, `architecture.md`); onde algo
  ainda não foi verificado de ponta a ponta (execução no Colab, interface), diz isso em um
  bloco "Estado de verificação", que deve ser reduzido pelo autor após o ensaio.
- **Texto obrigatório (testado em `tests/test_readme.py`):** a frase "Este produto usa a API da
  TMDB mas não é endossado nem certificado pela TMDB" e o aviso "As buscas são registradas de
  forma anônima".
- **Origem:** C · **Status:** proposta

### D-075 · 2026-11-06 · Roteiro de ensaio: formato e conteúdo
- **Decisão:** `docs/rehearsal_checklist.md` é um roteiro operacional com caixas de seleção e
  tabelas de anotação, em cinco partes: (A) preparação; (B) ensaio de 2 h contínuas no Colab,
  com medições a cada 15 min e registro de desconexões; (C) teste do plano B local; (D) teste de
  textos com 2 ou 3 pessoas leigas, com roteiro de tarefas e critérios de aprovação; (E) o que
  fazer se o Colab cair durante a feira. Cada passo é uma ação com resultado observável.
  Critérios de aprovação numéricos vêm de `project_scope.md` secao 5 (≤ 5 min para "Run all",
  ≤ 200 ms por busca, 2 h sem queda). O documento é ferramenta de trabalho: o Rafael preenche as
  tabelas e leva as conclusões para o diário.
- **Origem:** C · **Status:** proposta

### D-076 · 2026-11-06 · Itens da Sprint 8 que dependem de ação humana
- **Decisão:** na Sprint 8, só ficam marcados em `execution_plan.md` os itens verificáveis por
  comando nesta entrega. Ficam **desmarcados**: ensaio de 2 h no Colab, teste do plano B local
  (exigem o notebook 02 pronto e a máquina do autor), revisão final de `.gitignore`/segredos/`docs/`
  (depende da integração das três frentes) e a tag `v1.0` (publicação é do Rafael; criar tag
  está fora do que se faz neste fluxo). O item do README só é marcado com a ressalva de que o
  critério "reproduzível do zero" depende de um ensaio de instalação feito pelo autor.
- **Origem:** C · **Status:** proposta

### D-077 · 2026-11-06 · Teste de sincronia entre o `.py` e o `.ipynb` dos notebooks
- **Contexto:** o teste de fumaça (D-072) executa `notebooks/02_search_app.py`, mas o README manda
  abrir o `.ipynb` no Colab e no Jupyter. Sem verificação de sincronia, o teste provaria um
  arquivo que o usuário não executa.
- **Decisão:** `tests/test_notebook_sync.py` lê cada par com `jupytext` e compara, célula a
  célula, o tipo e o texto-fonte (sem saídas, metadados nem contadores de execução). Se o `.py`
  e o `.ipynb` divergirem, o teste falha e indica `python -m jupytext --sync notebooks/*.py`.
  Vale para todos os `notebooks/*.py`.
- **Alternativa descartada:** executar também o `.ipynb` no teste de fumaça. Exigiria um executor
  de notebook (dependência nova, D-072) para provar o mesmo que a sincronia já garante.
- **Consequência:** na integração, quem alterar o notebook 02 deve rodar o `--sync`; do contrário
  este teste falha.
- **Origem:** C · **Status:** proposta
