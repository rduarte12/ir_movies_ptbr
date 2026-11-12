"""Monta a apresentação num único arquivo HTML autocontido.

Junta ``site/src/`` (HTML, CSS e JavaScript), os dados de ``site/data/presentation.json``
(gerados por ``export_presentation_data.py``), o pôster reserva da interface e um QR code.
O resultado, ``site/dist/index.html``, não depende de servidor: abre direto do disco ou de
qualquer hospedagem estática. Só os pôsteres vêm da internet (servidor de imagens da TMDB).

Uso::

    python scripts/build_presentation.py

Requer o pacote ``qrcode`` (só para gerar o QR; a página final não usa biblioteca nenhuma).
"""

from __future__ import annotations

import base64
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "site" / "src"
DATA = ROOT / "site" / "data" / "presentation.json"
OUT = ROOT / "site" / "dist" / "index.html"
PLACEHOLDER = ROOT / "src" / "ir_movies" / "ui" / "assets" / "no_poster.svg"
PUBLIC_URL = "https://rmduarte.com.br/feira/filmusp/"
MAX_BYTES = 2 * 1024 * 1024


def qr_svg(text: str) -> str:
    """QR code como SVG embutido (caminho único, sem dependência na página)."""
    import qrcode
    import qrcode.image.svg

    img = qrcode.make(
        text,
        image_factory=qrcode.image.svg.SvgPathImage,
        border=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
    )
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode("utf-8")
    svg = svg[svg.index("<svg") :]
    return svg.replace("<svg ", '<svg role="img" aria-label="QR code da apresentação" ', 1)


def safe_json(payload: dict) -> str:
    """JSON seguro dentro de <script>: nenhum '</' pode fechar a tag antes da hora."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def main() -> int:
    payload = json.loads(DATA.read_text("utf-8"))
    html = (SRC / "index.html").read_text("utf-8")
    css = (SRC / "style.css").read_text("utf-8")
    js = (SRC / "app.js").read_text("utf-8")
    placeholder = (
        "data:image/svg+xml;base64," + base64.b64encode(PLACEHOLDER.read_bytes()).decode()
    )

    replacements = {
        "/*__UI_CSS__*/": payload["ui_css"],
        "/*__PRESENTATION_CSS__*/": css,
        "/*__QR_SVG__*/": qr_svg(PUBLIC_URL),
        "__PLACEHOLDER_URI__": placeholder,
        "__DATA_JSON__": safe_json(payload),
        "/*__PRESENTATION_JS__*/": js,
    }
    for key, value in replacements.items():
        if html.count(key) != 1:
            print(f"ERRO: marcador {key} deve aparecer uma vez no modelo", file=sys.stderr)
            return 1
        html = html.replace(key, value)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8", newline="\n")
    size = OUT.stat().st_size
    print(f"OK: {OUT.relative_to(ROOT)} ({size / 1024:.0f} KB)")
    if size > MAX_BYTES:
        print("AVISO: arquivo acima de 2 MB", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
