"""Monta a tela do Gradio a partir do serviço de busca e da configuração.

Este módulo é fino de propósito (D-057): cria os componentes, liga os eventos e
nada mais. Todo o conteúdo vem de ``ui/view.py``, que é testável sem abrir
navegador.

Duas regras do contrato (D-090) valem aqui:

- ``build_app`` **monta e devolve** o objeto Gradio e **nunca** chama
  ``.launch()``. Quem lança é o notebook 02, e só quando a variável de ambiente
  ``IR_MOVIES_NO_LAUNCH`` não vale exatamente ``"1"``.
- a tela fala somente com ``service`` (o protocolo) e com ``cfg``. Não conhece
  o índice TF-IDF nem o arquivo de log: o clique é registrado por
  ``service.log_click``.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import gradio as gr

from ir_movies.query.types import MAX_QUERY_CHARS
from ir_movies.ui import texts, view
from ir_movies.ui.styles import CSS

if TYPE_CHECKING:
    from ir_movies.query.types import SearchServiceProtocol

__all__ = ["build_app", "new_session_id"]


def new_session_id() -> str:
    """Identificador aleatório de uma visita (D-058).

    Sorteado a cada carregamento de página. Não tem nada da pessoa dentro: serve
    só para separar uma visita da seguinte no log anônimo.
    """
    return uuid.uuid4().hex


def _examples(cfg: dict) -> list[str]:
    """Perguntas de exemplo da configuração, limitadas por ``ui.max_examples``."""
    configured = list(cfg["ui"].get("examples") or [])
    return configured[: int(cfg["ui"].get("max_examples", len(configured)))]


def build_app(service: SearchServiceProtocol, cfg: dict) -> gr.Blocks:
    """Monta a interface descrita em ``docs/ui_spec.md`` e devolve o objeto Gradio.

    Não abre servidor nenhum: lançar é responsabilidade do notebook (D-090).
    """
    ui_cfg = cfg["ui"]

    def on_search(raw_query: str, session_id: str):
        screen = view.search_screen(service, cfg, raw_query, session_id)
        return (
            screen.gallery,
            screen.message,
            screen.panels.details,
            screen.panels.level1,
            screen.panels.level2,
            screen.panels.level3,
            screen.result,
        )

    def on_select(session_id: str, result, event: gr.SelectData):
        panels = view.select_panels(service, cfg, result, event.index, session_id)
        return panels.details, panels.level1, panels.level2, panels.level3

    # O ``elem_id`` é um identificador técnico, usado só pelo CSS: fica neutro
    # de propósito, porque o nome público do app vive no ``config.yaml`` e não
    # se repete no código (D-050).
    with gr.Blocks(title=str(ui_cfg["app_name"])) as demo:
        session_state = gr.State(value="")
        result_state = gr.State(value=None)

        # No Gradio 6.31 o ``elem_id`` do ``Blocks`` nao chega ao HTML; por isso o
        # conteudo fica num ``Column`` com o id que o CSS usa (D-079).
        with gr.Column(elem_id="ir-movies-app"):
            # O CSS entra como um bloco de estilo na própria página, e não pelo
            # parâmetro ``css`` do ``Blocks``: no Gradio 6 esse parâmetro só é lido
            # dentro de ``launch()``, e ``build_app`` nunca lança (D-055, D-090).
            gr.HTML(f"<style>{CSS}</style>")
            gr.HTML(view.header_html(cfg))
            gr.HTML(view.semantic_notice_html(service), elem_id="fu-semantic-notice")

            with gr.Row():
                query_box = gr.Textbox(
                    label=texts.SEARCH_LABEL,
                    placeholder=texts.SEARCH_PLACEHOLDER,
                    max_length=MAX_QUERY_CHARS,
                    lines=1,
                    scale=5,
                )
                search_button = gr.Button(texts.SEARCH_BUTTON, variant="primary", scale=1)

            example_buttons = []
            if _examples(cfg):
                gr.HTML(f'<p class="fu-hint">{texts.EXAMPLES_LABEL}</p>')
                with gr.Row():
                    for example in _examples(cfg):
                        example_buttons.append((example, gr.Button(example, size="sm")))

            # Cada componente que recebe conteúdo tem ``elem_id`` próprio. Serve ao
            # CSS e, sobretudo, aos testes: é por ele que se confere que cada valor
            # devolvido pelo manipulador chega ao componente certo.
            message_box = gr.HTML(value="", elem_id="fu-message")

            gr.HTML(f'<p class="fu-section-title">{texts.RESULTS_LABEL}</p>')
            gr.HTML(f'<p class="fu-hint">{texts.RESULTS_HINT}</p>')
            gallery = gr.Gallery(
                value=[],
                label=texts.RESULTS_LABEL,
                show_label=False,
                columns=int(ui_cfg["grid_columns"]),
                allow_preview=False,
                object_fit="contain",
                elem_id="fu-results",
            )

            gr.HTML(f'<p class="fu-section-title">{texts.DETAILS_TITLE}</p>')
            waiting = view.waiting_panels()
            details_box = gr.HTML(value=waiting.details, elem_id="fu-details-panel")

            gr.HTML(
                f'<p class="fu-section-title">{texts.EXPLAIN_TITLE}</p>'
                f'<p class="fu-hint">{texts.EXPLAIN_SUBTITLE}</p>'
            )
            # Os três níveis ficam sempre visíveis ao mesmo tempo (D-010).
            level1_box = gr.HTML(value=waiting.level1, elem_id="fu-level-1")
            level2_box = gr.HTML(value=waiting.level2, elem_id="fu-level-2")
            level3_box = gr.HTML(value=waiting.level3, elem_id="fu-level-3")

            gr.HTML(view.footer_html(service))

        search_outputs = [
            gallery,
            message_box,
            details_box,
            level1_box,
            level2_box,
            level3_box,
            result_state,
        ]
        search_inputs = [query_box, session_state]
        panel_outputs = [details_box, level1_box, level2_box, level3_box]

        demo.load(fn=new_session_id, inputs=None, outputs=session_state)
        search_button.click(fn=on_search, inputs=search_inputs, outputs=search_outputs)
        query_box.submit(fn=on_search, inputs=search_inputs, outputs=search_outputs)
        gallery.select(fn=on_select, inputs=[session_state, result_state], outputs=panel_outputs)

        for example, button in example_buttons:
            button.click(fn=lambda text=example: text, inputs=None, outputs=query_box).then(
                fn=on_search, inputs=search_inputs, outputs=search_outputs
            )

    return demo
