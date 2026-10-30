import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config, errors
from .db import init_db_with_retry
from .routers import auth, insights, me, movies

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db_with_retry()
    yield


app = FastAPI(title=f"{config.APP_NAME} API", description=config.APP_TAGLINE, version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])
errors.register(app)
for r in (auth, movies, me, insights):
    app.include_router(r.router, prefix="/api")
