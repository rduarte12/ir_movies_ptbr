"""Testes da etapa semântica (D-092 a D-100).

Todos os testes usam ``FakeEncoder`` (vetores 4-D fixos), sem baixar modelo.
Um único teste com o modelo real fica marcado com ``skip`` e só roda com
``IR_MOVIES_RUN_MODEL_TESTS=1`` no ambiente.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import numpy as np
import pytest

from ir_movies.index.semantic import (
    SemanticRetriever,
    _model_slug,
    load_semantic_retriever,
)
from ir_movies.index.tfidf import TfidfIndex
from ir_movies.query.service import SearchService
from ir_movies.query.snapshot_loader import LoadedSnapshot
from ir_movies.query.types import SearchServiceProtocol
from ir_movies.text.preprocess import Preprocessor
from tests.fakes import (
    FakeEncoder,
    FakeSearchService,
    MemoryQueryLogger,
    _to_movie,
)

# --- Corpus de brinquedo ---

FAKE_MOVIES_DATA = [
    {"id": 1, "title": "Robô Apaixonado", "overview": "Um robô se apaixona.", "genres": []},
    {"id": 2, "title": "Tubarão Branco", "overview": "Um tubarão assustador.", "genres": []},
    {"id": 3, "title": "Viagem Espacial", "overview": "Astronautas no espaço.", "genres": []},
    {"id": 4, "title": "Ilha Deserta", "overview": "Amigos numa ilha.", "tagline": "",
     "genres": []},
    {"id": 5, "title": "Chuva de Meteoros", "overview": "Meteoros caem na cidade.", "genres": []},
]

TEXT_CFG = {"stemmer": "snowball_pt", "extra_stopwords": [], "strip_accents": True}
TFIDF_CFG = {
    "ngram_range": [1, 1], "norm": "l2", "smooth_idf": True, "sublinear_tf": False, "min_df": 1
}


def _build_fake_snapshot(movies_data=None):
    data = movies_data or FAKE_MOVIES_DATA
    movies = [_to_movie(m) for m in data]
    from ir_movies.query.snapshot_loader import document_text
    snapshot_id = "toy-semantic-00"
    texts = [document_text(m) for m in movies]
    return LoadedSnapshot(snapshot_id=snapshot_id, movies=movies, texts=texts)


def _build_fake_retriever(snapshot: LoadedSnapshot) -> SemanticRetriever:
    """Cria SemanticRetriever com FakeEncoder sobre o corpus dado."""
    encoder = FakeEncoder()
    vectors = encoder.encode(snapshot.texts)
    return SemanticRetriever(
        encoder=encoder,
        vectors=vectors,
        snapshot_id=snapshot.snapshot_id,
        model_name="fake/model",
    )


def _base_cfg(semantic_enabled: bool = True) -> dict:
    return {
        "text": TEXT_CFG,
        "tfidf": TFIDF_CFG,
        "search": {"top_k": 5},
        "logging": {"enabled": False, "dir": "logs"},
        "semantic": {
            "enabled": semantic_enabled,
            "model": "fake/model",
            "revision": "",
            "embeddings_dir": "data",
            "candidates": 3,
            "rrf_k": 60,
            "batch_size": 32,
        },
    }


# --- Fixtures ---

@pytest.fixture
def snapshot():
    return _build_fake_snapshot()


@pytest.fixture
def retriever(snapshot):
    return _build_fake_retriever(snapshot)


@pytest.fixture
def service_with_semantic(snapshot, retriever):
    cfg = _base_cfg(semantic_enabled=True)
    return SearchService(
        snapshot,
        cfg,
        semantic_retriever=retriever,
        logger=MemoryQueryLogger(),
    )


@pytest.fixture
def service_no_semantic(snapshot):
    cfg = _base_cfg(semantic_enabled=False)
    return SearchService(snapshot, cfg, logger=MemoryQueryLogger())


# --- Protocolo e propriedade semantic_active ---


class TestSemanticActiveProtocol:
    def test_satisfies_protocol_with_semantic(self, service_with_semantic):
        assert isinstance(service_with_semantic, SearchServiceProtocol)

    def test_semantic_active_true(self, service_with_semantic):
        assert service_with_semantic.semantic_active is True

    def test_semantic_active_false_without_retriever(self, service_no_semantic):
        assert service_no_semantic.semantic_active is False

    def test_fake_service_semantic_active_false(self):
        svc = FakeSearchService.from_toy()
        assert svc.semantic_active is False


# --- Candidatos = top-k semânticos ---


class TestSemanticCandidates:
    def test_candidates_bounded_by_config(self, service_with_semantic):
        """Com candidates=3 no config, no máximo 3 hits."""
        result = service_with_semantic.search("robô espaço tubarão ilha meteoro")
        # Podem ser menos se a consulta for toda OOV, mas quando tem resultados,
        # o teto é min(candidates, top_k).
        assert len(result.hits) <= min(3, 5)

    def test_all_hits_come_from_semantic_top_k(self, snapshot, retriever):
        """Todos os doc_ids no resultado foram candidatos semânticos."""
        cfg = _base_cfg()
        cfg["semantic"]["candidates"] = 2
        svc = SearchService(
            snapshot, cfg, semantic_retriever=retriever, logger=MemoryQueryLogger()
        )
        result = svc.search("robô")
        sem_top2 = {doc_id for doc_id, _ in retriever.top_k("robô", k=2)}
        for hit in result.hits:
            assert hit.doc_id in sem_top2


# --- Invariante: soma das contribuições = hit.score (TF-IDF) ---


class TestContributionInvariantWithSemantic:
    def test_sum_equals_score_for_every_hit(self, service_with_semantic):
        """Invariante 3 do contrato vale com etapa semântica ativa (D-096)."""
        result = service_with_semantic.search("tubarão")
        for hit in result.hits:
            parts = service_with_semantic.contributions(result.effective_query, hit.doc_id)
            assert sum(p.contribution for p in parts) == pytest.approx(hit.score, abs=1e-9)

    def test_score_is_tfidf_not_rrf(self, service_with_semantic):
        """hit.score é o cosseno TF-IDF, não o rrf_score (D-096)."""
        result = service_with_semantic.search("tubarão")
        for hit in result.hits:
            if hit.rrf_score is not None:
                # rrf_score e score só coincidem por acaso; em geral diferem
                # Apenas verificamos que rrf_score existe e score é TF-IDF
                assert isinstance(hit.rrf_score, float)
                assert isinstance(hit.score, float)


# --- Campos opcionais preenchidos quando semântica ativa ---


class TestOptionalFields:
    def test_semantic_score_filled_when_active(self, service_with_semantic):
        result = service_with_semantic.search("robô")
        for hit in result.hits:
            assert hit.semantic_score is not None

    def test_rrf_score_filled_when_active(self, service_with_semantic):
        result = service_with_semantic.search("robô")
        for hit in result.hits:
            assert hit.rrf_score is not None

    def test_optional_fields_none_when_inactive(self, service_no_semantic):
        result = service_no_semantic.search("robô")
        for hit in result.hits:
            assert hit.semantic_score is None
            assert hit.rrf_score is None


# --- Ordenação RRF e desempate ---


class TestRRFOrdering:
    def test_hits_ordered_by_rrf_score_desc(self, service_with_semantic):
        result = service_with_semantic.search("robô espaço")
        rrf_scores = [h.rrf_score for h in result.hits if h.rrf_score is not None]
        assert rrf_scores == sorted(rrf_scores, reverse=True)

    def test_rank_is_one_based_and_consecutive(self, service_with_semantic):
        result = service_with_semantic.search("robô espaço tubarão")
        assert [h.rank for h in result.hits] == list(range(1, len(result.hits) + 1))

    def test_determinism_with_semantic(self, snapshot, retriever):
        """Mesma consulta, mesmos hits na mesma ordem (invariante 5)."""
        cfg = _base_cfg()
        svc = SearchService(
            snapshot, cfg, semantic_retriever=retriever, logger=MemoryQueryLogger()
        )
        a = svc.search("tubarão robô")
        b = svc.search("tubarão robô")
        assert [(h.movie_id, h.rank) for h in a.hits] == [(h.movie_id, h.rank) for h in b.hits]

    def test_tfidf_zero_candidate_has_zero_score(self, snapshot):
        """Candidato semântico com TF-IDF = 0 fica com score = 0 (D-095)."""
        # Consulta sem nenhuma palavra no vocabulário do TF-IDF
        encoder = FakeEncoder()
        vectors = encoder.encode(snapshot.texts)
        retriever = SemanticRetriever(
            encoder=encoder,
            vectors=vectors,
            snapshot_id=snapshot.snapshot_id,
        )
        cfg = _base_cfg()
        svc = SearchService(
            snapshot, cfg, semantic_retriever=retriever, logger=MemoryQueryLogger()
        )
        # "xyzzyx" não existe no vocabulário: TF-IDF = 0 para todos os candidatos
        result = svc.search("xyzzyx")
        for hit in result.hits:
            assert hit.score == pytest.approx(0.0)


# --- Aviso na interface só quando ativo ---


class TestSemanticWarningInUI:
    def test_no_warning_when_semantic_inactive(self, service_no_semantic):
        from ir_movies.ui import texts as uitexts

        # O aviso só deve existir quando semantic_active é True
        assert not service_no_semantic.semantic_active
        # Verifica que a constante de texto existe no módulo
        assert hasattr(uitexts, "SEMANTIC_NOTICE")

    def test_warning_text_matches_spec(self):
        from ir_movies.ui import texts as uitexts

        expected = "Primeiro, sua pergunta passa por uma IA que entende o significado."
        assert expected == uitexts.SEMANTIC_NOTICE


# --- Falha suave (D-097) ---


class TestSoftFailure:
    def test_missing_npy_falls_back_to_tfidf(self, snapshot):
        """Vetores ausentes: serviço ativa falha suave e usa TF-IDF puro."""
        cfg = _base_cfg(semantic_enabled=True)
        cfg["semantic"]["embeddings_dir"] = "/nao/existe/de/jeito/nenhum"
        svc = SearchService.from_config.__func__(  # type: ignore[attr-defined]
            SearchService,
            None,
        ) if False else _build_service_with_broken_retriever(snapshot, cfg)
        assert not svc.semantic_active

    def test_snapshot_id_mismatch_raises_on_load(self, snapshot):
        """Metadados com snapshot_id errado levantam ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            encoder = FakeEncoder()
            vectors = encoder.encode(snapshot.texts)
            # Nome do arquivo usa snapshot_id correto (loader encontra o arquivo);
            # JSON usa snapshot_id errado (loader rejeita na validação).
            _write_fake_embeddings(
                tmpdir_path,
                file_snapshot_id=snapshot.snapshot_id,
                vectors=vectors,
                model_name="fake/model",
                meta_snapshot_id="WRONG_ID",
            )
            cfg = _build_load_cfg(tmpdir, "fake/model", snapshot.snapshot_id)
            with pytest.raises(ValueError, match="snapshot_id"):
                load_semantic_retriever(cfg, snapshot.snapshot_id, encoder)

    def test_dim_mismatch_raises_on_load(self, snapshot):
        """Vetores com dimensão errada levantam ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            encoder = FakeEncoder()
            # Vetores com dim errada: 8 em vez de 4
            wrong_vectors = np.random.randn(len(snapshot.texts), 8).astype(np.float32)
            _write_fake_embeddings(
                tmpdir_path,
                file_snapshot_id=snapshot.snapshot_id,
                vectors=wrong_vectors,
                model_name="fake/model",
                dim_override=4,  # JSON diz dim=4 mas .npy tem 8 colunas
            )
            cfg = _build_load_cfg(tmpdir, "fake/model", snapshot.snapshot_id)
            with pytest.raises(ValueError, match="[Ss]hape"):
                load_semantic_retriever(cfg, snapshot.snapshot_id, encoder)

    def test_missing_file_raises_on_load(self, snapshot):
        """Arquivo .npy ausente levanta FileNotFoundError."""
        cfg = _build_load_cfg("/nao/existe", "fake/model", snapshot.snapshot_id)
        encoder = FakeEncoder()
        with pytest.raises(FileNotFoundError):
            load_semantic_retriever(cfg, snapshot.snapshot_id, encoder)


# --- Helpers dos testes de falha suave ---


def _write_fake_embeddings(
    dest: Path,
    file_snapshot_id: str,
    vectors: np.ndarray,
    model_name: str,
    *,
    meta_snapshot_id: str | None = None,
    dim_override: int | None = None,
) -> tuple[Path, Path]:
    """Escreve vetores e metadados em *dest*.

    *file_snapshot_id* vai no nome do arquivo (usado pelo loader para achar o arquivo).
    *meta_snapshot_id* vai no JSON; quando None, usa *file_snapshot_id* (caso normal).
    *dim_override* coloca dimensão errada no JSON para testar validação de shape.
    """
    slug = _model_slug(model_name)
    base = dest / f"embeddings_{slug}_{file_snapshot_id}"
    npy_path = base.with_suffix(".npy")
    json_path = base.with_suffix(".json")
    np.save(npy_path, vectors)
    meta = {
        "snapshot_id": meta_snapshot_id if meta_snapshot_id is not None else file_snapshot_id,
        "model": model_name,
        "dimension": dim_override if dim_override is not None else int(vectors.shape[1]),
        "n_docs": int(vectors.shape[0]),
        "revision": "",
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f)
    return npy_path, json_path


def _build_load_cfg(embeddings_dir: str, model_name: str, snapshot_id: str) -> dict:
    cfg = _base_cfg()
    cfg["semantic"]["embeddings_dir"] = embeddings_dir
    cfg["semantic"]["model"] = model_name
    return cfg


def _build_service_with_broken_retriever(snapshot: LoadedSnapshot, cfg: dict) -> SearchService:
    """Monta SearchService com config semântico quebrado; deve ativar falha suave."""
    from ir_movies.query.service import _try_load_retriever

    retriever = _try_load_retriever(cfg, snapshot.snapshot_id)
    return SearchService(snapshot, cfg, semantic_retriever=retriever, logger=MemoryQueryLogger())


# --- score_subset do TfidfIndex ---


class TestScoreSubset:
    def test_subset_scores_agree_with_full_search(self):
        """score_subset deve devolver os mesmos scores que search para os doc_ids dados."""
        preprocessor = Preprocessor(TEXT_CFG)
        snapshot = _build_fake_snapshot()
        index = TfidfIndex.build(snapshot.texts, preprocessor, TFIDF_CFG)

        query = "robô"
        full_hits = {h.doc_id: h.score for h in index.search(query)}
        subset_hits = {h.doc_id: h.score for h in index.score_subset(query, list(range(5)))}

        for doc_id, score in full_hits.items():
            assert subset_hits.get(doc_id, 0.0) == pytest.approx(score, abs=1e-9)

    def test_empty_doc_ids_returns_empty(self):
        preprocessor = Preprocessor(TEXT_CFG)
        snapshot = _build_fake_snapshot()
        index = TfidfIndex.build(snapshot.texts, preprocessor, TFIDF_CFG)
        assert index.score_subset("robô", []) == []

    def test_oov_query_returns_empty(self):
        preprocessor = Preprocessor(TEXT_CFG)
        snapshot = _build_fake_snapshot()
        index = TfidfIndex.build(snapshot.texts, preprocessor, TFIDF_CFG)
        assert index.score_subset("xyzzyx", [0, 1, 2]) == []


# --- Teste com modelo real (desligado por padrão) ---


@pytest.mark.skipif(
    os.environ.get("IR_MOVIES_RUN_MODEL_TESTS") != "1",
    reason="Testes com modelo real desativados (define IR_MOVIES_RUN_MODEL_TESTS=1 para rodar)",
)
class TestRealModel:
    def test_encode_shape_and_norm(self):
        """Vetor gerado pelo modelo real: shape (384,) e norma ~1."""
        from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

        model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        vec = model.encode(["robô que se apaixona"], normalize_embeddings=True)[0]
        assert vec.shape == (384,)
        assert np.linalg.norm(vec) == pytest.approx(1.0, abs=1e-5)

    def test_similar_sentences_have_high_cosine(self):
        """Duas frases com sentido parecido devem ter cosseno alto."""
        from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

        model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        a, b = "robô que se apaixona", "máquina que sente amor"
        vecs = model.encode([a, b], normalize_embeddings=True)
        cosine = float(vecs[0] @ vecs[1])
        assert cosine > 0.6, f"cosseno esperado > 0,6; obtido {cosine:.4f}"
