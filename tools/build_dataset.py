"""Build backend/data/movies.json from public movie datasets.

Sources (downloaded from GitHub because they are freely available):
  1. IMDB-Movie-Data.csv - 1,000 popular IMDb movies 2006-2016 (title, genres, director,
     actors, IMDb rating, votes, runtime, revenue, metascore, description).
  2. imdb_1000.csv - top-rated IMDb movies (used to add classics from before 2006).
  3. prust/wikipedia-movie-data - Wikipedia data: poster thumbnail, year, cast, genres, summary.

Run (needs internet):  python tools/build_dataset.py
"""
import csv
import io
import json
import re
import urllib.request
from pathlib import Path

URLS = {
    "imdb": "https://raw.githubusercontent.com/LearnDataSci/articles/master/Python%20Pandas%20Tutorial%20A%20Complete%20Introduction%20for%20Beginners/IMDB-Movie-Data.csv",
    "top": "https://raw.githubusercontent.com/justmarkham/pandas-videos/master/data/imdb_1000.csv",
    "wiki": "https://raw.githubusercontent.com/prust/wikipedia-movie-data/master/movies.json",
}
OUT = Path(__file__).resolve().parent.parent / "backend" / "data" / "movies.json"

GENRE_MAP = {"Science Fiction": "Sci-Fi", "Animated": "Animation", "Historical": "History", "Sports": "Sport",
             "Spy": "Thriller", "Suspense": "Thriller", "Superhero": "Action", "Martial Arts": "Action",
             "Film-Noir": "Crime", "Noir": "Crime", "Musical": "Music"}
VALID = {"Action", "Adventure", "Animation", "Biography", "Comedy", "Crime", "Drama", "Family", "Fantasy",
         "History", "Horror", "Music", "Mystery", "Romance", "Sci-Fi", "Sport", "Thriller", "War", "Western"}


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read().decode("utf-8")


def norm(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", t.lower())


def slug(title: str, year: int) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") + f"-{year}"


def genres(values) -> list[str]:
    out = []
    for g in values:
        g = GENRE_MAP.get(g.strip(), g.strip())
        if g in VALID and g not in out:
            out.append(g)
    return out


def short(text: str, limit: int = 320) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text or "")
    out = ""
    for s in sentences:
        if len(out) + len(s) > limit:
            break
        out += (" " if out else "") + s
    return out or (text or "")[:limit]


def main():
    imdb = list(csv.DictReader(io.StringIO(fetch(URLS["imdb"]))))
    top = list(csv.DictReader(io.StringIO(fetch(URLS["top"]))))
    wiki = json.loads(fetch(URLS["wiki"]))
    by_title: dict[str, list[dict]] = {}
    for w in wiki:
        by_title.setdefault(norm(w["title"]), []).append(w)

    def wiki_match(title, year=None, actors=()):
        cands = by_title.get(norm(title), [])
        if year:
            cands = [c for c in cands if abs(c["year"] - year) <= 1]
        if actors:
            scored = [(len(set(actors) & set(c.get("cast", []))), c) for c in cands]
            scored = [s for s in scored if s[0] > 0]
            return max(scored, key=lambda s: s[0])[1] if scored else None
        return cands[0] if cands else None

    movies, seen = [], set()
    for r in imdb:
        year = int(r["Year"])
        actors = [a.strip() for a in r["Actors"].split(",")]
        w = wiki_match(r["Title"], year)
        mid = slug(r["Title"], year)
        if mid in seen:
            continue
        seen.add(mid)
        movies.append({
            "_id": mid, "title": r["Title"], "year": year,
            "genres": genres(r["Genre"].split(",")),
            "director": r["Director"], "cast": actors,
            "runtime": int(r["Runtime (Minutes)"]),
            "imdb_rating": float(r["Rating"]), "imdb_votes": int(r["Votes"]),
            "metascore": int(r["Metascore"]) if r["Metascore"] else None,
            "revenue_musd": float(r["Revenue (Millions)"]) if r["Revenue (Millions)"] else None,
            "description": r["Description"],
            "poster": (w or {}).get("thumbnail"),
            "wiki": f"https://en.wikipedia.org/wiki/{w['href']}" if w and w.get("href") else None,
        })

    for r in top:  # classics before 2006
        if float(r["star_rating"]) < 7.8:
            continue
        actors = re.findall(r"u?['\"](.+?)['\"]", r["actors_list"])
        w = wiki_match(r["title"], actors=actors)
        if not w or w["year"] >= 2006:
            continue
        mid = slug(r["title"], w["year"])
        if mid in seen:
            continue
        seen.add(mid)
        director = re.search(r"directed by ([A-Z][\w.'-]+(?: [A-Z][\w.'-]+){0,3})", w.get("extract", ""))
        movies.append({
            "_id": mid, "title": r["title"], "year": w["year"],
            "genres": genres([r["genre"]] + w.get("genres", [])),
            "director": director.group(1) if director else None, "cast": actors,
            "runtime": int(r["duration"]), "imdb_rating": float(r["star_rating"]), "imdb_votes": None,
            "metascore": None, "revenue_musd": None, "certificate": r["content_rating"] or None,
            "description": short(w.get("extract", "")),
            "poster": w.get("thumbnail"),
            "wiki": f"https://en.wikipedia.org/wiki/{w['href']}" if w.get("href") else None,
        })

    movies = [m for m in movies if m["genres"]]
    movies.sort(key=lambda m: (-m["imdb_rating"], m["title"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(movies, ensure_ascii=False, indent=0))
    print(f"Wrote {len(movies)} movies ({sum(1 for m in movies if m['poster'])} with posters) to {OUT}")


if __name__ == "__main__":
    main()
