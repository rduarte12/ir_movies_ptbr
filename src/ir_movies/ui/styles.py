"""CSS da interface, pensado para projeção (``ui_spec.md`` secao 3).

Três regras guiaram as escolhas:

- **fonte grande**: o corpo do texto parte de 18px e os títulos de seção de
  26px, porque a última fila da feira fica longe da tela;
- **contraste alto**: texto quase preto sobre fundo quase branco; as cores do
  destaque foram escolhidas com texto escuro por cima, para seguirem legíveis
  mesmo num projetor que lava as cores;
- **nada depende só de cor**: as faixas de destaque vêm acompanhadas de
  sublinhado crescente, e as barras do nível 2 trazem sempre o número ao lado.

As classes ``.hl-1`` a ``.hl-4`` correspondem às ``ui.highlight_levels`` faixas
de intensidade (D-051). Mudar o número de faixas na configuração pede uma classe
nova aqui; acima do que existe, a última faixa é reaproveitada.
"""

CSS = """
#filmusp-app, #filmusp-app * { font-size: 18px; }
#filmusp-app { max-width: 1400px; margin: 0 auto; }

.fu-header { padding: 0.6rem 0 0.2rem 0; border-bottom: 4px solid #1a1a1a; }
.fu-header h1 { font-size: 44px; font-weight: 800; margin: 0; color: #111111; }
.fu-header p { font-size: 22px; margin: 0.2rem 0 0.6rem 0; color: #333333; }

.fu-section-title { font-size: 26px; font-weight: 800; color: #111111;
  margin: 1.2rem 0 0.4rem 0; }
.fu-hint { font-size: 17px; color: #444444; margin: 0 0 0.6rem 0; }

.fu-message { font-size: 24px; font-weight: 700; color: #4a2800;
  background: #ffeec2; border-left: 10px solid #b36b00;
  padding: 0.9rem 1.1rem; border-radius: 6px; margin: 0.6rem 0; }

.fu-card { background: #ffffff; border: 2px solid #c9ced8; border-radius: 10px;
  padding: 1rem 1.2rem; margin: 0.4rem 0; }

.fu-details { display: flex; gap: 1.4rem; align-items: flex-start; }
.fu-details img, .fu-details svg { width: 228px; height: auto; border-radius: 8px;
  border: 2px solid #c9ced8; }
.fu-details h2 { font-size: 32px; font-weight: 800; margin: 0 0 0.4rem 0; color: #111111; }
.fu-details dl { margin: 0; }
.fu-details dt { font-weight: 700; color: #333333; }
.fu-details dd { margin: 0 0 0.5rem 0; color: #111111; }
.fu-overview { line-height: 1.55; color: #111111; }

.fu-level { border-top: 2px solid #d8dce4; padding-top: 0.8rem; margin-top: 1rem; }
.fu-level-title { font-size: 24px; font-weight: 800; color: #111111; margin: 0 0 0.2rem 0; }

.fu-highlighted { line-height: 2.0; font-size: 20px; color: #111111; }
.fu-highlighted mark { color: #111111; padding: 0.08em 0.18em; border-radius: 4px;
  font-weight: 700; }
.fu-highlighted mark.hl-1 { background: #ffeaa0; border-bottom: 2px solid #8a6d00; }
.fu-highlighted mark.hl-2 { background: #ffd24d; border-bottom: 4px solid #8a6d00; }
.fu-highlighted mark.hl-3 { background: #ffb01f; border-bottom: 6px solid #6b4a00; }
.fu-highlighted mark.hl-4 { background: #ff8a00; border-bottom: 8px solid #4d3300; }

.fu-bars { width: 100%; border-collapse: collapse; }
.fu-bars td { padding: 0.35rem 0.5rem; vertical-align: middle; border: 0; }
.fu-bar-word { font-weight: 700; font-size: 20px; white-space: nowrap; color: #111111; }
.fu-bar-track { width: 60%; background: #e7eaf0; border-radius: 4px; height: 26px; }
.fu-bar-fill { background: #0b5fa5; height: 26px; border-radius: 4px; }
.fu-bar-value { font-variant-numeric: tabular-nums; font-weight: 700; font-size: 20px;
  white-space: nowrap; color: #111111; }
.fu-badge { display: inline-block; font-size: 15px; font-weight: 700; padding: 0.1rem 0.5rem;
  border-radius: 999px; white-space: nowrap; }
.fu-badge-rare { background: #11304d; color: #ffffff; }
.fu-badge-common { background: #e7eaf0; color: #333333; border: 1px solid #aeb6c4; }

.fu-steps { margin: 0; padding: 0; list-style: none; }
.fu-steps > li { margin: 0 0 0.7rem 0; }
.fu-step-label { font-weight: 700; color: #333333; }
.fu-chip { display: inline-block; background: #eef1f6; border: 1px solid #c9ced8;
  border-radius: 6px; padding: 0.05rem 0.45rem; margin: 0.1rem 0.25rem 0.1rem 0;
  font-variant-numeric: tabular-nums; color: #111111; }
.fu-chip-oov { background: #ffe0e0; border-color: #c08080; }

.fu-table { border-collapse: collapse; margin-top: 0.4rem; }
.fu-table th, .fu-table td { border: 1px solid #aeb6c4; padding: 0.35rem 0.7rem;
  text-align: right; font-variant-numeric: tabular-nums; color: #111111; }
.fu-table th { background: #eef1f6; font-weight: 700; text-align: center; }
.fu-table td:first-child, .fu-table th:first-child { text-align: left; }
.fu-table tr.fu-total td { font-weight: 800; background: #ffeec2; border-top: 3px solid #333333; }

.fu-note { font-size: 15px; color: #444444; margin-top: 0.3rem; }

.fu-footer { border-top: 3px solid #333333; margin-top: 1.6rem; padding-top: 0.7rem;
  font-size: 16px; color: #333333; }
.fu-footer p { margin: 0.15rem 0; }
"""
