"""Collection-wide statistics, each one a MongoDB aggregation pipeline (good for the viva)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from ..db import get_db

router = APIRouter(tags=["insights"])


def pipelines():
    since = datetime.now(timezone.utc) - timedelta(days=14)
    return {
        "genres": ("movies", [
            {"$unwind": "$genres"},
            {"$group": {"_id": "$genres", "movies": {"$sum": 1}, "avg_rating": {"$avg": "$imdb_rating"}}},
            {"$sort": {"movies": -1}},
        ]),
        "decades": ("movies", [
            {"$group": {"_id": {"$multiply": [{"$floor": {"$divide": ["$year", 10]}}, 10]},
                        "movies": {"$sum": 1}, "avg_rating": {"$avg": "$imdb_rating"}}},
            {"$sort": {"_id": 1}},
        ]),
        "rating_buckets": ("movies", [
            {"$bucket": {"groupBy": "$imdb_rating", "boundaries": [0, 5, 6, 7, 8, 9, 10.1], "default": "other",
                         "output": {"movies": {"$sum": 1}}}},
        ]),
        "top_directors": ("movies", [
            {"$match": {"director": {"$ne": None}}},
            {"$group": {"_id": "$director", "movies": {"$sum": 1}, "avg_rating": {"$avg": "$imdb_rating"},
                        "titles": {"$push": "$title"}}},
            {"$match": {"movies": {"$gte": 3}}},
            {"$sort": {"avg_rating": -1}},
            {"$limit": 10},
            {"$project": {"movies": 1, "avg_rating": 1, "titles": {"$slice": ["$titles", 4]}}},
        ]),
        "ratings_per_day": ("ratings", [
            {"$match": {"created_at": {"$gte": since}}},
            {"$group": {"_id": {"$dateTrunc": {"date": "$created_at", "unit": "day"}}, "ratings": {"$sum": 1},
                        "avg_stars": {"$avg": "$stars"}}},
            {"$sort": {"_id": 1}},
        ]),
        "most_loved": ("ratings", [
            {"$group": {"_id": "$movie_id", "ratings": {"$sum": 1}, "avg_stars": {"$avg": "$stars"}}},
            {"$match": {"ratings": {"$gte": 5}}},
            {"$sort": {"avg_stars": -1, "ratings": -1}},
            {"$limit": 10},
            {"$lookup": {"from": "movies", "localField": "_id", "foreignField": "_id", "as": "movie",
                         "pipeline": [{"$project": {"title": 1, "year": 1}}]}},
            {"$unwind": "$movie"},
        ]),
    }


def _round(doc):
    return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in doc.items()}


@router.get("/insights")
def insights():
    db = get_db()
    out = {name: [_round(r) for r in db[coll].aggregate(p)] for name, (coll, p) in pipelines().items()}
    out["counts"] = {c: db[c].estimated_document_count() for c in ("movies", "users", "ratings", "sessions")}
    return out


@router.get("/insights/pipelines")
def show_pipelines():
    """The raw pipelines, so you can show them in class."""
    return {name: {"collection": coll, "pipeline": p} for name, (coll, p) in pipelines().items()}
