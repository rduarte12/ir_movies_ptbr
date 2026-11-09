"""TfidfIndex: construção, busca e contribuições por termo."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from ir_movies.text.preprocess import Preprocessor


@dataclass
class Hit:
    """Resultado de busca: posição no corpus e pontuação de cosseno."""

    doc_id: int
    score: float


@dataclass
class TermContribution:
    """Contribuição de um termo da consulta ao score de um documento."""

    stem: str
    surface_forms: list[str]
    idf: float
    q_weight: float
    d_weight: float
    contribution: float


class TfidfIndex:
    """Índice TF-IDF com busca por cosseno e decomposição de contribuições."""

    @classmethod
    def build(
        cls,
        docs: list[str],
        preprocessor: Preprocessor,
        cfg: dict,
    ) -> TfidfIndex:
        """Constrói o índice a partir de textos brutos."""
        index = cls()
        index._preprocessor = preprocessor
        index._vectorizer = TfidfVectorizer(
            analyzer=preprocessor.tokens,
            ngram_range=tuple(cfg.get("ngram_range", [1, 1])),
            norm=cfg.get("norm", "l2"),
            smooth_idf=cfg.get("smooth_idf", True),
            sublinear_tf=cfg.get("sublinear_tf", False),
            min_df=cfg.get("min_df", 1),
        )
        index._matrix = index._vectorizer.fit_transform(docs)
        return index

    @property
    def vocabulary(self) -> set[str]:
        return set(self._vectorizer.vocabulary_.keys())

    @property
    def n_docs(self) -> int:
        return self._matrix.shape[0]

    def search(self, query: str, k: int = 20) -> list[Hit]:
        """Busca por cosseno. Retorna até k hits, score desc, desempate por doc_id asc."""
        q_vec = self._vectorizer.transform([query])
        if q_vec.nnz == 0:
            return []
        scores = (self._matrix @ q_vec.T).toarray().ravel()
        nonzero_idx = np.flatnonzero(scores > 0)
        ranked = sorted(nonzero_idx, key=lambda i: (-scores[i], i))
        return [Hit(doc_id=int(i), score=float(scores[i])) for i in ranked[:k]]

    def score_subset(self, query: str, doc_ids: list[int]) -> list[Hit]:
        """Pontua os doc_ids dados usando o IDF do corpus inteiro (D-096).

        Não reajusta o vectorizer: o IDF é o mesmo do índice completo. Retorna
        só os doc_ids com score > 0, em ordem decrescente de score.
        """
        q_vec = self._vectorizer.transform([query])
        if q_vec.nnz == 0 or not doc_ids:
            return []
        subset = self._matrix[doc_ids]
        scores = (subset @ q_vec.T).toarray().ravel()
        hits = [
            Hit(doc_id=int(doc_ids[i]), score=float(scores[i]))
            for i in range(len(doc_ids))
            if scores[i] > 0
        ]
        return sorted(hits, key=lambda h: (-h.score, h.doc_id))

    def contributions(self, query: str, doc_id: int) -> list[TermContribution]:
        """Decomposição do score: contribuição de cada termo da consulta."""
        q_vec = self._vectorizer.transform([query])
        d_vec = self._matrix[doc_id]
        trace = self._preprocessor.trace(query)
        idf_array = self._vectorizer.idf_
        vocab = self._vectorizer.vocabulary_

        result: list[TermContribution] = []
        seen: set[str] = set()
        for stem in trace.stems:
            if stem in seen or stem not in vocab:
                continue
            seen.add(stem)
            idx = vocab[stem]
            q_w = float(q_vec[0, idx])
            d_w = float(d_vec[0, idx])
            result.append(
                TermContribution(
                    stem=stem,
                    surface_forms=trace.stem_to_surface.get(stem, [stem]),
                    idf=float(idf_array[idx]),
                    q_weight=q_w,
                    d_weight=d_w,
                    contribution=q_w * d_w,
                )
            )
        return sorted(result, key=lambda t: (-t.contribution, t.stem))

    def oov_terms(self, query: str) -> list[str]:
        """Radicais da consulta ausentes do vocabulário do índice."""
        stems = self._preprocessor.tokens(query)
        vocab = self._vectorizer.vocabulary_
        seen: set[str] = set()
        result: list[str] = []
        for s in stems:
            if s not in vocab and s not in seen:
                result.append(s)
                seen.add(s)
        return result
