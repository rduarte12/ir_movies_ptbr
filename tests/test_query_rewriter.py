"""Testes do IdentityRewriter (D-009)."""

import pytest

from ir_movies.query.rewriter import IdentityRewriter
from ir_movies.query.types import Rewriter


class TestIdentityRewriter:
    def test_satisfies_protocol(self):
        assert isinstance(IdentityRewriter(), Rewriter)

    def test_name_is_the_value_logged(self):
        assert IdentityRewriter().name == "identity"

    @pytest.mark.parametrize(
        "raw",
        ["robô apaixonado", "", "  espaços  e  MAIÚSCULAS  ", "!!! ???", "a\tb\nc"],
    )
    def test_returns_query_unchanged(self, raw):
        assert IdentityRewriter().rewrite(raw) == raw

    def test_is_deterministic(self):
        rewriter = IdentityRewriter()
        assert rewriter.rewrite("tubarão") == rewriter.rewrite("tubarão")

    def test_does_not_strip_or_normalize(self):
        """A normalização é trabalho do pré-processador, não do reescritor."""
        assert IdentityRewriter().rewrite("  Ação ") == "  Ação "
