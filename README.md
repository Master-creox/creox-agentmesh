# Creox AgentMesh

Agent-to-agent communication + task execution framework — a team of
agents, not a single agent. **Standalone: it does not touch BAOS.**

## What v1 does
- **Agent registry** — agents register with capabilities + permissions.
- **Identity verification** — each agent gets a token (shown once,
  stored only as a SHA-256 hash). Bad tokens are rejected + logged.
- **Task bus** — the dispatcher assigns a task only to an agent whose
  capability and permission match. States: pending → running → done /
  failed / unassigned / dead_letter.
- **Audit log** — every registration, task, result and rejection is
  logged in SQLite.
- **Failed-agent recovery** — a stale heartbeat means the running task
  is re-assigned to another capable agent (max 3 attempts), then it
  goes to dead_letter instead of vanishing.
- **Demo agents (safe, local, deterministic)** — Echo, Calculator
  (safe AST arithmetic only — code injection is rejected), Log
  Analyzer (counts ERROR lines in a sample log).

## Stack
Python + FastAPI + SQLite. Rust is deferred to Phase 2 by blueprint
lock (2026-10-29): v1 must be testable on a laptop with existing tools.

## Run (local only — do not expose publicly)
```bash
python -m pip install -r requirements.txt
python demo.py
python -m uvicorn creox_agentmesh.api:create_app --factory --port 8001
```
### Seed CreoX agents (your real projects as mesh agents)

On the dashboard, click **Seed CreoX Agents** — or `POST /agents/seed`.
It registers 12 of your real projects as agents (Baby Angel,
Aegis Prime, SentinelAI, ScamShield Global, Master CreoX API,
Advanced + Basic Network Sniffer, CicadaLab 3301, AI Cyber Account
Lab, Creox Aegis Defense, Ethical Hacking Practice Lab, Obdsss),
each with the demo task it can actually run (echo / log_analyze /
calc). Tokens are shown only once at seeding and saved in the
browser for submit/execute. Re-seeding never duplicates.
Not seeded by design: BAOS (solo), CodeMentor-AI + codealpha_tasks
(parked), profile repo, SDC plan, Jarvis (design only), BabyCoach
apps. This is mesh registration + routing — live integration of
each project's real code is Phase 2.

Then open the Mission Control dashboard at http://127.0.0.1:8001/
— top stats (agents / online / active / completed / audit),
Agent Network graph, Agent Status donut, Agent Load bars,
Active Tasks, Comms Feed (audit) and Control forms
(register / submit / execute / recover). Every number on it is
real mesh data — no invented agents, tasks or counts.
API docs are at http://127.0.0.1:8001/docs

## API
- `GET /health`
- `POST /agents/register` — returns the agent token **once**
- `GET /agents`, `POST /agents/heartbeat`
- `POST /tasks`, `GET /tasks/{id}`, `POST /tasks/{id}/execute`
- `POST /tasks/recover`, `GET /audit`

## Tests
```bash
python -m unittest discover -s tests -t .
```
7/7 pass on v1. Laptop test (his machine only) is the final check,
as with every CreoX project.

## Out of scope for v1
Real LLM agents, internet-facing or cross-machine mesh, BAOS agents
or integration, automatic host-system actions, recurring scheduler,
web dashboard.
