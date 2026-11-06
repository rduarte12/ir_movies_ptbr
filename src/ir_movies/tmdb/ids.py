"""Download e leitura do export diário de IDs da TMDB (D-003, D-022)."""

from __future__ import annotations

import gzip
import json
import logging
from datetime import date, timedelta
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_EXPORT_URL = "http://files.tmdb.org/p/exports/movie_ids_{date}.json.gz"


def _format_export_date(d: date) -> str:
    """Formata a data no padrão MM_DD_YYYY usado pela TMDB."""
    return d.strftime("%m_%d_%Y")


def download_id_export(
    target_date: date,
    dest_dir: str | Path,
    *,
    fallback_days: int = 1,
    timeout: int = 120,
) -> Path:
    """Baixa o export de IDs de filmes da TMDB para *dest_dir*.

    Tenta *target_date*; se falhar (HTTP != 200), recua até *fallback_days*
    dias anteriores. Sem autenticação (D-022).

    Retorna o caminho do arquivo salvo.
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    for offset in range(fallback_days + 1):
        d = target_date - timedelta(days=offset)
        url = _EXPORT_URL.format(date=_format_export_date(d))
        logger.info("Tentando download: %s", url)
        resp = requests.get(url, timeout=timeout, stream=True)
        if resp.status_code == 200:
            dest = dest_dir / f"movie_ids_{d.isoformat()}.json.gz"
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 256):
                    f.write(chunk)
            logger.info("Export salvo em %s (%d bytes)", dest, dest.stat().st_size)
            return dest
        logger.warning("HTTP %d para %s", resp.status_code, url)

    raise RuntimeError(
        f"Não foi possível baixar o export de IDs para {target_date} "
        f"(tentou {fallback_days + 1} dia(s))"
    )


def load_candidates(
    path: str | Path,
    *,
    exclude_adult: bool = True,
) -> list[tuple[int, float]]:
    """Lê o export gzipped e devolve candidatos ``(id, popularity)`` ordenados.

    Filtra ``adult=True`` quando *exclude_adult* (padrão). Ordena por
    ``popularity`` decrescente, com desempate estável por ``id`` crescente.
    """
    candidates: list[tuple[int, float]] = []
    path = Path(path)
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if exclude_adult and entry.get("adult", False):
                continue
            candidates.append((entry["id"], entry["popularity"]))

    candidates.sort(key=lambda x: (-x[1], x[0]))
    return candidates
