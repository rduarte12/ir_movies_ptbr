"""Reescrita da consulta antes do pré-processamento (D-009).

O protocolo ``Rewriter`` está em ``ir_movies.query.types``; este módulo traz a
única implementação da v1.
"""

from __future__ import annotations

from ir_movies.query.types import Rewriter

__all__ = ["IdentityRewriter", "Rewriter"]


class IdentityRewriter:
    """Reescritor neutro: devolve a consulta exatamente como veio (D-009).

    É o ponto de extensão do pipeline ``consulta bruta -> Rewriter ->
    pré-processamento -> modelo``. Um reescritor por modelo de linguagem entraria
    aqui, implementando o mesmo protocolo, sem tocar no índice nem na tela.

    O custo dessa troca é o determinismo: hoje a mesma consulta sempre produz a
    mesma lista de filmes, e um modelo de linguagem poderia reescrevê-la de formas
    diferentes a cada chamada. Por isso a troca exigiria um interruptor, um cache e
    a exibição da consulta reescrita (consequências já anotadas em D-009).
    """

    name = "identity"

    def rewrite(self, raw: str) -> str:
        """Devolve *raw* sem alteração."""
        return raw
