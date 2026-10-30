"""MongoDB connection, indexes and first-run data loading."""
import json
import logging
import time
from pathlib import Path

from pymongo import ASCENDING, DESCENDING, TEXT, MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from . import config

log = logging.getLogger(__name__)
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "movies.json"
_client = None


def get_db() -> Database:
    global _client
    if _client is None:
        _client = MongoClient(config.MONGO_URL, serverSelectionTimeoutMS=3000, tz_aware=True)
    return _client[config.MONGO_DB]


def create_indexes(db: Database) -> None:
    # movies --------------------------------------------------------------
    # Text index: lets users search words in title, cast, director and description.
    db.movies.create_index([("title", TEXT), ("cast", TEXT), ("director", TEXT), ("description", TEXT)],
                           name="movie_text", weights={"title": 10, "cast": 4, "director": 4, "description": 1})
    # Multikey compound index: `genres` is an array, so each genre gets its own index entry.
    db.movies.create_index([("genres", ASCENDING), ("imdb_rating", DESCENDING)], name="genre_rating")
    db.movies.create_index([("imdb_rating", DESCENDING), ("imdb_votes", DESCENDING)], name="rating_votes")
    db.movies.create_index([("year", DESCENDING)], name="year")
    db.movies.create_index([("director", ASCENDING)], name="director")
    # users -----------------------------------------------------------------
    db.users.create_index([("username", ASCENDING)], name="username_unique", unique=True)
    # ratings ---------------------------------------------------------------
    # One rating per user per movie (unique compound index).
    db.ratings.create_index([("user_id", ASCENDING), ("movie_id", ASCENDING)], name="user_movie_unique", unique=True)
    db.ratings.create_index([("movie_id", ASCENDING), ("stars", DESCENDING)], name="movie_stars")
    db.ratings.create_index([("created_at", DESCENDING)], name="created_at")
    # sessions: TTL index deletes a login session automatically when it expires.
    db.sessions.create_index([("expires_at", ASCENDING)], name="session_ttl", expireAfterSeconds=0)


def load_movies(db: Database) -> int:
    if db.movies.estimated_document_count() > 0:
        return 0
    movies = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    db.movies.insert_many(movies, ordered=False)
    log.info("Loaded %d movies", len(movies))
    return len(movies)


def init_db(db: Database | None = None, seed_users: bool | None = None) -> None:
    from .seed import seed_demo_users  # avoid circular import

    db = db if db is not None else get_db()
    create_indexes(db)
    load_movies(db)
    if config.SEED_DEMO_USERS if seed_users is None else seed_users:
        seed_demo_users(db)


def init_db_with_retry(attempts: int = 15) -> bool:
    for i in range(attempts):
        try:
            init_db()
            return True
        except PyMongoError as exc:
            log.warning("MongoDB not ready (%d/%d): %s", i + 1, attempts, exc)
            time.sleep(2)
    return False
