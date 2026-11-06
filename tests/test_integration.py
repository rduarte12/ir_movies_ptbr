"""Integração ponta a ponta: consulta -> resultado -> linha de log (D-090).

Usa o serviço **real** (``SearchService.from_config``) sobre o acervo mínimo de
``tests/fixtures/mini_snapshot/`` e a tela montada por ``build_app``. Os eventos
são disparados pelos mesmos manipuladores que o Gradio chama no navegador. O log
vai sempre para ``tmp_path``: nunca para o ``logs/`` do repositório.
"""

import json
from pathlib import Path

import gradio as gr
import pytest
import yaml

from ir_movies.config import load_config
from ir_movies.logging_jsonl import new_session_id
from ir_movies.query.service import SearchService
from ir_movies.ui.app import build_app

MINI_SNAPSHOT_DIR = Path(__file__).resolve().parent / "fixtures" / "mini_snapshot"


@pytest.fixture
def cfg(tmp_path):
    """Configuração do projeto, com o log redirecionado para a pasta temporária."""
    cfg = load_config()
    cfg["logging"] = {"dir": str(tmp_path / "logs"), "enabled": True}
    return cfg


@pytest.fixture
def service(cfg, tmp_path):
    """Serviço real sobre o acervo mínimo, montado pelo caminho de produção."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return SearchService.from_config(config_path, data_dir=MINI_SNAPSHOT_DIR)


def wired_fn(demo: gr.Blocks, name: str):
    found = [fn for fn in demo.fns.values() if getattr(fn.fn, "__name__", "") == name]
    assert found, f"nenhum evento registrado com o manipulador {name}"
    return found[0]


def read_log(tmp_path) -> list[dict]:
    files = sorted((tmp_path / "logs").glob("queries-*.jsonl"))
    assert len(files) == 1, files
    return [json.loads(line) for line in files[0].read_text(encoding="utf-8").splitlines()]


def test_search_then_click_writes_two_log_lines(service, cfg, tmp_path):
    demo = build_app(service, cfg)
    gallery = next(b for b in demo.blocks.values() if isinstance(b, gr.Gallery))
    session_id = new_session_id()
    query = cfg["ui"]["examples"][0]

    # 1. Busca pelo manipulador que o Gradio liga ao botão.
    result = wired_fn(demo, "on_search").fn(query, session_id)[-1]
    assert len(result.hits) >= 2, "o acervo mínimo deve responder à consulta de exemplo"

    first_line = read_log(tmp_path)
    assert len(first_line) == 1
    search_event = first_line[0]
    assert search_event["event"] == "search"
    assert search_event["session_id"] == session_id
    assert search_event["raw_query"] == query
    assert search_event["snapshot_id"] == service.snapshot_id
    assert search_event["n_results"] == len(result.hits)
    assert search_event["top_ids"] == [hit.movie_id for hit in result.hits]

    # 2. Clique no segundo pôster, também pelo manipulador do Gradio.
    event_data = gr.SelectData(target=gallery, data={"index": 1, "value": None, "selected": True})
    wired_fn(demo, "on_select").fn(session_id, result, event_data)

    lines = read_log(tmp_path)
    assert len(lines) == 2
    assert lines[0] == search_event
    click_event = lines[1]
    assert click_event["event"] == "click"
    assert click_event["session_id"] == session_id
    assert click_event["movie_id"] == result.hits[1].movie_id
    assert click_event["rank"] == 2


def test_log_stays_inside_the_temporary_folder(service, cfg, tmp_path):
    """O serviço montado pela configuração grava só onde a configuração mandou."""
    service.search(cfg["ui"]["examples"][0], session_id=new_session_id())

    assert [p.parent for p in (tmp_path / "logs").glob("queries-*.jsonl")] == [tmp_path / "logs"]
