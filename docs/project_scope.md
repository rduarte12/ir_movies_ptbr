# Escopo do projeto — Buscador de filmes PT-BR

> Atualizado em 2026-11-05. Decisões e motivos em `decisions.md` (IDs `D-NNN` citados abaixo).

## 1. Contexto e objetivo

Aplicação para a **feira de extensão do ICMC-USP**: demonstrar de forma lúdica como um buscador funciona.
A pessoa digita uma frase sobre um filme; o sistema ranqueia filmes por **TF-IDF + similaridade do cosseno** e mostra, de forma visual, **por que** cada filme apareceu (Explicabilidade).

## 2. Público e contexto de uso

- Todos os públicos: ensino médio, pais, comerciantes, universitários. Linguagem simples; termos técnicos entre parênteses.
- Demo de ~2h, no notebook do autor (Colab com Gradio; plano B: Jupyter local). Internet confiável.
- Modelos escolhidos por serem **determinísticos**: mesma consulta, mesmo resultado (D-005).

## 3. Escopo da v1

1. **Coleta** (notebook 01, local): top 20 mil filmes por popularidade com sinopse PT-BR, via API da TMDB → snapshot versionado (D-002, D-003, D-004, D-016).
2. **Buscador** (notebook 02, Colab): interface estilo marketplace (grade de pôsteres + detalhes ao clicar) com consulta em linguagem natural (D-005, D-007).
3. **Explicabilidade** em 3 níveis, sempre visíveis (D-010).
4. **Log de consultas** anônimo em JSONL (D-008).
5. **Ponto de extensão** para reescrita de consulta por LLM, **sem implementá-lo** (D-009).

## 4. Fora do escopo da v1

BM25 / toggle de modelos, embeddings, busca híbrida, LLM, login, deploy público permanente, avaliação com qrels, recomendação personalizada.

## 5. Metas verificáveis (propostas, ajustar após a Sprint 4)

- Latência de uma busca ≤ 200 ms no notebook do autor (índice em memória).
- Notebook 02 "Run all" no Colab, a partir de sessão nova, sem passos manuais, em ≤ 5 min.
- Estabilidade por 2h contínuas em ensaio.
- Invariante de explicabilidade: soma das contribuições por termo = score de cosseno (tolerância 1e-9).

## 6. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Colab desconecta por ociosidade ou limite de duração | Plano B local com o mesmo notebook; aba aberta; ensaio de 2h |
| Logs no Colab somem ao fim da sessão (disco efêmero) | Questão aberta Q-001: baixar o log ao final ou espelhar no Drive |
| Sinopses curtas → descasamento de vocabulário ("robô" × "androide") | Aceito e tratado como momento didático; mensagens claras na UI |
| Mudança de versão do Gradio quebra a UI | Versão fixada; teste no Colab desde a Sprint 6 |
| Snapshot grande demais para o GitHub | Verificar tamanho na Sprint 2 (alerta em 50 MB) |
| Termos de uso da TMDB | Atribuição visível; uso não comercial; revisar termos antes de publicar |
