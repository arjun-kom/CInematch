"""Every error is returned as {"error": code, "detail": message}."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo.errors import ConnectionFailure, PyMongoError

log = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, status: int, error: str, detail: str):
        self.status, self.error, self.detail = status, error, detail


def register(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api(_: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status, content={"error": exc.error, "detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        msgs = [f"{'.'.join(str(p) for p in e['loc'] if p != 'body')}: {e['msg']}" for e in exc.errors()]
        return JSONResponse(status_code=422, content={"error": "validation_error", "detail": "; ".join(msgs)})

    @app.exception_handler(ConnectionFailure)
    async def _down(_: Request, exc: Exception):
        return JSONResponse(status_code=503, content={"error": "database_unavailable",
                                                      "detail": "Cannot reach MongoDB. Is the database container running?"})

    @app.exception_handler(PyMongoError)
    async def _db(_: Request, exc: PyMongoError):
        log.exception("Database error")
        return JSONResponse(status_code=500, content={"error": "database_error", "detail": str(exc)[:300]})
