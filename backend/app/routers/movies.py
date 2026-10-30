from fastapi import APIRouter, Depends, Query

from ..auth import current_user
from ..db import get_db
from ..errors import ApiError
from ..recommend import CARD_FIELDS, fans_also_liked, similar_movies
from ..serialize import clean

router = APIRouter(tags=["movies"])

SORTS = {
    "popular": [("imdb_votes", -1), ("imdb_rating", -1)],
    "rating": [("imdb_rating", -1), ("imdb_votes", -1)],
    "newest": [("year", -1), ("imdb_rating", -1)],
    "oldest": [("year", 1), ("imdb_rating", -1)],
}


@router.get("/genres")
def genres():
    """Every genre with how many movies it has and their average IMDb rating ($unwind + $group)."""
    pipeline = [
        {"$unwind": "$genres"},
        {"$group": {"_id": "$genres", "movies": {"$sum": 1}, "avg_rating": {"$avg": "$imdb_rating"}}},
        {"$sort": {"movies": -1}},
    ]
    return [{"genre": r["_id"], "movies": r["movies"], "avg_rating": round(r["avg_rating"], 2)}
            for r in get_db().movies.aggregate(pipeline)]


@router.get("/movies")
def search_movies(
    q: str | None = Query(default=None, max_length=100, description="words to search (text index)"),
    genre: list[str] = Query(default=[]),
    year_from: int | None = Query(default=None, ge=1900, le=2100),
    year_to: int | None = Query(default=None, ge=1900, le=2100),
    min_rating: float | None = Query(default=None, ge=0, le=10),
    sort: str = Query(default="popular", pattern="^(popular|rating|newest|oldest|relevance)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=60),
):
    query: dict = {}
    if q and q.strip():
        query["$text"] = {"$search": q.strip()}
    if genre:
        query["genres"] = {"$in": genre}
    if year_from or year_to:
        query["year"] = {k: v for k, v in (("$gte", year_from), ("$lte", year_to)) if v}
    if min_rating is not None:
        query["imdb_rating"] = {"$gte": min_rating}
    projection = dict(CARD_FIELDS)
    db = get_db()
    if "$text" in query and sort in ("relevance", "popular"):
        projection["relevance"] = {"$meta": "textScore"}
        cursor = db.movies.find(query, projection).sort([("relevance", {"$meta": "textScore"})])
    else:
        cursor = db.movies.find(query, projection).sort(SORTS.get(sort, SORTS["popular"]))
    total = db.movies.count_documents(query)
    items = list(cursor.skip((page - 1) * page_size).limit(page_size))
    return {"total": total, "page": page, "page_size": page_size, "items": clean(items)}


@router.get("/movies/{movie_id}")
def movie_detail(movie_id: str, user: dict = Depends(current_user)):
    db = get_db()
    movie = db.movies.find_one({"_id": movie_id})
    if not movie:
        raise ApiError(404, "not_found", f"Movie '{movie_id}' was not found.")
    stats = list(db.ratings.aggregate([
        {"$match": {"movie_id": movie_id}},
        {"$group": {"_id": "$stars", "n": {"$sum": 1}}},
    ]))
    counts = {s: 0 for s in range(1, 6)}
    counts.update({r["_id"]: r["n"] for r in stats})
    total = sum(counts.values())
    mine = db.ratings.find_one({"user_id": user["_id"], "movie_id": movie_id})
    return clean({
        "movie": movie,
        "community": {"ratings": total,
                      "avg_stars": round(sum(s * n for s, n in counts.items()) / total, 2) if total else None,
                      "distribution": counts},
        "my_stars": mine["stars"] if mine else None,
        "in_my_list": any(i["movie_id"] == movie_id for i in user.get("my_list", [])),
        "similar": similar_movies(db, movie),
        "fans_also_liked": fans_also_liked(db, movie_id, exclude_user=user["_id"], limit=8),
    })
