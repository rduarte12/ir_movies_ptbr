"""Gera os vetores semânticos do corpus e salva em data/.

Lê o snapshot, codifica os textos em lotes com ``sentence-transformers``,
L2-normaliza e salva:

  data/embeddings_<slug>_<snapshot_id>.npy   — matriz (N, D) float32
  data/embeddings_<slug>_<snapshot_id>.json  — metadados

Uso:
  python scripts/build_embeddings.py
  python scripts/build_embeddings.py --config config.yaml

Para evitar chamadas de rede após o primeiro download, defina
HF_HUB_OFFLINE=1 no ambiente.

Decisões: D-093, D-094, D-099.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def _slug(model_name: str) -> str:
    return model_name.replace("/", "_").replace("-", "_").lower()


def build_embeddings(config_path: Path) -> None:
    from ir_movies.config import load_config
    from ir_movies.query.snapshot_loader import document_text, load_snapshot

    cfg = load_config(config_path)
    sem_cfg = cfg.get("semantic", {})
    model_name: str = str(sem_cfg.get("model", ""))
    revision_cfg: str | None = str(sem_cfg.get("revision")) or None
    batch_size: int = int(sem_cfg.get("batch_size", 32))

    data_dir_raw = sem_cfg.get("embeddings_dir", "data")
    data_dir = Path(data_dir_raw)
    if not data_dir.is_absolute():
        data_dir = PROJECT_ROOT / data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    print(f"Carregando snapshot de {data_dir} ...")
    snapshot = load_snapshot(data_dir)
    texts = [document_text(m) for m in snapshot.movies]
    n_docs = len(texts)
    print(f"  {n_docs} filmes, snapshot_id={snapshot.snapshot_id}")

    print(f"Carregando modelo {model_name!r} ...")
    from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

    model = SentenceTransformer(model_name, revision=revision_cfg)
    dim = model.get_sentence_embedding_dimension()
    max_seq_length = getattr(model, "max_seq_length", None)
    print(f"  dim={dim}, max_seq_length={max_seq_length}")

    # Revisão real do commit do modelo (lida do cache do HF)
    try:
        revision_actual = _read_model_revision(model)
    except Exception:
        revision_actual = revision_cfg or ""

    print(f"Codificando {n_docs} documentos em lotes de {batch_size} ...")
    t0 = time.perf_counter()
    n_truncated = 0

    import torch

    all_vecs: list[np.ndarray] = []
    with torch.inference_mode():
        for start in range(0, n_docs, batch_size):
            batch = texts[start : start + batch_size]
            vecs = model.encode(
                batch,
                normalize_embeddings=True,
                show_progress_bar=False,
                batch_size=len(batch),
            )
            all_vecs.append(np.array(vecs, dtype=np.float32))
            done = min(start + batch_size, n_docs)
            pct = done / n_docs * 100
            bar_len = 40
            filled = int(bar_len * done / n_docs)
            bar = "#" * filled + "-" * (bar_len - filled)
            print(f"\r  [{bar}] {done}/{n_docs} ({pct:.0f}%)", end="", flush=True)

    print()
    elapsed = time.perf_counter() - t0

    vectors = np.vstack(all_vecs)  # (N, D)

    # Verificação de truncamento: tokens > max_seq_length
    if max_seq_length:
        from transformers import AutoTokenizer  # type: ignore[import-untyped]

        try:
            tokenizer = AutoTokenizer.from_pretrained(model_name, revision=revision_actual or None)
            for text in texts:
                toks = tokenizer.encode(text, add_special_tokens=True)
                if len(toks) > max_seq_length:
                    n_truncated += 1
        except Exception as exc:
            print(f"  Aviso: não foi possível verificar truncamentos: {exc}")

    slug = _slug(model_name)
    base = data_dir / f"embeddings_{slug}_{snapshot.snapshot_id}"
    npy_path = base.with_suffix(".npy")
    json_path = base.with_suffix(".json")

    np.save(npy_path, vectors)

    import sentence_transformers
    import transformers

    meta = {
        "model": model_name,
        "revision": revision_actual,
        "dimension": int(dim),
        "max_seq_length": max_seq_length,
        "n_docs": n_docs,
        "n_docs_truncated": n_truncated,
        "snapshot_id": snapshot.snapshot_id,
        "created_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "versions": {
            "torch": str(torch.__version__),
            "sentence_transformers": str(sentence_transformers.__version__),
            "transformers": str(transformers.__version__),
            "numpy": str(np.__version__),
        },
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Vetores salvos em {npy_path} ({vectors.nbytes / 1e6:.1f} MB)")
    print(f"Metadados em     {json_path}")
    print(f"Shape: {vectors.shape}, docs truncados: {n_truncated}, tempo: {elapsed:.1f}s")
    print()
    print("Para usar, copie esta linha para config.yaml (semantic.revision):")
    print(f"  revision: \"{revision_actual}\"")


def _read_model_revision(model) -> str:
    """Tenta ler o commit do modelo a partir dos metadados do cache do HF."""
    try:
        # SentenceTransformer armazena o model_card_data
        card = getattr(model, "model_card_data", None)
        if card and hasattr(card, "model_id"):
            from huggingface_hub import model_info  # type: ignore[import-untyped]

            info = model_info(card.model_id)
            return str(info.sha or "")
    except Exception:
        pass
    return ""


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera vetores semânticos do corpus (D-093, D-094)."
    )
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "config.yaml"),
        help="Caminho do config.yaml (padrão: config.yaml na raiz do projeto)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    build_embeddings(Path(args.config))
