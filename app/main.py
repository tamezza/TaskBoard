from fastapi import FastAPI, Response
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.auth import router as auth_router
from app.boards import router as boards_router
from app.deps import DbSession
from app.models import User

app = FastAPI(title="taskboard")
Instrumentator().instrument(app).expose(app)
app.include_router(auth_router)
app.include_router(boards_router)


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