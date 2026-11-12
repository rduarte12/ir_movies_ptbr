# Apresentação do FilmUSP

Apresentação interativa do projeto, publicada em <https://rmduarte.com.br/feira/filmusp/>.

O resultado final é **um único arquivo**, `site/dist/index.html`, com HTML, CSS, JavaScript,
dados e pôsteres embutidos. Ele abre direto do disco (duplo clique) ou de qualquer hospedagem
estática, sem servidor, sem configuração e sem depender da internet.

## Conteúdo

| Caminho | O que é |
|---|---|
| `site/src/index.html`, `style.css`, `app.js` | Fonte da apresentação (11 slides) |
| `site/data/presentation.json` | Dados gerados pelo serviço de busca real |
| `site/dist/index.html` | Arquivo final, autocontido |
| `site/dist/FilmUSP.pdf` | Versão em PDF, um slide por página |
| `scripts/export_presentation_data.py` | Gera `presentation.json` |
| `scripts/build_presentation.py` | Junta tudo em `site/dist/index.html` |

## De onde vêm os números

Tudo o que a apresentação mostra sai de `export_presentation_data.py`, que usa o mesmo
`SearchService` do app, com o `config.yaml` do repositório:

- rankings (TF-IDF puro, só significado e o combinado por RRF);
- rastreio do pré-processamento, pesos da consulta e contribuições por termo;
- os três níveis da Explicabilidade, gerados pelas mesmas funções de `ui/view.py`;
- vocabulário com df e idf (sem nomes próprios) e números do acervo e dos vetores.

O único cálculo feito no navegador é a soma do RRF no slide 8, quando a pessoa mexe no `k`.
Com o `k` do `config.yaml`, a ordem é idêntica à do serviço.

## Como regenerar

Na raiz do projeto, com o ambiente do notebook 02 ativo (o modelo semântico precisa estar no
cache local; com `HF_HUB_OFFLINE=1` funciona sem internet):

```
python scripts/export_presentation_data.py
python scripts/build_presentation.py --embed-posters
```

`--embed-posters` baixa da TMDB só os pôsteres que aparecem nos slides (cerca de 60) e os embute
no HTML. Sem a opção, a página busca os pôsteres no servidor da TMDB na hora de exibir, e eles
somem onde imagens externas são bloqueadas (algumas pré-visualizações) e na impressão.

O segundo script precisa do pacote `qrcode` (`pip install qrcode==8.2`), usado só para gerar o
QR code do último slide.

Regenere sempre que mudar o `config.yaml` (por exemplo `semantic.candidates` ou `semantic.rrf_k`),
o acervo ou os vetores.

## PDF

Abra `site/dist/index.html` no Chrome ou no Edge e use **Imprimir → Salvar como PDF**, com margens "Nenhuma" e "Gráficos de plano de fundo" marcado.
O tamanho da página já vem definido (16:9, um slide por página).

## Publicar no site

1. Copie `site/dist/index.html` para `feira/filmusp/index.html` no repositório do site.
2. Faça o deploy normal do site. Não há nada a configurar: é um arquivo estático.

## Navegação

- Setas, espaço, Page Up/Down, Home/End; ou os botões no canto inferior direito.
- No celular (tela estreita), os slides viram uma página única com rolagem.
- O endereço `#/n` abre direto o slide `n`.
