"""Exporta os dados da apresentação (``site/``) a partir do serviço de busca real.

Tudo o que a apresentação mostra sai daqui: rankings, rastreio do pré-processamento,
pesos, contribuições e os fragmentos HTML dos três níveis da Explicabilidade, gerados
pelas mesmas funções da interface (``ui/view.py``). Nada é recalculado à mão no
navegador, exceto a soma do RRF no slide interativo, que é aritmética sobre postos.

Uso (na raiz do projeto, com o ambiente do notebook 02 ativo)::

    python scripts/export_presentation_data.py
    python scripts/build_presentation.py

Saída: ``site/data/presentation.json``. Depende do modelo semântico no cache local
(o mesmo da busca híbrida); com ``HF_HUB_OFFLINE=1`` funciona sem internet.
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from unidecode import unidecode

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ir_movies.ui import texts, view  # noqa: E402
from ir_movies.ui.styles import CSS  # noqa: E402

OUT_PATH = ROOT / "site" / "data" / "presentation.json"

# Consultas do slide "onde as palavras não bastam": cada uma tem um filme-alvo que a
# frase descreve sem usar as palavras da sinopse. A última é um contraexemplo, em que
# o significado atrapalha, de propósito: a apresentação mostra os dois lados.
MEANING_CASES = [
    {"query": "rato que quer ser cozinheiro em paris", "target_title": "Ratatouille"},
    {"query": "peixinho perdido no oceano procurado pelo pai", "target_title": "Procurando Nemo"},
    {"query": "mafioso italiano e sua família", "target_title": "O Poderoso Chefão"},
    {
        "query": "garoto bruxo que estuda numa escola de magia",
        "target_title": "Harry Potter e a Pedra Filosofal",
    },
]

N_RESULTS = 10  # resultados mostrados por consulta
N_PANELS = 5  # filmes com os três níveis exportados, por consulta de exemplo
N_DEEP = 200  # profundidade para achar o posto do filme-alvo
VOCAB_MIN_DF = 2  # radicais raros demais ficam de fora do slide de raridade
NAME_RATIO = 0.8  # palavra com maiúscula em mais de 80% das ocorrências = nome próprio


def _movie_card(service, movie_id: int) -> dict:
    m = service.get_movie(movie_id)
    return {
        "id": m.id,
        "title": m.title,
        "year": m.year,
        "poster_path": m.poster_path,
        "overview": m.overview,
        "genres": list(m.genres),
    }


def _contrib_dict(c) -> dict:
    return {
        "stem": c.stem,
        "surface": list(c.surface_forms),
        "idf": c.idf,
        "q_weight": c.q_weight,
        "d_weight": c.d_weight,
        "contribution": c.contribution,
    }


def _trace_dict(trace) -> dict:
    return {
        "original_tokens": list(trace.original_tokens),
        "stopped": list(trace.stopped),
        "stems": list(trace.stems),
        "stem_to_surface": {k: list(v) for k, v in trace.stem_to_surface.items()},
    }


def _semantic_ranking(hybrid, query: str, k: int) -> list[tuple[int, float]]:
    retriever = hybrid._semantic_retriever  # noqa: SLF001 (leitura, sem alterar estado)
    return retriever.top_k(query, k)


def _candidates(hybrid, query: str, cfg: dict) -> list[dict]:
    """Candidatos semânticos com os dois postos usados pelo RRF (mesma regra do serviço)."""
    n_candidates = int(cfg["semantic"]["candidates"])
    sem = _semantic_ranking(hybrid, query, n_candidates)
    doc_ids = [d for d, _ in sem]
    tf_hits = hybrid._index.score_subset(query, doc_ids)  # noqa: SLF001
    tf_score = {h.doc_id: h.score for h in tf_hits}
    tf_order = sorted(tf_score, key=lambda d: (-tf_score[d], d))
    tf_rank = {d: i + 1 for i, d in enumerate(tf_order)}
    movies = hybrid._movies  # noqa: SLF001
    return [
        {
            "movie_id": movies[d].id,
            "sem_rank": i + 1,
            "sem_score": s,
            "tf_rank": tf_rank.get(d),
            "tf_score": tf_score.get(d, 0.0),
        }
        for i, (d, s) in enumerate(sem)
    ]


def _rank_of(ids: list[int], target: int | None) -> int | None:
    if target is None or target not in ids:
        return None
    return ids.index(target) + 1


def _find_movie(service, title: str) -> int | None:
    for m in service._movies:  # noqa: SLF001
        if m.title == title:
            return m.id
    return None


def _example(hybrid, cfg: dict, query: str, movies: dict) -> dict:
    result = hybrid.search(query, k=N_RESULTS)
    hits = []
    for i, h in enumerate(result.hits):
        movies.setdefault(h.movie_id, _movie_card(hybrid, h.movie_id))
        item = {
            "movie_id": h.movie_id,
            "rank": h.rank,
            "score": h.score,
            "semantic_score": h.semantic_score,
            "rrf_score": h.rrf_score,
        }
        if i < N_PANELS:
            movie = hybrid.get_movie(h.movie_id)
            contribs = hybrid.contributions(result.effective_query, h.doc_id)
            item["contributions"] = [_contrib_dict(c) for c in contribs]
            item["level1"] = view.level1_html(movie, contribs, cfg)
            item["level2"] = view.level2_html(contribs, cfg)
            item["level3"] = view.level3_html(result, contribs, cfg)
        hits.append(item)
    return {
        "query": query,
        "query_weights": _query_weights(hybrid, result.effective_query),
        "effective_query": result.effective_query,
        "trace": _trace_dict(result.trace),
        "oov_terms": list(result.oov_terms),
        "hits": hits,
    }


def _query_weights(hybrid, query: str) -> list[dict]:
    """Peso de cada radical da consulta no vetor TF-IDF já normalizado (L2)."""
    vec = hybrid._index._vectorizer  # noqa: SLF001
    row = vec.transform([query]).tocoo()
    inv = {i: t for t, i in vec.vocabulary_.items()}
    out = [
        {"stem": inv[j], "idf": float(vec.idf_[j]), "q_weight": float(v)}
        for j, v in zip(row.col, row.data, strict=True)
    ]
    return sorted(out, key=lambda e: -e["q_weight"])


def _meaning_case(hybrid, tfidf, cfg: dict, case: dict, movies: dict) -> dict:
    query = case["query"]
    target = _find_movie(hybrid, case["target_title"])
    tf_ids = [h.movie_id for h in tfidf.search(query, k=N_DEEP).hits]
    sem_ids = [hybrid._movies[d].id for d, _ in _semantic_ranking(hybrid, query, N_DEEP)]  # noqa: SLF001
    hy_ids = [h.movie_id for h in hybrid.search(query, k=N_DEEP).hits]
    for mid in tf_ids[:5] + sem_ids[:5] + hy_ids[:5] + ([target] if target else []):
        movies.setdefault(mid, _movie_card(hybrid, mid))
    return {
        "query": query,
        "target_id": target,
        "lists": {"tfidf": tf_ids[:5], "semantic": sem_ids[:5], "hybrid": hy_ids[:5]},
        "target_rank": {
            "tfidf": _rank_of(tf_ids, target),
            "semantic": _rank_of(sem_ids, target),
            "hybrid": _rank_of(hy_ids, target),
        },
    }


def _vocabulary(hybrid) -> dict:
    """Radicais com df, idf e a forma mais comum no acervo, sem nomes próprios.

    Cada entrada: ``[forma sem acento, radical, df, idf, forma com acento]``.
    """
    vec = hybrid._index._vectorizer  # noqa: SLF001
    n_docs = hybrid._index.n_docs  # noqa: SLF001
    pre = hybrid._preprocessor  # noqa: SLF001
    surface_count: dict[str, Counter] = {}
    accented: dict[str, Counter] = {}
    for text in _corpus_texts(hybrid):
        for tok in re.findall(r"[^\W_]+", text.lower()):
            accented.setdefault(unidecode(tok), Counter())[tok] += 1
    # Nome próprio = quase sempre com maiúscula no meio da sinopse (gêneros e títulos,
    # que também vêm com maiúscula, ficam fora desta contagem).
    in_overview: Counter = Counter()
    capitalized: Counter = Counter()
    for m in hybrid._movies:  # noqa: SLF001
        for raw in re.findall(r"[^\W_]+", m.overview):
            key = unidecode(raw.lower())
            in_overview[key] += 1
            if raw[0].isupper():
                capitalized[key] += 1
    for text in _corpus_texts(hybrid):
        tr = pre.trace(text)
        for stem, forms in tr.stem_to_surface.items():
            c = surface_count.setdefault(stem, Counter())
            for f in forms:
                c[f] += 1
    entries = []
    for stem, idx in vec.vocabulary_.items():
        idf = float(vec.idf_[idx])
        df = round((1 + n_docs) / math.exp(idf - 1) - 1)
        if df < VOCAB_MIN_DF:
            continue
        surface = surface_count.get(stem)
        word = surface.most_common(1)[0][0] if surface else stem
        forms = accented.get(word)
        total = in_overview[word]
        if total and capitalized[word] / total > NAME_RATIO:
            continue  # nomes de pessoas e lugares: o slide é sobre palavras comuns
        display = forms.most_common(1)[0][0] if forms else word
        entries.append([word, stem, df, round(idf, 4), display])
    entries.sort(key=lambda e: -e[2])
    return {"n_docs": n_docs, "n_terms_total": len(vec.vocabulary_), "entries": entries}


def _corpus_texts(hybrid) -> list[str]:
    from ir_movies.query.snapshot_loader import document_text

    return [document_text(m) for m in hybrid._movies]  # noqa: SLF001


def _stopwords(hybrid) -> list[str]:
    return sorted(hybrid._preprocessor._stopwords)  # noqa: SLF001


def build_payload(hybrid, tfidf, cfg: dict) -> dict:
    """Monta o dicionário completo. *hybrid* precisa da etapa semântica ativa."""
    if not hybrid.semantic_active:
        raise RuntimeError("A exportação precisa da etapa semântica ativa (semantic.enabled).")
    movies: dict[int, dict] = {}
    examples = [_example(hybrid, cfg, q, movies) for q in cfg["ui"]["examples"]]
    cases = [_meaning_case(hybrid, tfidf, cfg, c, movies) for c in MEANING_CASES]
    rrf_queries = [c["query"] for c in MEANING_CASES] + list(cfg["ui"]["examples"])
    rrf = []
    for q in rrf_queries:
        cands = _candidates(hybrid, q, cfg)
        for c in cands[:30]:
            movies.setdefault(c["movie_id"], _movie_card(hybrid, c["movie_id"]))
        for c in cands:
            if c["movie_id"] not in movies:
                m = hybrid.get_movie(c["movie_id"])
                movies[c["movie_id"]] = {"id": m.id, "title": m.title, "year": m.year}
        rrf.append({"query": q, "candidates": cands})

    snapshot_meta = json.loads((ROOT / "data" / "snapshot_meta.json").read_text("utf-8"))
    emb_meta_path = next((ROOT / cfg["semantic"]["embeddings_dir"]).glob("embeddings_*.json"))
    emb_meta = json.loads(emb_meta_path.read_text("utf-8"))

    keep_overview = {h["movie_id"] for ex in examples for h in ex["hits"]}
    for mid, card in movies.items():
        if mid not in keep_overview:
            card.pop("overview", None)

    return {
        "manifest": {
            "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "app_name": cfg["ui"]["app_name"],
            "app_version": hybrid.app_version,
            "snapshot_id": hybrid.snapshot_id,
            "n_movies": len(hybrid._movies),  # noqa: SLF001
            "snapshot": {
                "candidates_tested": snapshot_meta.get("candidates_tested"),
                "accepted": snapshot_meta.get("accepted"),
                "rejections_by_reason": snapshot_meta.get("rejections_by_reason"),
                "overview_word_count": snapshot_meta.get("overview_word_count"),
                "filters": snapshot_meta.get("filters"),
            },
            "config": {
                "text": cfg["text"],
                "tfidf": cfg["tfidf"],
                "semantic": {
                    k: cfg["semantic"][k] for k in ("model", "revision", "candidates", "rrf_k")
                },
                "rare_idf_threshold": cfg["ui"]["rare_idf_threshold"],
                "highlight_levels": cfg["ui"]["highlight_levels"],
                "score_decimals": cfg["ui"]["score_decimals"],
            },
            "embeddings": {
                k: emb_meta.get(k)
                for k in ("dimension", "max_seq_length", "n_docs", "n_docs_truncated", "versions")
            },
            "tmdb_attribution": texts.TMDB_ATTRIBUTION,
        },
        "ui_css": CSS,
        "movies": {str(k): v for k, v in movies.items()},
        "examples": examples,
        "meaning_cases": cases,
        "rrf": rrf,
        "vocabulary": _vocabulary(hybrid),
        "stopwords": _stopwords(hybrid),
    }


def main() -> None:
    from ir_movies.config import load_config
    from ir_movies.query.service import SearchService, _try_load_retriever
    from ir_movies.query.snapshot_loader import load_snapshot

    cfg = load_config(ROOT / "config.yaml")
    snapshot = load_snapshot()
    retriever = _try_load_retriever(cfg, snapshot.snapshot_id)
    hybrid = SearchService(snapshot, cfg, logger=_NullLogger(), semantic_retriever=retriever)
    tfidf = SearchService(snapshot, cfg, logger=_NullLogger())
    payload = build_payload(hybrid, tfidf, cfg)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"OK: {OUT_PATH.relative_to(ROOT)} ({size_kb:.0f} KB)")


class _NullLogger:
    """Exportar não é uso do app: nada vai para o log de consultas."""

    def log_search(self, result, session_id: str) -> None:
        pass

    def log_click(self, session_id: str, movie_id: int, rank: int) -> None:
        pass


if __name__ == "__main__":
    main()
