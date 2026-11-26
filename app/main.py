import re
import time
import uuid

from fastapi import FastAPI, Request, Response
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.auth import router as auth_router
from app.boards import router as boards_router
from app.deps import DbSession
from app.logs import get_logger
from app.models import User

app = FastAPI(title="taskboard")
Instrumentator().instrument(app).expose(app)
app.include_router(auth_router)
app.include_router(boards_router)

logger = get_logger()
QUIET_PATHS = {"/metrics", "/health", "/ready"}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Reuse the caller's identifier if it sent a reasonable one,
    # otherwise create one. It follows the request everywhere.
    request_id = request.headers.get("X-Request-ID", "")
    if not re.fullmatch(r"[A-Za-z0-9-]{8,64}", request_id):
        request_id = uuid.uuid4().hex
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        if request.url.path not in QUIET_PATHS:
            logger.info(
                "request",
                extra={
                    "fields": {
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status": status,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    }
                },
            )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: DbSession, response: Response):
    try:
        db.execute(select(User.id).limit(1))
    except SQLAlchemyError:
        response.status_code = 503
        return {"status": "database not ready"}
    return {"status": "ready"}