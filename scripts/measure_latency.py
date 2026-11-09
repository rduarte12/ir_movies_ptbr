"""Mede latência de codificação de consulta e de busca completa.

Carrega o serviço real, executa 50 consultas (exemplos do config + variações) e
imprime mediana e p95 de:
  (a) codificação da consulta (SemanticRetriever.top_k isolado)
  (b) busca completa (SearchService.search)

Decisão: project_scope.md criterio <= 200 ms por busca. Se estourar, apenas
relata; nao altera o criterio.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


QUERY_EXTRAS = [
    "heroi que salva o mundo",
    "familia em perigo",
    "amor proibido em tempo de guerra",
    "detetive investigando um crime",
    "crianca com poderes sobrenaturais",
    "vampiros na cidade moderna",
    "navio afundando no oceano",
    "lutador de artes marciais",
    "cientista louco e sua criacao",
    "fugitivo procurado pela policia",
    "exploradores em selva desconhecida",
    "romance entre inimigos",
    "jogador de futebol famoso",
    "piloto de aviao em apuros",
    "inteligencia artificial que ganha consciencia",
    "espioes em missao secreta",
    "rebeliao em nave espacial",
    "bruxa jovem aprendendo magia",
    "sobreviventes num apocalipse zombie",
    "medico que descobre uma cura",
    "atleta olímpico superando obstáculos",
    "empresa corrompida e jornalista corajoso",
    "musico incompreendido que busca fama",
    "tempo que se repete todo dia",
    "duas civilizacoes em guerra intergalatica",
]


def _percentile(values: list[float], p: float) -> float:
    return float(np.percentile(values, p))


def main() -> None:
    from ir_movies.config import load_config
    from ir_movies.query.service import SearchService

    cfg = load_config(PROJECT_ROOT / "config.yaml")
    examples: list[str] = list(cfg["ui"].get("examples") or [])

    queries = (examples + QUERY_EXTRAS)[:50]
    while len(queries) < 50:
        queries += queries
    queries = queries[:50]

    sem_enabled = cfg.get("semantic", {}).get("enabled", False)
    print(f"Carregando serviço real (semantic.enabled={sem_enabled})...")
    service = SearchService.from_config(PROJECT_ROOT / "config.yaml")
    print(f"  semantic_active: {service.semantic_active}")
    print()

    # --- (a) latência de codificação da consulta ---
    encode_times: list[float] = []
    if service.semantic_active and service._semantic_retriever is not None:
        retriever = service._semantic_retriever
        for q in queries:
            t0 = time.perf_counter()
            retriever.top_k(q, k=20)
            encode_times.append((time.perf_counter() - t0) * 1000)
    else:
        print("(etapa semantica inativa: latencia de codificacao nao medida)")

    # --- (b) latência de busca completa ---
    search_times: list[float] = []
    for q in queries:
        t0 = time.perf_counter()
        service.search(q)
        search_times.append((time.perf_counter() - t0) * 1000)

    print(f"Consultas medidas: {len(queries)}")
    print()
    if encode_times:
        print("(a) Codificacao da consulta (semântico.top_k):")
        print(f"    mediana = {_percentile(encode_times, 50):.1f} ms")
        print(f"    p95     = {_percentile(encode_times, 95):.1f} ms")
        print()
    print("(b) Busca completa (SearchService.search):")
    print(f"    mediana = {_percentile(search_times, 50):.1f} ms")
    print(f"    p95     = {_percentile(search_times, 95):.1f} ms")
    print()
    criterio = 200
    p95 = _percentile(search_times, 95)
    if p95 <= criterio:
        print(f"Criterio de project_scope.md (<= {criterio} ms): ATENDIDO (p95 = {p95:.1f} ms)")
    else:
        print(
            f"Criterio de project_scope.md (<= {criterio} ms): NAO ATENDIDO "
            f"(p95 = {p95:.1f} ms). Apenas relatado; criterio nao alterado."
        )


if __name__ == "__main__":
    main()
