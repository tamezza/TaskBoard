from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="taskboard")

class TaskIn(BaseModel):
    title: str

tasks: dict[int, dict] = {}
next_id = 1

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/tasks")
def list_tasks():
    return list(tasks.values())

@app.post("/tasks", status_code=201)
def create_task(task: TaskIn):
    global next_id
    item = {"id": next_id, "title": task.title, "done": False}
    tasks[next_id] = item
    next_id += 1
    return item

@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="task not found")
    return tasks[task_id]
