"""Demo users so that "people who liked X also liked Y" and "Trending" have data on day one.

The 60 demo users and their ratings are made up (deterministic, seed 7); the movies are real.
A ready-made account for presenting: username `demo`, password `demo1234`.
"""
import random
from datetime import datetime, timedelta, timezone

from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from .auth import hash_password

TASTES = [
    ["Sci-Fi", "Adventure"], ["Action", "Thriller"], ["Comedy", "Romance"], ["Horror", "Mystery"],
    ["Animation", "Family"], ["Drama", "Biography"], ["Crime", "Thriller"], ["Fantasy", "Adventure"],
    ["Drama", "Romance"], ["Action", "Sci-Fi"], ["Crime", "Drama"], ["Comedy", "Animation"],
]
DEMO_LIST = ["inception-2010", "interstellar-2014", "the-dark-knight-2008", "the-martian-2015",
             "mad-max-fury-road-2015", "the-prestige-2006"]


def seed_demo_users(db: Database) -> None:
    if db.users.count_documents({"is_demo": True}) > 0:
        return
    rng = random.Random(7)
    now = datetime.now(timezone.utc)
    movies = list(db.movies.find({}, {"genres": 1, "imdb_rating": 1, "imdb_votes": 1}))
    popularity = {m["_id"]: (m.get("imdb_votes") or 300_000) for m in movies}

    ratings = []
    for i in range(1, 61):
        taste = TASTES[(i - 1) % len(TASTES)]
        if rng.random() < 0.4:
            taste = taste + [rng.choice(["Drama", "Comedy", "Action", "Thriller", "Adventure"])]
        user = {"username": f"viewer{i:02d}", "display_name": f"Viewer {i:02d}", "is_demo": True,
                "password": hash_password(f"locked-{rng.random()}"), "favourite_genres": taste,
                "onboarded": True, "my_list": [], "created_at": now - timedelta(days=30)}
        uid = db.users.insert_one(user).inserted_id
        # Like real people, demo users mostly watch the well-known movies of their favourite genres.
        fits = sorted((m for m in movies if set(m["genres"]) & set(taste)),
                      key=lambda m: -popularity[m["_id"]] * m["imdb_rating"])[:120]
        others = [m for m in movies if not set(m["genres"]) & set(taste)]
        # Popular, well-rated movies in their genres are more likely to be watched.
        weights = [popularity[m["_id"]] * m["imdb_rating"] for m in fits]
        picked = {m["_id"]: m for m in rng.choices(fits, weights=weights, k=rng.randint(20, 32))}
        for m in picked.values():
            stars = 5 if m["imdb_rating"] >= 8 else 4 if m["imdb_rating"] >= 7 else 3
            stars = max(1, min(5, stars + rng.choice([-1, 0, 0, 0, 1])))
            ratings.append({"user_id": uid, "movie_id": m["_id"], "stars": stars,
                            "created_at": now - timedelta(hours=rng.uniform(1, 24 * 14))})
        for m in rng.sample(others, k=min(len(others), rng.randint(2, 5))):
            ratings.append({"user_id": uid, "movie_id": m["_id"], "stars": rng.choice([1, 2, 2, 3]),
                            "created_at": now - timedelta(hours=rng.uniform(1, 24 * 14))})
    db.ratings.insert_many(ratings, ordered=False)

    # The presenter account.
    try:
        uid = db.users.insert_one({
            "username": "demo", "display_name": "Demo User", "is_demo": True,
            "password": hash_password("demo1234"), "favourite_genres": ["Sci-Fi", "Thriller", "Adventure"],
            "onboarded": True, "created_at": now,
            "my_list": [{"movie_id": mid, "added_at": now - timedelta(minutes=k)} for k, mid in enumerate(DEMO_LIST)
                        if db.movies.count_documents({"_id": mid})],
        }).inserted_id
        db.ratings.insert_many([{"user_id": uid, "movie_id": mid, "stars": 5, "created_at": now - timedelta(minutes=k)}
                                for k, mid in enumerate(DEMO_LIST) if db.movies.count_documents({"_id": mid})])
    except DuplicateKeyError:
        pass
