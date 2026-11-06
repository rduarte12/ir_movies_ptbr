"""Deriva um acervo mínimo e determinístico do snapshot real (D-070 a D-072).

O acervo mínimo serve de fixture para os testes de fumaça do notebook 02 e da
interface: tem poucos filmes (roda em segundos), mas contém de propósito os
estados que a interface precisa tratar (filme sem pôster, sem tagline, sem
duração, sem direção) e responde às consultas de exemplo da tela.

Uso:
    python scripts/make_mini_snapshot.py
    python scripts/make_mini_snapshot.py --dest outra/pasta

Lê ``data/snapshot_meta.json`` para descobrir o ``snapshot_id`` e, com ele, o
parquet de origem. Escreve **somente** em ``tests/fixtures/mini_snapshot/``
(ou na pasta dada em ``--dest``): o snapshot real nunca é alterado.

Determinismo: sem aleatoriedade; a ordem de desempate é sempre
``(-popularity, id)``. Rodar duas vezes gera arquivos idênticos byte a byte.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ir_movies.collect.snapshot import validate_snapshot  # noqa: E402
from ir_movies.config import load_config  # noqa: E402
from ir_movies.index.tfidf import TfidfIndex  # noqa: E402
from ir_movies.text.preprocess import Preprocessor  # noqa: E402

DEFAULT_SOURCE_DIR = ROOT / "data"
DEFAULT_DEST_DIR = ROOT / "tests" / "fixtures" / "mini_snapshot"

# Parâmetros da seleção (D-070). Teto de 50 filmes: o acervo precisa continuar pequeno.
MAX_MOVIES = 50
TARGET_MOVIES = 30
N_NO_POSTER = 3  # todos os sem pôster, até este limite (o snapshot real tem 2)
N_NO_TAGLINE = 3  # sem tagline, mas com pôster, por popularidade
N_NO_RUNTIME = 1  # duração 0 no snapshot (vira "desconhecida" na interface)
N_NO_DIRECTOR = 1
HITS_PER_EXAMPLE_QUERY = 2

# Consultas de exemplo de docs/ui_spec.md, secao 1.2.
EXAMPLE_QUERIES = (
    "um tubarão assustador na praia",
    "robô que se apaixona",
)


def _read_source(source_dir: Path) -> tuple[pd.DataFrame, dict]:
    """Lê o snapshot real, resolvendo o nome do parquet pelo ``snapshot_id``."""
    with open(source_dir / "snapshot_meta.json", encoding="utf-8") as f:
        meta = json.load(f)
    parquet = source_dir / f"movies_ptbr_{meta['snapshot_id']}.parquet"
    df = pd.read_parquet(parquet)
    # Ordem canônica: mais popular primeiro; empate decidido pelo id.
    df = df.sort_values(["popularity", "id"], ascending=[False, True]).reset_index(drop=True)
    return df, meta


def _document_text(row: pd.Series) -> str:
    """Texto indexado de um filme: título + tagline + sinopse + gêneros (D-013)."""
    return " ".join([row["title"], row["tagline"], row["overview"], " ".join(row["genres"])])


def select_ids(df: pd.DataFrame, cfg: dict) -> list[int]:
    """Escolhe os ids do acervo mínimo, na ordem canônica de ``df``.

    Critério, em ordem (D-070): estados de borda primeiro, depois os melhores
    resultados das consultas de exemplo, depois os mais populares até completar
    ``TARGET_MOVIES``.
    """
    chosen: list[int] = []

    def add(ids) -> None:
        for movie_id in ids:
            if movie_id not in chosen:
                chosen.append(int(movie_id))

    add(df[df["poster_path"].isna()]["id"].head(N_NO_POSTER))
    add(df[(df["tagline"] == "") & df["poster_path"].notna()]["id"].head(N_NO_TAGLINE))
    add(df[df["runtime"] == 0]["id"].head(N_NO_RUNTIME))
    add(df[df["director"] == ""]["id"].head(N_NO_DIRECTOR))

    preprocessor = Preprocessor(cfg["text"])
    index = TfidfIndex.build(
        [_document_text(row) for _, row in df.iterrows()], preprocessor, cfg["tfidf"]
    )
    for query in EXAMPLE_QUERIES:
        add(df.loc[hit.doc_id, "id"] for hit in index.search(query, k=HITS_PER_EXAMPLE_QUERY))

    # Preenchimento: os mais populares ainda não escolhidos, até o alvo.
    for movie_id in df["id"]:
        if len(chosen) >= TARGET_MOVIES:
            break
        add([movie_id])
    return chosen


def build_mini_snapshot(source_dir: Path, dest_dir: Path) -> tuple[Path, Path]:
    """Gera parquet + ``snapshot_meta.json`` do acervo mínimo em *dest_dir*."""
    cfg = load_config()
    df, source_meta = _read_source(source_dir)

    ids = select_ids(df, cfg)
    mini = df[df["id"].isin(ids)].reset_index(drop=True)  # mantém a ordem canônica

    errors = validate_snapshot(mini, cfg)
    if errors:
        raise ValueError("Acervo mínimo inválido:\n" + "\n".join(f"  - {e}" for e in errors))
    if len(mini) > MAX_MOVIES:
        raise ValueError(f"Acervo mínimo com {len(mini)} filmes (máximo {MAX_MOVIES}).")
    if not mini["poster_path"].isna().any():
        raise ValueError("Acervo mínimo sem nenhum filme sem pôster.")
    if not (mini["tagline"] == "").any():
        raise ValueError("Acervo mínimo sem nenhum filme sem tagline.")

    dest_dir.mkdir(parents=True, exist_ok=True)
    snapshot_id = source_meta["snapshot_id"]
    parquet_path = dest_dir / f"movies_ptbr_{snapshot_id}.parquet"
    mini.to_parquet(parquet_path, index=False, engine="pyarrow")

    words = [len(text.split()) for text in mini["overview"]]
    sorted_words = sorted(words)
    meta = dict(source_meta)  # created_utc herdado da origem: nada de relógio (determinismo)
    meta.update(
        {
            "candidates_tested": len(mini),
            "accepted": len(mini),
            "rejections_by_reason": {},
            "overview_word_count": {
                "min": sorted_words[0],
                "median": sorted_words[len(sorted_words) // 2],
                "max": sorted_words[-1],
            },
            "derived_from": {
                "snapshot_id": snapshot_id,
                "accepted": source_meta["accepted"],
                "script": "scripts/make_mini_snapshot.py",
            },
            "file_size_bytes": parquet_path.stat().st_size,
        }
    )
    meta_path = dest_dir / "snapshot_meta.json"
    with open(meta_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return parquet_path, meta_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera o acervo mínimo de testes.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST_DIR)
    args = parser.parse_args()

    parquet_path, meta_path = build_mini_snapshot(args.source, args.dest)
    n_rows = len(pd.read_parquet(parquet_path))
    print(f"Acervo mínimo: {n_rows} filmes")
    print(f"  {parquet_path}")
    print(f"  {meta_path}")


if __name__ == "__main__":
    main()
