"""Settings from environment variables. Rename the project with APP_NAME / APP_TAGLINE in .env."""
import os

APP_NAME = os.getenv("APP_NAME", "CineMatch")
APP_TAGLINE = os.getenv("APP_TAGLINE", "Personalised Movie Recommendation System using MongoDB")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "cinematch")
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "7"))
SEED_DEMO_USERS = os.getenv("SEED_DEMO_USERS", "true").lower() == "true"
