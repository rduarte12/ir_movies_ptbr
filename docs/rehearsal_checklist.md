# Roteiro de ensaio e de contingência (Sprint 8)

> Para o autor do projeto executar. Cada passo tem um resultado observável: marque a caixa só quando
> viu o resultado. Anote tudo nas tabelas; as conclusões vão para `docs/journal/sprint-08.md`.
> Critérios de aprovação vêm de `docs/project_scope.md` (secao 5).
> Decisão de origem: D-075.

**Antes de começar:** o notebook 02 e a interface precisam estar integrados e `python -m pytest`
passando (sem `skip` no teste de fumaça do notebook). Sem isso, o ensaio não tem o que ensaiar.

Resumo dos critérios de aprovação:

| Critério | Meta |
|---|---|
| "Executar tudo" no Colab, sessão nova, sem passos manuais | até 5 min |
| Latência de uma busca (campo `latency_ms` do log) | até 200 ms (mediana e p95) |
| Estabilidade | 2 h contínuas sem queda da interface |
| Resultado igual no Colab e no local (determinismo) | mesmos ids no topo para a mesma frase |
| Textos da tela | pelo menos 2 de 3 pessoas leigas explicam o resultado com as próprias palavras |

---

## A. Preparação (véspera)

- [ ] Conta Google que será usada na feira, com o notebook aberto uma vez (confere o acesso ao
      repositório). Anote qual conta: ______
- [ ] Conferir o endereço do repositório nos comandos do `README.md` (`git clone ...`) e o link de
      abertura no Colab: abrir o link do README em uma janela anônima e ver o notebook carregar.
- [ ] No computador da feira: ambiente local pronto (seção C) **antes** do ensaio, não depois.
- [ ] Computador na tomada, proteção de tela e suspensão desativadas
      (Windows: Configurações > Sistema > Energia > Tela e suspensão: "Nunca" na tomada).
- [ ] Duas fontes de internet: a do local e o roteador do celular (teste que o celular conecta
      e abre `colab.research.google.com`).
- [ ] Zoom do navegador entre 110% e 125% e tela em resolução de projeção; confira que dá para ler
      a tela a 2 m de distância.
- [ ] Planilha ou papel para anotar (modelo nas seções B e D).

## B. Ensaio de 2 horas contínuas no Colab

**Objetivo:** medir o tempo de partida, a latência das buscas e se a interface sobrevive a 2 h
sem queda. Duração mínima: 2 h 00 min sem interrupção do ensaio.

### B1. Partida a frio

- [ ] Abrir o Colab em uma aba nova, **sessão nova** (Ambiente de execução > Desconectar e excluir
      ambiente de execução, e abrir o notebook de novo).
- [ ] Disparar um cronômetro e clicar em **Executar tudo**. Parar o cronômetro quando a interface
      aparecer pronta para uma busca.
- [ ] Tempo medido: ______ min ______ s. **Aprovado se <= 5 min** e sem nenhum passo manual
      (nenhum clique extra, nenhuma entrada de texto, nenhuma autorização).
- [ ] Anotar qualquer aviso ou erro que apareceu no meio (copiar o texto): ______

### B2. Rotina de 15 em 15 minutos

Mantenha a aba do Colab aberta e visível o tempo todo (aba em segundo plano pode ser suspensa pelo
navegador, e isso estraga a medição). A cada 15 minutos, **execute estas 6 buscas, nesta ordem**,
e preencha a linha da tabela:

1. `um tubarão assustador na praia`
2. `robô que se apaixona`
3. (vazia: clicar em "Buscar" sem digitar)
4. `de a o que`  (só palavras comuns: deve mostrar a mensagem de palavras comuns demais)
5. `zzqxwv blorptan`  (nenhuma palavra no acervo: deve mostrar a mensagem correspondente)
6. clicar em um exemplo pronto e depois em outro filme da grade (conferir que o painel de detalhes
   e a explicabilidade mudam)

| Hora | Minuto do ensaio | 6 buscas deram o resultado esperado? (S/N) | Resposta demorou perceptivelmente? (S/N) | Desconectou? (S/N) | Observação |
|---|---|---|---|---|---|
| | 0 | | | | |
| | 15 | | | | |
| | 30 | | | | |
| | 45 | | | | |
| | 60 | | | | |
| | 75 | | | | |
| | 90 | | | | |
| | 105 | | | | |
| | 120 | | | | |

"Resultado esperado" é o descrito em `docs/ui_spec.md` (secao 2): para a busca 1, deve aparecer
uma grade de filmes; para a 3, a mensagem "Escreva algo sobre o filme que você procura."; para a
4 e a 5, as mensagens da tabela da secao 2. Se a tela mostrar "Algo deu errado. Tente de novo.",
registre o minuto e o que você tinha acabado de fazer.

### B3. Registro de desconexões e de lentidão

Sempre que a interface parar de responder, o Colab mostrar "Reconectando" ou a página pedir
recarregar:

- [ ] Anotar a hora exata e o que a tela mostrava.
- [ ] Anotar o que foi preciso para voltar (nada / recarregar a página / Executar tudo de novo)
      e quanto tempo levou.

| Hora | O que aconteceu (texto da tela) | O que foi feito para voltar | Tempo até voltar |
|---|---|---|---|
| | | | |

Lentidão: se uma busca demorar mais que 2 segundos, anote a hora e o que mais estava rodando no
computador (outras abas, videochamada).

### B4. Baixar o log e medir a latência

O log fica no disco do Colab e some quando a sessão termina (Q-001). Ao fim do ensaio, **antes**
de fechar a aba:

- [ ] Painel de arquivos do Colab (ícone de pasta, à esquerda) > pasta `logs/` > o arquivo
      `queries-AAAA-MM-DD.jsonl` > Fazer download. Salve em uma pasta local `ensaio/` (fora do
      repositório, ou dentro de `logs/`, que o Git ignora).
- [ ] Conferir que o arquivo tem linhas de busca e de clique: no PowerShell,
      `Select-String '"search"' ensaio\queries-AAAA-MM-DD.jsonl | Measure-Object` e o mesmo com
      `'"click"'`. Esperado: pelo menos uma linha de busca por rodada (9 rodadas) e pelo menos um
      clique por rodada. Se faltar, o log não está registrando e isso é um defeito a relatar.
- [ ] Calcular a latência (mediana e percentil 95) com o Python do ambiente local:

```
python -c "import json,sys,math,statistics as s; v=sorted(json.loads(l)['latency_ms'] for l in open(sys.argv[1],encoding='utf-8') if json.loads(l)['event']=='search'); print('n',len(v),'mediana',s.median(v),'p95',v[math.ceil(0.95*len(v))-1],'max',v[-1])" ensaio\queries-AAAA-MM-DD.jsonl
```

- [ ] Mediana: ______ ms · p95: ______ ms · máx: ______ ms. **Aprovado se mediana e p95 <= 200 ms.**
- [ ] Conferir que o log **não** tem IP, navegador nem nome: abrir o arquivo e procurar os campos
      (devem ser só os de `docs/architecture.md`, secao 5).

### B5. Veredito do ensaio

- [ ] 2 h completas sem queda irrecuperável: sim / não
- [ ] Partida a frio <= 5 min: sim / não
- [ ] Latência <= 200 ms: sim / não
- [ ] Se algum "não": registrar a causa provável e o que muda (por exemplo, mensagem na tela,
      passo no roteiro E) em `docs/journal/sprint-08.md`. Repetir o ensaio depois da correção.

## C. Plano B: Jupyter local

**Objetivo:** provar que, do zero, o mesmo notebook roda na máquina da feira.

- [ ] Em uma pasta nova, seguir **apenas** o `README.md`, seção "Como rodar localmente (plano B)",
      sem usar nada que já esteja instalado de outro jeito: `git clone`, criar o `venv`, instalar
      `requirements-app.txt`.
- [ ] Anotar qualquer passo em que o README não bastou (comando que falhou, programa que faltava,
      dúvida): ______ . Cada item vira correção no README.
- [ ] Abrir o notebook `notebooks/02_search_app.ipynb` no Jupyter com o kernel do `.venv`
      (lembrete: o Jupyter não está nos arquivos de requirements; instale à parte).
- [ ] Conferir a versão do Python: no notebook, `import sys; print(sys.version)` deve mostrar 3.13.x.
- [ ] Primeira execução com internet (baixa as *stopwords* do NLTK). Depois, repetir **sem
      internet** (desligar o Wi-Fi): a busca deve continuar funcionando; os pôsteres não aparecem,
      e isso é esperado.
- [ ] Executar tudo; tempo até a interface pronta: ______ s.
- [ ] Executar as 6 buscas da seção B2 e conferir os resultados esperados.
- [ ] **Determinismo:** para `robô que se apaixona`, anote os ids dos 5 primeiros filmes (campo
      `top_ids` do log local ou o que a tela mostrar) e compare com os do Colab (seção B).
      Devem ser idênticos, na mesma ordem. Local: ______ · Colab: ______
- [ ] Deixar o plano B **já aberto e executado** em outra janela durante a feira (seção E).

## D. Teste dos textos com 2 ou 3 pessoas leigas

**Objetivo:** ver se mensagens, rótulos e a seção de explicabilidade são entendidos sem a sua ajuda.
Pessoas leigas = não estudam nem trabalham com computação. Escolha, se puder, perfis diferentes
(por exemplo, uma pessoa do ensino médio e um adulto fora da área). Mínimo 2, ideal 3.

Preparação:
- [ ] Interface rodando (Colab ou local), na resolução de projeção.
- [ ] Papel e caneta. Não grave áudio nem vídeo; **não anote nome**: use "Pessoa 1", "Pessoa 2".
- [ ] Combine antes: você só observa e não explica nada, mesmo se a pessoa ficar parada.
      Pode dizer: "o que você esperava que acontecesse?"

Fale exatamente isto no início: "Estou testando o programa, não você. Se algo for confuso, o
problema é do programa. Pode pensar em voz alta?"

Tarefas, uma por vez (anote o tempo e o que a pessoa disse ou fez):

| # | Tarefa dita à pessoa | O que observar | Aprovado se |
|---|---|---|---|
| T1 | "Procure um filme descrevendo-o do seu jeito." | Achou a caixa e o botão sem ajuda? Usou os exemplos? | Fez a busca em até 1 minuto, sem ajuda |
| T2 | "Por que esse primeiro filme apareceu? Explique com suas palavras." | Citou as palavras destacadas na sinopse? | Disse que apareceu porque as palavras da busca estão na sinopse |
| T3 | "O que as barras significam?" | Entendeu "quanto cada palavra pesou"? Entendeu "palavra rara" e "palavra comum"? | Explicou que palavras mais raras pesam mais |
| T4 | "Escreva uma frase sem sentido (por exemplo, `xkcd lorem`) e veja o que acontece." | Entendeu a mensagem de nenhuma palavra no acervo? Soube o que fazer em seguida? | Disse o que fazer (tentar outras palavras) |
| T5 | "Para você, o que quer dizer 'pontuação'? De onde vem esse número?" | Leu o passo a passo (nível 3)? Ficou perdida em alguma palavra? | Disse que é uma soma de pesos das palavras, ainda que sem os termos técnicos |

Ficha por pessoa (copie uma para cada):

```
Pessoa N · perfil (ex.: ensino médio / adulto fora da área) · data
T1: tempo ___ · aprovada (S/N) · observação
T2: aprovada (S/N) · palavras que a pessoa usou
T3: aprovada (S/N) · palavras que a pessoa usou
T4: aprovada (S/N) · observação
T5: aprovada (S/N) · observação
Palavras ou frases da tela que a pessoa não entendeu (copiar do jeito que disse):
Onde a pessoa hesitou por mais de 10 segundos:
```

Depois dos testes:
- [ ] Reunir as fichas e listar, em ordem de quantas pessoas tropeçaram, os textos confusos.
- [ ] Para cada texto que 2 ou mais pessoas não entenderam, propor uma frase nova (linguagem
      simples, termo técnico entre parênteses, conforme `docs/ui_spec.md` secao 3) e passar ao
      responsável pela interface. Textos de interface são decisão do autor.
- [ ] **Aprovado se** pelo menos 2 de 3 pessoas (ou as 2 de 2) concluíram T1, T2 e T4 sem ajuda.
      Se não, corrigir os textos e repetir com **pessoas novas** (quem já viu a tela não serve).

## E. Se o Colab cair no meio da feira

**Prevenção (antes de abrir ao público):**

- [ ] Plano B (seção C) já executado e aberto em outra janela do navegador, com a interface pronta.
- [ ] Rede reserva (roteador do celular) testada na véspera.
- [ ] Esta seção impressa ou aberta em um celular.

**Se a interface parar de responder:**

1. Olhe o sintoma, sem mexer ainda:
   - "Reconectando" no Colab: espere até 30 segundos. Se voltou, siga.
   - Interface em branco ou erro de conexão: recarregue a página (F5) e espere 30 segundos.
2. Se não voltou, **troque para o plano B**: leve a janela do Jupyter local para a frente. Tempo
   para a troca: menos de 1 minuto, e é por isso que ele já está executado.
3. Se o plano B também não responde, no Jupyter local: Kernel > Reiniciar e executar tudo.
   Tempo esperado: o medido na seção C.
4. Enquanto isso, diga ao público: "Já volto em 1 minuto." Não deixe pessoas olhando uma tela de erro.
5. Em segundo plano, tente religar o Colab: Ambiente de execução > Desconectar e excluir ambiente
   de execução, abrir o notebook de novo, Executar tudo (até 5 min). Volte a ele só se estiver
   estável; **não troque de novo durante uma conversa com um visitante**.

**Registro (para não perder dados):**

- [ ] A cada 30 minutos de feira, baixe o log do Colab (seção B4). Se o Colab cair, o disco dele é
      apagado e o log do trecho não baixado se perde.
- [ ] Anote a hora da queda, o sintoma e quanto tempo levou para voltar (tabela B3). Os logs do
      Colab e do local ficam em arquivos diferentes: guarde os dois, com o nome do dia.

**Depois da feira:**

- [ ] Conferir o conjunto de logs baixados e mover para uma pasta fora do repositório
      (`logs/` nunca vai para o Git).
- [ ] Preencher "Pendências e riscos" em `docs/journal/sprint-08.md` com o que caiu e por quê.
