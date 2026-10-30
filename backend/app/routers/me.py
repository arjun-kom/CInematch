from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from ..auth import current_user, public_user
from ..db import get_db
from ..errors import ApiError
from ..recommend import (CARD_FIELDS, because_you_liked, picked_for_you, seen_ids, taste_profile, top_in_genre,
                         trending)
from ..schemas import ListItem, Onboarding, Preferences, RatingIn
from ..serialize import clean

router = APIRouter(prefix="/me", tags=["my account"])


def _valid_genres(db, genres: list[str]) -> list[str]:
    known = set(db.movies.distinct("genres"))
    bad = [g for g in genres if g not in known]
    if bad:
        raise ApiError(400, "unknown_genre", f"Unknown genre(s): {', '.join(bad)}")
    return list(dict.fromkeys(genres))


def _check_movie(db, movie_id: str) -> None:
    if not db.movies.count_documents({"_id": movie_id}, limit=1):
        raise ApiError(404, "not_found", f"Movie '{movie_id}' was not found.")


@router.post("/onboarding")
def onboarding(body: Onboarding, user: dict = Depends(current_user)):
    """Step 1 + 2 of sign-up: favourite genres and the movies the user is interested in."""
    db = get_db()
    genres = _valid_genres(db, body.genres)
    ids = list(dict.fromkeys(body.movie_ids))
    found = set(db.movies.distinct("_id", {"_id": {"$in": ids}}))
    now = datetime.now(timezone.utc)
    have = {i["movie_id"] for i in user.get("my_list", [])}
    new_items = [{"movie_id": m, "added_at": now} for m in ids if m in found and m not in have]
    db.users.update_one({"_id": user["_id"]}, {
        "$set": {"favourite_genres": genres, "onboarded": True},
        "$push": {"my_list": {"$each": new_items, "$position": 0}},
    })
    return public_user(db.users.find_one({"_id": user["_id"]}))


@router.put("/preferences")
def preferences(body: Preferences, user: dict = Depends(current_user)):
    db = get_db()
    db.users.update_one({"_id": user["_id"]}, {"$set": {"favourite_genres": _valid_genres(db, body.favourite_genres)}})
    return public_user(db.users.find_one({"_id": user["_id"]}))


# ---- My list (embedded array inside the user document) ---------------------
@router.get("/list")
def my_list(user: dict = Depends(current_user)):
    db = get_db()
    items = user.get("my_list", [])
    movies = {m["_id"]: m for m in db.movies.find({"_id": {"$in": [i["movie_id"] for i in items]}}, CARD_FIELDS)}
    return clean([{**movies[i["movie_id"]], "added_at": i["added_at"]} for i in items if i["movie_id"] in movies])


@router.post("/list", status_code=201)
def add_to_list(body: ListItem, user: dict = Depends(current_user)):
    db = get_db()
    _check_movie(db, body.movie_id)
    # The filter only matches if the movie is NOT already in the list, so there are no duplicates.
    db.users.update_one(
        {"_id": user["_id"], "my_list.movie_id": {"$ne": body.movie_id}},
        {"$push": {"my_list": {"$each": [{"movie_id": body.movie_id, "added_at": datetime.now(timezone.utc)}],
                               "$position": 0}}},
    )
    return {"ok": True}


@router.delete("/list/{movie_id}")
def remove_from_list(movie_id: str, user: dict = Depends(current_user)):
    get_db().users.update_one({"_id": user["_id"]}, {"$pull": {"my_list": {"movie_id": movie_id}}})
    return {"ok": True}


# ---- Ratings (separate collection: many per user, needed for "people also liked") ----
@router.get("/ratings")
def my_ratings(user: dict = Depends(current_user)):
    pipeline = [
        {"$match": {"user_id": user["_id"]}},
        {"$sort": {"created_at": -1}},
        {"$lookup": {"from": "movies", "localField": "movie_id", "foreignField": "_id", "as": "movie",
                     "pipeline": [{"$project": CARD_FIELDS}]}},
        {"$unwind": "$movie"},
        {"$project": {"_id": 0, "stars": 1, "created_at": 1, "movie": 1}},
    ]
    return clean(list(get_db().ratings.aggregate(pipeline)))


@router.put("/ratings/{movie_id}")
def rate(movie_id: str, body: RatingIn, user: dict = Depends(current_user)):
    db = get_db()
    _check_movie(db, movie_id)
    # Upsert: insert the rating the first time, update it after that (unique index on user+movie).
    db.ratings.update_one({"user_id": user["_id"], "movie_id": movie_id},
                          {"$set": {"stars": body.stars, "created_at": datetime.now(timezone.utc)}}, upsert=True)
    return {"ok": True, "stars": body.stars}


@router.delete("/ratings/{movie_id}")
def unrate(movie_id: str, user: dict = Depends(current_user)):
    get_db().ratings.delete_one({"user_id": user["_id"], "movie_id": movie_id})
    return {"ok": True}


# ---- Dashboard ----------------------------------------------------------------
@router.get("/dashboard")
def dashboard(user: dict = Depends(current_user)):
    db = get_db()
    exclude = seen_ids(db, user)
    fav = user.get("favourite_genres", [])
    return clean({
        "user": public_user(user),
        "my_list": my_list(user),
        "picked_for_you": picked_for_you(db, user),
        "because_you_liked": because_you_liked(db, user),
        "trending": trending(db),
        "top_in_genre": {"genre": fav[0], "items": top_in_genre(db, fav[0], exclude)} if fav else None,
        "taste": taste_profile(db, user),
        "stats": {"rated": db.ratings.count_documents({"user_id": user["_id"]}),
                  "in_list": len(user.get("my_list", []))},
    })
