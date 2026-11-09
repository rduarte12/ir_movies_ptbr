"""Recuperação semântica por similaridade densa (D-093 a D-097).

Pipeline: consulta -> Encoder -> vetor L2-normalizado -> produto escalar com
corpus -> top-k candidatos -> passados ao TF-IDF via ``SearchService``.

O Encoder é carregado uma única vez (lock em ``SemanticRetriever``). Em produção
usa ``sentence-transformers``; nos testes usa ``FakeEncoder`` (vetores fixos).
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ir_movies.query.types import Encoder

__all__ = [
    "SemanticRetriever",
    "EmbeddingsMeta",
    "load_semantic_retriever",
]

logger = logging.getLogger(__name__)

EMBEDDINGS_TEMPLATE = "embeddings_{model_slug}_{snapshot_id}"


def _model_slug(model_name: str) -> str:
    """Converte nome do modelo em slug seguro para nome de arquivo."""
    return model_name.replace("/", "_").replace("-", "_").lower()


class EmbeddingsMeta:
    """Metadados gravados pelo ``scripts/build_embeddings.py``."""

    def __init__(self, data: dict) -> None:
        self._data = data

    @classmethod
    def load(cls, path: Path) -> EmbeddingsMeta:
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    @property
    def snapshot_id(self) -> str:
        return str(self._data["snapshot_id"])

    @property
    def model(self) -> str:
        return str(self._data["model"])

    @property
    def dimension(self) -> int:
        return int(self._data["dimension"])

    @property
    def n_docs(self) -> int:
        return int(self._data["n_docs"])

    @property
    def revision(self) -> str:
        return str(self._data.get("revision") or "")

    @property
    def raw(self) -> dict:
        return self._data


class SemanticRetriever:
    """Recuperação por similaridade semântica: encode-once + produto escalar.

    ``vectors``: matriz ``(N, D) float32`` L2-normalizada, linha i = doc_id i.
    O lock protege o encoder, que pode não ser thread-safe.
    """

    def __init__(
        self,
        encoder: Encoder,
        vectors: np.ndarray,
        snapshot_id: str,
        model_name: str = "",
        revision: str = "",
    ) -> None:
        self._encoder = encoder
        self._vectors = vectors
        self._snapshot_id = snapshot_id
        self._model_name = model_name
        self._revision = revision
        self._lock = threading.Lock()

    @property
    def n_docs(self) -> int:
        return self._vectors.shape[0]

    @property
    def dimension(self) -> int:
        return self._vectors.shape[1]

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def revision(self) -> str:
        return self._revision

    def top_k(self, query: str, k: int) -> list[tuple[int, float]]:
        """Devolve os k doc_ids mais próximos da consulta, com scores.

        Retorna lista de ``(doc_id, score)`` em ordem decrescente de score.
        O lock garante que o encoder não seja chamado em paralelo.
        """
        with self._lock:
            q_vec = self._encoder.encode([query])[0].astype(np.float32)
        norm = np.linalg.norm(q_vec)
        if norm > 0:
            q_vec = q_vec / norm
        scores = self._vectors @ q_vec
        if k >= len(scores):
            ranked_idx = np.argsort(-scores)
        else:
            ranked_idx = np.argpartition(-scores, k)[:k]
            ranked_idx = ranked_idx[np.argsort(-scores[ranked_idx])]
        return [(int(i), float(scores[i])) for i in ranked_idx[:k]]


def load_semantic_retriever(
    cfg: dict,
    snapshot_id: str,
    encoder: Encoder,
) -> SemanticRetriever:
    """Carrega e valida os vetores; levanta exceção descritiva em caso de problema.

    O chamador (SearchService.from_config) captura a exceção e cai para TF-IDF
    puro (D-097).
    """
    sem_cfg = cfg.get("semantic", {})
    model_name: str = str(sem_cfg.get("model", ""))
    revision: str = str(sem_cfg.get("revision") or "")

    from ir_movies.config import PROJECT_ROOT

    data_dir_raw = sem_cfg.get("embeddings_dir", "data")
    data_dir = Path(data_dir_raw)
    if not data_dir.is_absolute():
        data_dir = PROJECT_ROOT / data_dir

    slug = _model_slug(model_name)
    base = data_dir / f"{EMBEDDINGS_TEMPLATE.format(model_slug=slug, snapshot_id=snapshot_id)}"
    npy_path = base.with_suffix(".npy")
    json_path = base.with_suffix(".json")

    if not npy_path.is_file():
        raise FileNotFoundError(f"Vetores semânticos não encontrados: {npy_path}")
    if not json_path.is_file():
        raise FileNotFoundError(f"Metadados semânticos não encontrados: {json_path}")

    meta = EmbeddingsMeta.load(json_path)

    if meta.snapshot_id != snapshot_id:
        raise ValueError(
            f"snapshot_id dos vetores ({meta.snapshot_id!r}) "
            f"não bate com o do acervo ({snapshot_id!r})"
        )
    if meta.model != model_name:
        raise ValueError(
            f"Modelo dos vetores ({meta.model!r}) "
            f"não bate com o config ({model_name!r})"
        )

    vectors = np.load(npy_path)
    if vectors.ndim != 2 or vectors.shape[1] != meta.dimension:
        raise ValueError(
            f"Shape inesperado dos vetores: {vectors.shape} "
            f"(esperado (N, {meta.dimension}))"
        )

    vectors = vectors.astype(np.float32)
    logger.info(
        "Vetores semânticos carregados: shape=%s modelo=%r revisão=%r",
        vectors.shape,
        model_name,
        revision or meta.revision,
    )
    return SemanticRetriever(
        encoder=encoder,
        vectors=vectors,
        snapshot_id=snapshot_id,
        model_name=model_name,
        revision=revision or meta.revision,
    )
