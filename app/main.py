from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.auth import router as auth_router
from app.boards import router as boards_router

app = FastAPI(title="taskboard")
Instrumentator().instrument(app).expose(app)
app.include_router(auth_router)
app.include_router(boards_router)


@app.get("/health")
def health():
    return {"status": "ok"}
