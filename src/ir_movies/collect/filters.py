"""Filtros de qualidade para filmes candidatos (D-004, D-025)."""

from __future__ import annotations


def _count_words(text: str) -> int:
    """Conta palavras separadas por espaço."""
    return len(text.split())


def evaluate(raw: dict, cfg: dict) -> tuple[bool, str | None]:
    """Avalia se o filme atende aos critérios de qualidade.

    Retorna ``(True, None)`` se aceito ou ``(False, motivo)`` se rejeitado.
    Motivos possíveis: ``"adult"``, ``"no_overview"``, ``"short_overview"``,
    ``"low_votes"``.
    """
    snap_cfg = cfg.get("snapshot", {})
    min_words = snap_cfg.get("min_overview_words", 5)
    min_votes = snap_cfg.get("min_vote_count", 2)
    exclude_adult = snap_cfg.get("exclude_adult", True)

    if exclude_adult and raw.get("adult", False):
        return False, "adult"

    overview = raw.get("overview") or ""
    if not overview.strip():
        return False, "no_overview"

    if _count_words(overview) < min_words:
        return False, "short_overview"

    if raw.get("vote_count", 0) < min_votes:
        return False, "low_votes"

    return True, None
