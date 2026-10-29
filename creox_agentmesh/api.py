"""Creox AgentMesh v1 API (FastAPI).

Local-only demo API. No auth beyond agent tokens, which are the
mesh's own identity mechanism — do not expose this port publicly.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .mesh import Mesh, MeshError

VERSION = "0.1.0"


class RegisterRequest(BaseModel):
    name: str
    capabilities: list[str]
    permissions: list[str]


class TaskRequest(BaseModel):
    agent_id: int
    token: str
    task_type: str
    payload: dict = {}


class ExecuteRequest(BaseModel):
    agent_id: int
    token: str


class HeartbeatRequest(BaseModel):
    agent_id: int
    token: str


def create_app(mesh: Mesh | None = None) -> FastAPI:
    app = FastAPI(title="Creox AgentMesh", version=VERSION)
    app.state.mesh = mesh or Mesh()

    def m() -> Mesh:
        return app.state.mesh

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "Creox AgentMesh",
                "version": VERSION}

    @app.get("/", response_class=HTMLResponse)
    def dashboard():
        return DASHBOARD_HTML

    @app.get("/tasks")
    def tasks():
        return {"tasks": m().list_tasks()}

    @app.post("/agents/register", status_code=201)
    def register(payload: RegisterRequest):
        try:
            return m().register_agent(payload.name, payload.capabilities,
                                      payload.permissions)
        except MeshError as e:
            raise HTTPException(e.status, str(e))

    @app.get("/agents")
    def agents():
        return {"agents": m().list_agents()}

    @app.post("/agents/seed")
    def seed():
        return m().seed_creox_agents()

    @app.post("/agents/heartbeat")
    def heartbeat(payload: HeartbeatRequest):
        try:
            return m().heartbeat(payload.agent_id, payload.token)
        except MeshError as e:
            raise HTTPException(e.status, str(e))

    @app.post("/tasks", status_code=201)
    def submit(payload: TaskRequest):
        try:
            return m().submit_task(payload.agent_id, payload.token,
                                   payload.task_type, payload.payload)
        except MeshError as e:
            raise HTTPException(e.status, str(e))

    @app.get("/tasks/{task_id}")
    def task(task_id: int):
        try:
            return m().get_task(task_id)
        except MeshError as e:
            raise HTTPException(e.status, str(e))

    @app.post("/tasks/{task_id}/execute")
    def execute(task_id: int, payload: ExecuteRequest):
        try:
            return m().execute_task(task_id, payload.agent_id, payload.token)
        except MeshError as e:
            raise HTTPException(e.status, str(e))

    @app.post("/tasks/recover")
    def recover():
        return {"recovered": m().recover_stale(timeout_seconds=0)}

    @app.get("/audit")
    def audit(limit: int = 100):
        return {"audit": m().audit_log(limit)}

    return app


from pathlib import Path

DASHBOARD_HTML = (Path(__file__).parent / "dashboard.html").read_text(encoding="utf-8")
