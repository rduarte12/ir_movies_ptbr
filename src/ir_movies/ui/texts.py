"""Textos da interface, em PT-BR, conforme ``docs/ui_spec.md``.

Todo texto que a pessoa lê na tela mora aqui. Dois motivos:

- as mensagens dos seis estados de ``ui_spec.md`` secao 2 são **cópias literais**
  da especificação, e um lugar só torna a conferência possível de olho;
- o público é leigo (ensino médio, pais, comerciantes) e o texto é a parte que
  precisa ser revista com pessoas de verdade, sem abrir código.

Mudar qualquer mensagem desta seção exige decisão registrada (D-059).
"""

# --- Cabeçalho (ui_spec.md secao 1.1) ---

TAGLINE = "Descreva um filme do seu jeito e veja como o buscador pensa."

# --- Busca (ui_spec.md secao 1.2) ---

SEARCH_LABEL = "Descreva o filme que você procura"
SEARCH_PLACEHOLDER = "Ex.: um tubarão assustador na praia"
SEARCH_BUTTON = "Buscar"
EXAMPLES_LABEL = "Ou clique num exemplo:"

# --- Resultados e detalhes (ui_spec.md secao 1.3 e 1.4) ---

RESULTS_LABEL = "Resultados"
RESULTS_HINT = "Clique num pôster para ver os detalhes e a explicação."
DETAILS_TITLE = "Filme selecionado"
NO_POSTER_ALT = "Sem pôster"

LABEL_ORIGINAL_TITLE = "Título original"
LABEL_RUNTIME = "Duração"
LABEL_GENRES = "Gêneros"
LABEL_RATING = "Nota TMDB"
LABEL_DIRECTOR = "Direção"
LABEL_CAST = "Elenco"
LABEL_OVERVIEW = "Sinopse"
RUNTIME_UNIT = "min"
RATING_VOTES = "votos"

# --- Explicabilidade (ui_spec.md secao 1.5, D-010) ---

EXPLAIN_TITLE = "Explicabilidade"
EXPLAIN_SUBTITLE = "Por que este filme apareceu na sua busca."

LEVEL1_TITLE = "1 · Onde suas palavras aparecem"
LEVEL1_HINT = "Na sinopse, cor mais forte quer dizer que a palavra contribuiu mais."

LEVEL2_TITLE = "2 · Quanto cada palavra pesou"
LEVEL2_HINT = "Barra maior e número maior querem dizer que a palavra somou mais à pontuação."
LEVEL2_RARE = "palavra rara"
LEVEL2_COMMON = "palavra comum"
# "IDF" nunca aparece na tela (ui_spec.md secao 3).
LEVEL2_RARITY_EXPLANATION = (
    "O selo vem da raridade da palavra no acervo: palavra que aparece em poucos filmes "
    "ajuda mais a distinguir um filme dos outros, então pesa mais."
)

LEVEL3_TITLE = "3 · Das palavras ao número (passo a passo)"
LEVEL3_STEP_QUERY = "a) Sua pergunta"
LEVEL3_STEP_STOPPED = "b) Palavras ignoradas por serem comuns"
LEVEL3_STEP_STEMS = "c) Palavras reduzidas ao radical"
LEVEL3_STEP_OOV = "d) Palavras que não existem no acervo"
LEVEL3_STEP_TABLE = "e) Conta de cada radical"
LEVEL3_STEP_SUM = "f) Soma dos produtos = pontuação"

LEVEL3_COL_STEM = "radical"
LEVEL3_COL_QUERY_WEIGHT = "peso na pergunta"
LEVEL3_COL_DOC_WEIGHT = "peso no filme"
LEVEL3_COL_PRODUCT = "produto"
LEVEL3_SUM_LABEL = "Soma dos produtos"
LEVEL3_SCORE_LABEL = "Pontuação deste filme"
LEVEL3_ROUNDING_NOTE = (
    "Os valores da tabela estão arredondados para 3 casas decimais; a soma é a pontuação exata."
)
LEVEL3_STEMS_HINT = (
    "Antes de comparar, o buscador põe tudo em minúsculas e tira os acentos. Depois reduz "
    'cada palavra ao radical, para juntar as formas da mesma palavra: "assustador" e '
    '"assustadora" viram "assust".'
)
LEVEL3_NONE = "nenhuma"
NO_MATCHED_WORDS = "Nenhuma palavra da sua pergunta aparece neste filme."
WAITING_FOR_SEARCH = "Faça uma busca para ver a explicação."

# --- Etapa semântica (D-100) ---

SEMANTIC_NOTICE = "Primeiro, sua pergunta passa por uma IA que entende o significado."

# --- Estados (ui_spec.md secao 2) ---
# Textos copiados da especificação, palavra por palavra.

STATE_EMPTY_QUERY = "Escreva algo sobre o filme que você procura."
STATE_ONLY_STOPWORDS = (
    "Todas as suas palavras são comuns demais para ajudar a busca. "
    "Tente incluir assuntos, objetos ou lugares."
)
STATE_NO_WORD_IN_CORPUS = (
    "Nenhuma das suas palavras aparece nas sinopses. Tente outras palavras ou sinônimos."
)
STATE_UNEXPECTED_ERROR = "Algo deu errado. Tente de novo."

# --- Rodapé (ui_spec.md secao 1.6) ---

TMDB_ATTRIBUTION = "Este produto usa a API da TMDB mas não é endossado nem certificado pela TMDB"
LOG_NOTICE = "As buscas são registradas de forma anônima"
FOOTER_VERSION = "versão"
FOOTER_SNAPSHOT = "acervo"
