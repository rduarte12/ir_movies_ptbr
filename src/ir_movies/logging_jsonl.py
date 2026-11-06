"""Log de consultas e cliques em JSONL, anônimo (D-008, D-030 a D-035).

Um arquivo por dia (``queries-AAAA-MM-DD.jsonl``, data em UTC), uma linha JSON por evento,
UTF-8, só acrescentando. O esquema está em ``docs/architecture.md`` secao 5.

Nunca registra IP, user-agent, nome de máquina nem qualquer dado pessoal: o logger nem
recebe esses dados. O único identificador é o ``session_id`` aleatório (D-031).
"""

from __future__ import annotations

import json
import logging
import secrets
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from ir_movies.config import PROJECT_ROOT
from ir_movies.query.types import MODEL_NAME, SearchResult

__all__ = ["MAX_TOP_IDS", "QueryLogger", "new_session_id"]

# Quantos ids do topo da lista vão para o campo `top_ids` (architecture.md secao 5).
MAX_TOP_IDS = 10

_warn = logging.getLogger(__name__)


def new_session_id() -> str:
    """Identificador de visita: 16 caracteres hexadecimais aleatórios (D-031)."""
    return secrets.token_hex(8)


def _utc_now() -> datetime:
    return datetime.now(UTC)


class QueryLogger:
    """Grava eventos ``search`` e ``click`` em ``<log_dir>/queries-AAAA-MM-DD.jsonl``.

    O contexto fixo de cada linha (versão do app, acervo, modelo, reescritor) é dado ao
    construir; assim quem registra um evento só passa o que é do evento (D-090).

    Com ``enabled=False`` nada é criado nem escrito (D-033). Uma falha de escrita vira
    aviso no ``logging`` padrão e não interrompe a busca.
    """

    def __init__(
        self,
        log_dir: str | Path,
        *,
        enabled: bool = True,
        app_version: str,
        snapshot_id: str,
        model: str = MODEL_NAME,
        rewriter: str = "identity",
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._dir = _resolve_log_dir(log_dir)
        self._enabled = enabled
        self._context = {
            "app_version": app_version,
            "snapshot_id": snapshot_id,
            "model": model,
            "rewriter": rewriter,
        }
        self._clock = clock
        self._lock = threading.Lock()

    @classmethod
    def from_config(
        cls,
        cfg: dict,
        *,
        app_version: str,
        snapshot_id: str,
        model: str = MODEL_NAME,
        rewriter: str = "identity",
        clock: Callable[[], datetime] = _utc_now,
    ) -> QueryLogger:
        """Monta o logger a partir da seção ``logging`` do ``config.yaml``."""
        section = cfg["logging"]
        return cls(
            section["dir"],
            enabled=bool(section["enabled"]),
            app_version=app_version,
            snapshot_id=snapshot_id,
            model=model,
            rewriter=rewriter,
            clock=clock,
        )

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def log_dir(self) -> Path:
        return self._dir

    def log_search(self, result: SearchResult, session_id: str) -> None:
        """Acrescenta uma linha de evento ``search``."""
        self._write(
            "search",
            session_id,
            {
                "raw_query": result.raw_query,
                "effective_query": result.effective_query,
                "n_query_tokens": len(set(result.trace.stems)),
                "n_oov_tokens": len(result.oov_terms),
                "n_results": len(result.hits),
                "top_ids": [h.movie_id for h in result.hits[:MAX_TOP_IDS]],
                "latency_ms": result.latency_ms,
            },
        )

    def log_click(self, session_id: str, movie_id: int, rank: int) -> None:
        """Acrescenta uma linha de evento ``click`` (``rank`` começa em 1)."""
        self._write("click", session_id, {"movie_id": int(movie_id), "rank": int(rank)})

    def _write(self, event: str, session_id: str, fields: dict) -> None:
        if not self._enabled:
            return
        now = self._clock()
        record = {
            "event": event,
            "ts": now.isoformat(timespec="milliseconds"),
            "session_id": str(session_id),
            **self._context,
            **fields,
        }
        line = json.dumps(record, ensure_ascii=False) + "\n"
        path = self._dir / f"queries-{now.strftime('%Y-%m-%d')}.jsonl"
        try:
            with self._lock:
                self._dir.mkdir(parents=True, exist_ok=True)
                with open(path, "a", encoding="utf-8", newline="\n") as f:
                    f.write(line)
        except OSError as exc:
            _warn.warning("Não foi possível gravar o log em %s: %s", path, exc)


def _resolve_log_dir(log_dir: str | Path) -> Path:
    path = Path(log_dir)
    return path if path.is_absolute() else PROJECT_ROOT / path
