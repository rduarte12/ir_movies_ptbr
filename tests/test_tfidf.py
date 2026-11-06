"""Testes do índice TF-IDF (D-015) e invariantes de architecture.md."""

import pytest
from sklearn.metrics.pairwise import cosine_similarity

from ir_movies.index.tfidf import Hit, TermContribution, TfidfIndex
from ir_movies.text.preprocess import Preprocessor

TEXT_CFG = {"stemmer": "snowball_pt", "extra_stopwords": [], "strip_accents": True}
TFIDF_CFG = {
    "ngram_range": [1, 1],
    "norm": "l2",
    "smooth_idf": True,
    "sublinear_tf": False,
    "min_df": 1,
}


@pytest.fixture
def prep():
    return Preprocessor(TEXT_CFG)


def _build_toy(prep, toy_corpus):
    """Constrói índice a partir do toy_corpus (campos concatenados, D-013)."""
    docs = []
    for m in toy_corpus:
        text = " ".join(
            [m["title"], m.get("tagline", ""), m["overview"], " ".join(m["genres"])]
        )
        docs.append(text)
    return TfidfIndex.build(docs, prep, TFIDF_CFG), docs


# --- Construção ---


class TestBuild:
    def test_matrix_shape(self, prep, toy_corpus):
        index, _ = _build_toy(prep, toy_corpus)
        assert index.n_docs == len(toy_corpus)

    def test_vocabulary_non_empty(self, prep, toy_corpus):
        index, _ = _build_toy(prep, toy_corpus)
        assert len(index.vocabulary) > 0


# --- Busca ---


class TestSearch:
    def test_returns_hits(self, prep, toy_corpus):
        index, _ = _build_toy(prep, toy_corpus)
        hits = index.search("robô apaixonado", k=5)
        assert len(hits) > 0
        assert all(isinstance(h, Hit) for h in hits)

    def test_descending_scores(self, prep, toy_corpus):
        index, _ = _build_toy(prep, toy_corpus)
        hits = index.search("robô", k=5)
        for i in range(len(hits) - 1):
            assert hits[i].score >= hits[i + 1].score

    def test_tiebreak_by_doc_id(self, prep):
        docs = ["gato bonito animal", "gato bonito animal"]
        index = TfidfIndex.build(docs, prep, TFIDF_CFG)
        hits = index.search("gato bonito animal", k=2)
        assert len(hits) == 2
        assert hits[0].score == hits[1].score
        assert hits[0].doc_id < hits[1].doc_id

    def test_respects_k(self, prep, toy_corpus):
        index, _ = _build_toy(prep, toy_corpus)
        hits = index.search("filme", k=2)
        assert len(hits) <= 2


# --- Invariante 1: sum(contribution) == cosseno ---


class TestInvariant1:
    def test_contributions_sum_equals_cosine(self, prep, toy_corpus):
        index, _ = _build_toy(prep, toy_corpus)
        query = "robô apaixonado"
        hits = index.search(query, k=5)
        assert len(hits) > 0
        for hit in hits:
            contribs = index.contributions(query, hit.doc_id)
            total = sum(c.contribution for c in contribs)
            assert abs(total - hit.score) < 1e-9, (
                f"doc {hit.doc_id}: sum={total}, score={hit.score}"
            )

    def test_contributions_match_sklearn_cosine(self, prep, toy_corpus):
        index, _ = _build_toy(prep, toy_corpus)
        query = "tubarão assustador na praia"
        q_vec = index._vectorizer.transform([query])
        for doc_id in range(index.n_docs):
            d_vec = index._matrix[doc_id]
            expected = cosine_similarity(q_vec, d_vec)[0, 0]
            contribs = index.contributions(query, doc_id)
            total = sum(c.contribution for c in contribs)
            assert abs(total - expected) < 1e-9

    def test_multiple_queries(self, prep, toy_corpus):
        """Invariante 1 vale para diversas consultas."""
        index, _ = _build_toy(prep, toy_corpus)
        queries = [
            "robô que se apaixona",
            "ilha misteriosa com perigos",
            "viagem espacial brasileira",
            "chuva de verão amor",
        ]
        for query in queries:
            hits = index.search(query, k=5)
            for hit in hits:
                contribs = index.contributions(query, hit.doc_id)
                total = sum(c.contribution for c in contribs)
                assert abs(total - hit.score) < 1e-9


# --- Invariante 2: OOV não entram no vetor ---


class TestInvariant2:
    def test_oov_not_in_contributions(self, prep, toy_corpus):
        index, _ = _build_toy(prep, toy_corpus)
        query = "xylophone robô"  # "xylophon" é OOV
        oov = index.oov_terms(query)
        assert len(oov) > 0
        hits = index.search(query, k=5)
        for hit in hits:
            contribs = index.contributions(query, hit.doc_id)
            contrib_stems = {c.stem for c in contribs}
            for term in oov:
                assert term not in contrib_stems

    def test_oov_listed_separately(self, prep, toy_corpus):
        index, _ = _build_toy(prep, toy_corpus)
        oov = index.oov_terms("xylophone zzznoexiste robô")
        assert len(oov) >= 2
        assert all(t not in index.vocabulary for t in oov)


# --- Invariante 3: determinismo ---


class TestInvariant3:
    def test_same_query_same_ranking(self, prep, toy_corpus):
        index, _ = _build_toy(prep, toy_corpus)
        query = "robô apaixonado"
        r1 = [(h.doc_id, h.score) for h in index.search(query, k=5)]
        r2 = [(h.doc_id, h.score) for h in index.search(query, k=5)]
        assert r1 == r2

    def test_rebuild_same_ranking(self, prep, toy_corpus):
        _, docs = _build_toy(prep, toy_corpus)
        idx1 = TfidfIndex.build(docs, prep, TFIDF_CFG)
        idx2 = TfidfIndex.build(docs, prep, TFIDF_CFG)
        query = "tubarão na praia"
        r1 = [(h.doc_id, h.score) for h in idx1.search(query, k=5)]
        r2 = [(h.doc_id, h.score) for h in idx2.search(query, k=5)]
        assert r1 == r2


# --- Invariante 4: consulta sem termos no vocabulário → lista vazia ---


class TestInvariant4:
    def test_all_oov_returns_empty(self, prep, toy_corpus):
        index, _ = _build_toy(prep, toy_corpus)
        hits = index.search("xylophone zzznoexiste", k=5)
        assert hits == []

    def test_only_stopwords_returns_empty(self, prep, toy_corpus):
        index, _ = _build_toy(prep, toy_corpus)
        hits = index.search("o de a um uma", k=5)
        assert hits == []


# --- Invariante 5: mesmo Preprocessor para docs e consultas ---


class TestInvariant5:
    def test_same_preprocessor(self, prep, toy_corpus):
        index, _ = _build_toy(prep, toy_corpus)
        assert index._preprocessor is prep


# --- Contribuições ---


class TestContributions:
    def test_structure(self, prep, toy_corpus):
        index, _ = _build_toy(prep, toy_corpus)
        contribs = index.contributions("robô apaixonado", doc_id=0)
        assert len(contribs) > 0
        for c in contribs:
            assert isinstance(c, TermContribution)
            assert isinstance(c.stem, str)
            assert isinstance(c.surface_forms, list)
            assert c.idf > 0
            assert isinstance(c.contribution, float)

    def test_sorted_by_contribution_desc(self, prep, toy_corpus):
        index, _ = _build_toy(prep, toy_corpus)
        contribs = index.contributions("robô apaixonado", doc_id=0)
        for i in range(len(contribs) - 1):
            assert contribs[i].contribution >= contribs[i + 1].contribution

    def test_surface_forms_from_query(self, prep, toy_corpus):
        index, _ = _build_toy(prep, toy_corpus)
        contribs = index.contributions("robô", doc_id=0)
        stems = {c.stem for c in contribs}
        assert any("robo" in c.surface_forms for c in contribs if c.stem in stems)
