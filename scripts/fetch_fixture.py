"""Baixa uma resposta da TMDB e salva em tests/fixtures/. Rodar uma única vez.

Uso:
    python scripts/fetch_fixture.py

O script lê TMDB_READ_ACCESS_TOKEN do .env (via python-dotenv).
O token NÃO é salvo no JSON resultante — só vai no header HTTP.
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = ROOT / "tests" / "fixtures"
MOVIE_ID = 278  # "Um Sonho de Liberdade" (The Shawshank Redemption)

EXPECTED_KEYS = {"id", "title", "overview", "genres", "credits", "keywords"}


def load_token() -> str:
    """Carrega o token do .env ou variável de ambiente."""
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    token = os.environ.get("TMDB_READ_ACCESS_TOKEN")
    if not token:
        print("TMDB_READ_ACCESS_TOKEN não encontrado no .env nem nas variáveis de ambiente.")
        token = input("Cole o token aqui: ").strip()
    return token


def fetch_movie(token: str, movie_id: int) -> dict:
    """Busca detalhes do filme na TMDB."""
    url = (
        f"https://api.themoviedb.org/3/movie/{movie_id}"
        f"?language=pt-BR&append_to_response=credits,keywords"
    )
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def analyze(data: dict) -> None:
    """Exibe um resumo da resposta para conferência manual."""
    print(f"\n{'=' * 60}")
    print("ANÁLISE DA RESPOSTA")
    print(f"{'=' * 60}")

    print(f"\nID:              {data.get('id')}")
    print(f"Título PT-BR:    {data.get('title')}")
    print(f"Título original: {data.get('original_title')}")
    print(f"Tagline:         {data.get('tagline')}")
    print(f"Data lançamento: {data.get('release_date')}")
    print(f"Duração:         {data.get('runtime')} min")
    print(f"Nota média:      {data.get('vote_average')}")
    print(f"Nº de votos:     {data.get('vote_count')}")
    print(f"Popularidade:    {data.get('popularity')}")
    print(f"Poster path:     {data.get('poster_path')}")

    overview = data.get("overview", "")
    print(f"\nSinopse ({len(overview.split())} palavras):")
    print(f"  {overview[:200]}{'...' if len(overview) > 200 else ''}")

    genres = [g["name"] for g in data.get("genres", [])]
    print(f"\nGêneros: {', '.join(genres)}")

    keywords = [k["name"] for k in data.get("keywords", {}).get("keywords", [])]
    suffix = "..." if len(keywords) > 10 else ""
    print(f"Keywords ({len(keywords)}): {', '.join(keywords[:10])}{suffix}")

    cast = data.get("credits", {}).get("cast", [])
    print(f"Elenco (top 5): {', '.join(c['name'] for c in cast[:5])}")

    crew = data.get("credits", {}).get("crew", [])
    directors = [c["name"] for c in crew if c.get("job") == "Director"]
    print(f"Diretor(es):     {', '.join(directors)}")

    missing = EXPECTED_KEYS - set(data.keys())
    if missing:
        print(f"\n⚠ Chaves esperadas AUSENTES: {missing}")
    else:
        print(f"\n✓ Todas as chaves esperadas presentes: {EXPECTED_KEYS}")

    print(f"\nTotal de chaves no JSON: {len(data)}")
    print(f"{'=' * 60}")


def main() -> None:
    token = load_token()

    print(f"Buscando filme {MOVIE_ID} na TMDB...")
    try:
        data = fetch_movie(token, MOVIE_ID)
    except urllib.error.HTTPError as e:
        print(f"Erro HTTP {e.code}: {e.reason}", file=sys.stderr)
        sys.exit(1)

    analyze(data)

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    out = FIXTURES_DIR / f"movie_{MOVIE_ID}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    size_kb = out.stat().st_size / 1024
    print(f"\nSalvo em {out.relative_to(ROOT)} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
