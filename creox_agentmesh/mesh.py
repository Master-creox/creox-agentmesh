"""Creox AgentMesh v1 core — registry, tokens, task bus, audit, recovery.

Storage: SQLite via stdlib only. Agent tokens are SHA-256 hashed;
only the hash is stored, the plain token is shown once at
registration. Local-only by design: this module never touches
the network, the host system, or any other project (including BAOS).
"""
from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import time
from pathlib import Path

from .demo_agents import DEMO_AGENTS

MAX_ATTEMPTS = 3


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class MeshError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


class Mesh:
    def __init__(self, db_path: str | Path = "agentmesh.db"):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            capabilities TEXT NOT NULL, permissions TEXT NOT NULL,
            token_hash TEXT NOT NULL, last_heartbeat TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, task_type TEXT NOT NULL,
            payload TEXT NOT NULL, status TEXT NOT NULL,
            assigned_agent_id INTEGER, submitter_agent_id INTEGER,
            result TEXT, attempts INTEGER DEFAULT 0, created_at TEXT);
        CREATE TABLE IF NOT EXISTS audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT NOT NULL,
            action TEXT NOT NULL, task_id INTEGER, detail TEXT,
            created_at TEXT);
        """)
        self.conn.commit()

    # -- audit ------------------------------------------------------
    def _audit(self, actor: str, action: str, task_id=None, detail="") -> None:
        self.conn.execute(
            "INSERT INTO audit (actor, action, task_id, detail, created_at)"
            " VALUES (?,?,?,?,?)", (actor, action, task_id, detail, _now()))
        self.conn.commit()

    def audit_log(self, limit: int = 100) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    # -- agents -----------------------------------------------------
    def register_agent(self, name: str, capabilities: list[str],
                       permissions: list[str]) -> dict:
        if not name or not capabilities:
            raise MeshError("name and capabilities are required")
        token = "agm_" + secrets.token_hex(16)
        cur = self.conn.execute(
            "INSERT INTO agents (name, capabilities, permissions, token_hash,"
            " last_heartbeat, created_at) VALUES (?,?,?,?,?,?)",
            (name, json.dumps(capabilities), json.dumps(permissions),
             _hash(token), _now(), _now()))
        self.conn.commit()
        self._audit(f"agent:{cur.lastrowid}", "agent_registered",
                    detail=f"name={name}")
        return {"id": cur.lastrowid, "name": name,
                "capabilities": capabilities, "permissions": permissions,
                "token": token,
                "note": "Store this token now — it is shown only once."}

    def list_agents(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, name, capabilities, permissions, last_heartbeat,"
            " created_at FROM agents ORDER BY id").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["capabilities"] = json.loads(d["capabilities"])
            d["permissions"] = json.loads(d["permissions"])
            out.append(d)
        return out

    def _agent(self, agent_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
        return dict(row) if row else None

    def verify_token(self, agent_id: int, token: str) -> bool:
        agent = self._agent(agent_id)
        if agent is None or not token:
            return False
        return secrets.compare_digest(agent["token_hash"], _hash(token))

    def heartbeat(self, agent_id: int, token: str) -> dict:
        if not self.verify_token(agent_id, token):
            self._audit(f"agent:{agent_id}", "heartbeat_rejected")
            raise MeshError("invalid agent token", 403)
        self.conn.execute(
            "UPDATE agents SET last_heartbeat = ? WHERE id = ?",
            (_now(), agent_id))
        self.conn.commit()
        return {"agent_id": agent_id, "heartbeat": "ok"}

    # -- tasks ------------------------------------------------------
    def _pick_agent(self, task_type: str) -> int | None:
        for a in self.list_agents():
            if task_type in a["capabilities"] and task_type in a["permissions"]:
                return a["id"]
        return None

    def submit_task(self, agent_id: int, token: str, task_type: str,
                    payload: dict) -> dict:
        if not self.verify_token(agent_id, token):
            self._audit(f"agent:{agent_id}", "task_rejected_bad_token")
            raise MeshError("invalid agent token", 403)
        if task_type not in DEMO_AGENTS:
            raise MeshError(f"unknown task type: {task_type}")
        assigned = self._pick_agent(task_type)
        cur = self.conn.execute(
            "INSERT INTO tasks (task_type, payload, status, assigned_agent_id,"
            " submitter_agent_id, created_at) VALUES (?,?,?,?,?,?)",
            (task_type, json.dumps(payload),
             "pending" if assigned else "unassigned", assigned,
             agent_id, _now()))
        self.conn.commit()
        self._audit(f"agent:{agent_id}", "task_submitted", cur.lastrowid,
                    f"type={task_type} assigned={assigned}")
        return self.get_task(cur.lastrowid)

    def get_task(self, task_id: int) -> dict:
        row = self.conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise MeshError("task not found", 404)
        d = dict(row)
        d["payload"] = json.loads(d["payload"])
        d["result"] = json.loads(d["result"]) if d["result"] else None
        return d

    def execute_task(self, task_id: int, agent_id: int, token: str) -> dict:
        if not self.verify_token(agent_id, token):
            self._audit(f"agent:{agent_id}", "execute_rejected_bad_token",
                        task_id)
            raise MeshError("invalid agent token", 403)
        task = self.get_task(task_id)
        if task["status"] not in ("pending", "running"):
            raise MeshError(f"task is {task['status']}, cannot execute")
        if task["assigned_agent_id"] not in (None, agent_id):
            self._audit(f"agent:{agent_id}", "execute_rejected_not_assigned",
                        task_id)
            raise MeshError("task assigned to another agent", 403)
        agent = self._agent(agent_id)
        caps = json.loads(agent["capabilities"])
        perms = json.loads(agent["permissions"])
        if task["task_type"] not in caps or task["task_type"] not in perms:
            self._audit(f"agent:{agent_id}", "execute_rejected_no_permission",
                        task_id)
            raise MeshError("agent lacks capability/permission for task", 403)
        self.conn.execute(
            "UPDATE tasks SET status = 'running', assigned_agent_id = ?"
            " WHERE id = ?", (agent_id, task_id))
        self.conn.commit()
        try:
            result = DEMO_AGENTS[task["task_type"]](task["payload"])
        except Exception as exc:  # demo agent failure is a task failure
            self.conn.execute(
                "UPDATE tasks SET status = 'failed', result = ? WHERE id = ?",
                (json.dumps({"error": str(exc)}), task_id))
            self.conn.commit()
            self._audit(f"agent:{agent_id}", "task_failed", task_id, str(exc))
            return self.get_task(task_id)
        self.conn.execute(
            "UPDATE tasks SET status = 'done', result = ? WHERE id = ?",
            (json.dumps(result), task_id))
        self.conn.commit()
        self._audit(f"agent:{agent_id}", "task_done", task_id)
        return self.get_task(task_id)

    def recover_stale(self, timeout_seconds: int = 60) -> list[dict]:
        """Reassign running tasks whose agent heartbeat is stale.

        Returns the tasks it touched. After MAX_ATTEMPTS a task goes
        to dead_letter instead of looping forever.
        """
        import datetime
        cutoff = (datetime.datetime.now(datetime.timezone.utc)
                  - datetime.timedelta(seconds=timeout_seconds))
        touched = []
        rows = self.conn.execute(
            "SELECT * FROM tasks WHERE status = 'running'").fetchall()
        for row in rows:
            task = dict(row)
            agent = self._agent(task["assigned_agent_id"]) if task["assigned_agent_id"] else None
            hb = agent["last_heartbeat"] if agent else None
            stale = True
            if hb:
                try:
                    hb_dt = datetime.datetime.strptime(
                        hb, "%Y-%m-%dT%H:%M:%SZ").replace(
                            tzinfo=datetime.timezone.utc)
                    stale = hb_dt < cutoff
                except ValueError:
                    stale = True
            if not stale:
                continue
            attempts = task["attempts"] + 1
            if attempts >= MAX_ATTEMPTS:
                self.conn.execute(
                    "UPDATE tasks SET status = 'dead_letter', attempts = ?"
                    " WHERE id = ?", (attempts, task["id"]))
                self.conn.commit()
                self._audit("mesh", "task_dead_letter", task["id"],
                            f"attempts={attempts}")
            else:
                nxt = self._pick_agent(task["task_type"])
                # Never reassign to the same stale agent if another fits.
                if nxt == task["assigned_agent_id"]:
                    others = [a["id"] for a in self.list_agents()
                              if a["id"] != task["assigned_agent_id"]
                              and task["task_type"] in a["capabilities"]
                              and task["task_type"] in a["permissions"]]
                    nxt = others[0] if others else None
                self.conn.execute(
                    "UPDATE tasks SET status = 'pending',"
                    " assigned_agent_id = ?, attempts = ? WHERE id = ?",
                    (nxt, attempts, task["id"]))
                self.conn.commit()
                self._audit("mesh", "task_reassigned", task["id"],
                            f"from={task['assigned_agent_id']} to={nxt}")
            touched.append(self.get_task(task["id"]))
        return touched
