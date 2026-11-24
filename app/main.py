from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import router as auth_router
from app.db import Task
from app.deps import DbSession

app = FastAPI(title="taskboard")
Instrumentator().instrument(app).expose(app)
app.include_router(auth_router)


class TaskIn(BaseModel):
    title: str


class TaskOut(BaseModel):
    id: int
    title: str
    done: bool

    model_config = {"from_attributes": True}



def get_task_or_404(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tasks", response_model=list[TaskOut])
def list_tasks(db: DbSession):
    return db.query(Task).all()


@app.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(task: TaskIn, db: DbSession):
    item = Task(title=task.title)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: DbSession):
    return get_task_or_404(db, task_id)


@app.patch("/tasks/{task_id}/done", response_model=TaskOut)
def complete_task(task_id: int, db: DbSession):
    task = get_task_or_404(db, task_id)
    task.done = True
    db.commit()
    db.refresh(task)
    return task
