"""Recommendation logic. Everything here is plain rules + MongoDB aggregation pipelines (no ML).

1. picked_for_you    content-based: score movies by how well they match the user's taste
2. fans_also_liked   collaborative: "people who liked X also liked Y" (self-join on ratings)
3. trending          most-rated movies by all users in the last 7 days
4. similar_movies    same genres / director / cast as one movie
5. taste_profile     which genres the user likes, from their own ratings
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from pymongo.database import Database

CARD_FIELDS = {"title": 1, "year": 1, "genres": 1, "poster": 1, "imdb_rating": 1, "director": 1, "runtime": 1}
LIKED = 4  # 4 or 5 stars counts as "liked"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def seen_ids(db: Database, user: dict) -> list[str]:
    """Movies the user already rated or saved. We never recommend these again."""
    rated = db.ratings.distinct("movie_id", {"user_id": user["_id"]})
    listed = [i["movie_id"] for i in user.get("my_list", [])]
    return list(set(rated) | set(listed))


def liked_movies(db: Database, user: dict, limit: int = 50) -> list[dict]:
    """Movies the user liked (4-5 stars) plus movies in their list, newest first."""
    ids = [r["movie_id"] for r in db.ratings.find({"user_id": user["_id"], "stars": {"$gte": LIKED}})
           .sort("created_at", -1).limit(limit)]
    for item in user.get("my_list", []):
        if item["movie_id"] not in ids:
            ids.append(item["movie_id"])
    movies = {m["_id"]: m for m in db.movies.find({"_id": {"$in": ids}}, {"genres": 1, "director": 1, "cast": 1, "title": 1})}
    return [movies[i] for i in ids if i in movies]


def genre_weights(user: dict, liked: list[dict]) -> dict[str, int]:
    """Favourite genres count 3 points each; every liked movie adds 1 point to each of its genres."""
    weights: Counter = Counter({g: 3 for g in user.get("favourite_genres", [])})
    for m in liked:
        weights.update(m.get("genres", []))
    return dict(weights)


# ---------------------------------------------------------------------------
# 1. Content-based: "Picked for you"
# ---------------------------------------------------------------------------
def picked_for_you_pipeline(weights: dict[str, int], directors: list[str], cast: list[str],
                            exclude: list[str], limit: int) -> list[dict]:
    top_genres = [g for g, _ in sorted(weights.items(), key=lambda kv: -kv[1])[:6]]
    genre_score = {"$add": [{"$cond": [{"$in": [g, "$genres"]}, w, 0]} for g, w in weights.items()] or [0]}
    return [
        # Only movies in the user's main genres that they have not seen (uses the genres index).
        {"$match": {"genres": {"$in": top_genres}, "_id": {"$nin": exclude}}},
        {"$addFields": {
            "matched_genres": {"$setIntersection": ["$genres", top_genres]},
            "genre_score": genre_score,
            "same_director": {"$in": ["$director", directors]},
            "shared_cast": {"$setIntersection": ["$cast", cast]},
        }},
        {"$addFields": {"score": {"$add": [
            "$genre_score",                                             # taste match
            {"$cond": ["$same_director", 4, 0]},                        # liked this director before
            {"$multiply": [{"$min": [{"$size": "$shared_cast"}, 3]}, 2]},  # liked these actors before
            {"$multiply": [{"$subtract": ["$imdb_rating", 6]}, 2]},     # quality bonus
        ]}}},
        {"$sort": {"score": -1, "imdb_votes": -1}},
        {"$limit": limit},
        {"$project": {**CARD_FIELDS, "score": 1, "matched_genres": 1, "same_director": 1, "shared_cast": 1}},
    ]


def picked_for_you(db: Database, user: dict, limit: int = 12) -> list[dict]:
    liked = liked_movies(db, user)
    weights = genre_weights(user, liked)
    if not weights:
        return []
    director_from = {}
    for m in liked:
        if m.get("director"):
            director_from.setdefault(m["director"], m["title"])
    cast_counts = Counter(a for m in liked for a in m.get("cast", [])[:4])
    cast = [a for a, _ in cast_counts.most_common(30)]
    pipeline = picked_for_you_pipeline(weights, list(director_from), cast, seen_ids(db, user), limit)
    out = []
    for m in db.movies.aggregate(pipeline):
        reasons = []
        if m["matched_genres"]:
            reasons.append("Matches your taste: " + ", ".join(m["matched_genres"]))
        if m["same_director"]:
            reasons.append(f"Same director as {director_from[m['director']]} ({m['director']})")
        if m["shared_cast"]:
            reasons.append("Stars " + ", ".join(m["shared_cast"][:2]) + ", who you have liked before")
        reasons.append(f"IMDb {m['imdb_rating']}")
        m["reasons"] = reasons
        m["score"] = round(m["score"], 1)
        out.append(m)
    return out


# ---------------------------------------------------------------------------
# 2. Collaborative: "People who liked X also liked"
# ---------------------------------------------------------------------------
def fans_also_liked_pipeline(movie_id: str, exclude: list[str], exclude_user, limit: int) -> list[dict]:
    return [
        # a) everyone (except me) who liked movie X
        {"$match": {"movie_id": movie_id, "stars": {"$gte": LIKED}, "user_id": {"$ne": exclude_user}}},
        # b) self-join: fetch every other movie those same users liked
        {"$lookup": {
            "from": "ratings",
            "localField": "user_id",
            "foreignField": "user_id",
            "pipeline": [{"$match": {"stars": {"$gte": LIKED}}}, {"$project": {"movie_id": 1, "stars": 1}}],
            "as": "their_likes",
        }},
        {"$unwind": "$their_likes"},
        {"$match": {"their_likes.movie_id": {"$nin": exclude + [movie_id]}}},
        # c) count how many of those fans liked each movie
        {"$group": {"_id": "$their_likes.movie_id", "fans": {"$sum": 1}, "avg_stars": {"$avg": "$their_likes.stars"}}},
        {"$match": {"fans": {"$gte": 2}}},
        {"$sort": {"fans": -1, "avg_stars": -1, "_id": 1}},
        {"$limit": limit},
        # d) join the movie details for the cards
        {"$lookup": {"from": "movies", "localField": "_id", "foreignField": "_id", "as": "movie",
                     "pipeline": [{"$project": CARD_FIELDS}]}},
        {"$unwind": "$movie"},
    ]


def fans_also_liked(db: Database, movie_id: str, exclude: list[str] | None = None, exclude_user=None,
                    limit: int = 10) -> list[dict]:
    fans = db.ratings.count_documents({"movie_id": movie_id, "stars": {"$gte": LIKED}})
    out = []
    for r in db.ratings.aggregate(fans_also_liked_pipeline(movie_id, exclude or [], exclude_user, limit)):
        m = r["movie"]
        m["fans"] = r["fans"]
        m["avg_stars"] = round(r["avg_stars"], 1)
        m["reasons"] = [f"{r['fans']} of the {fans} people who liked this also liked it"]
        out.append(m)
    return out


def because_you_liked(db: Database, user: dict, limit: int = 10) -> dict | None:
    """Pick the user's most recent liked movie that has enough fans, and run the collaborative query."""
    exclude = seen_ids(db, user)
    for seed in liked_movies(db, user, limit=10):
        items = fans_also_liked(db, seed["_id"], exclude, user["_id"], limit)
        if len(items) >= 3:
            return {"seed": {"id": seed["_id"], "title": seed["title"]}, "items": items}
    return None


# ---------------------------------------------------------------------------
# 3. Trending
# ---------------------------------------------------------------------------
def trending_pipeline(since: datetime, limit: int) -> list[dict]:
    return [
        {"$match": {"created_at": {"$gte": since}}},
        {"$group": {"_id": "$movie_id", "ratings": {"$sum": 1}, "avg_stars": {"$avg": "$stars"}}},
        {"$match": {"ratings": {"$gte": 2}}},
        {"$sort": {"ratings": -1, "avg_stars": -1, "_id": 1}},
        {"$limit": limit},
        {"$lookup": {"from": "movies", "localField": "_id", "foreignField": "_id", "as": "movie",
                     "pipeline": [{"$project": CARD_FIELDS}]}},
        {"$unwind": "$movie"},
    ]


def trending(db: Database, days: int = 7, limit: int = 10) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    out = []
    for r in db.ratings.aggregate(trending_pipeline(since, limit)):
        m = r["movie"]
        m["reasons"] = [f"{r['ratings']} ratings this week, average {r['avg_stars']:.1f} stars"]
        out.append(m)
    return out


# ---------------------------------------------------------------------------
# 4. Similar movies (content)
# ---------------------------------------------------------------------------
def similar_movies(db: Database, movie: dict, limit: int = 8) -> list[dict]:
    pipeline = [
        {"$match": {"_id": {"$ne": movie["_id"]},
                    "$or": [{"genres": {"$in": movie["genres"]}}, {"director": movie.get("director")}]}},
        {"$addFields": {
            "shared_genres": {"$setIntersection": ["$genres", movie["genres"]]},
            "same_director": {"$eq": ["$director", movie.get("director")]},
            "shared_cast": {"$setIntersection": ["$cast", movie.get("cast", [])]},
        }},
        {"$addFields": {"score": {"$add": [
            {"$multiply": [{"$size": "$shared_genres"}, 2]},
            {"$cond": ["$same_director", 4, 0]},
            {"$multiply": [{"$size": "$shared_cast"}, 2]},
            {"$divide": ["$imdb_rating", 2]},
        ]}}},
        {"$sort": {"score": -1, "imdb_votes": -1}},
        {"$limit": limit},
        {"$project": {**CARD_FIELDS, "shared_genres": 1, "same_director": 1, "shared_cast": 1}},
    ]
    out = []
    for m in db.movies.aggregate(pipeline):
        reasons = []
        if m["same_director"]:
            reasons.append(f"Also directed by {m['director']}")
        if m["shared_cast"]:
            reasons.append("Also stars " + ", ".join(m["shared_cast"][:2]))
        if m["shared_genres"]:
            reasons.append("Shared genres: " + ", ".join(m["shared_genres"]))
        m["reasons"] = reasons
        out.append(m)
    return out


# ---------------------------------------------------------------------------
# 5. Taste profile and top picks per genre
# ---------------------------------------------------------------------------
def taste_profile(db: Database, user: dict) -> list[dict]:
    pipeline = [
        {"$match": {"user_id": user["_id"]}},
        {"$lookup": {"from": "movies", "localField": "movie_id", "foreignField": "_id", "as": "m",
                     "pipeline": [{"$project": {"genres": 1}}]}},
        {"$unwind": "$m"},
        {"$unwind": "$m.genres"},
        {"$group": {"_id": "$m.genres", "rated": {"$sum": 1}, "avg_stars": {"$avg": "$stars"},
                    "liked": {"$sum": {"$cond": [{"$gte": ["$stars", LIKED]}, 1, 0]}}}},
        {"$sort": {"liked": -1, "avg_stars": -1}},
    ]
    return [{"genre": r["_id"], "rated": r["rated"], "liked": r["liked"], "avg_stars": round(r["avg_stars"], 1)}
            for r in db.ratings.aggregate(pipeline)]


def top_in_genre(db: Database, genre: str, exclude: list[str], limit: int = 10) -> list[dict]:
    cur = (db.movies.find({"genres": genre, "_id": {"$nin": exclude}}, CARD_FIELDS)
           .sort([("imdb_rating", -1), ("imdb_votes", -1)]).limit(limit))
    return [{**m, "reasons": [f"Top rated {genre} movie (IMDb {m['imdb_rating']})"]} for m in cur]
