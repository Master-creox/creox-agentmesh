# Creox AgentMesh — Blueprint (LOCKED 2026-10-29 by Akash)

v1 built to this blueprint, 7/7 unittest pass + API flow verified
on Muse VM. Laptop test by Akash is the final check.

Agent-to-agent communication + task execution framework.
Standalone project — it does NOT touch BAOS or BAOS agents (A001–A005).
BAOS boundary is respected: this mesh has its own demo/worker agents only.

## Purpose (Akash's idea, 2026-10-28)
Multiple agents talk to each other, take tasks, and report results —
with identity checks, permissions, scheduling, audit logs, and
recovery when an agent fails. Like a team, not a single agent.

## Principles
- Local-first, defensive only. v1 runs on one machine, never
  internet-facing, never acting on real systems by itself.
- No agent runs a task it has no permission for. Permission denied
  is a normal, logged outcome — not an error to work around.
- Everything is audited. Every registration, task, message and
  result goes into the audit log.
- Deterministic demo agents first. No real LLM needed for v1, so
  the mesh can be tested on any laptop without a model download.

## v1 scope (proposed)
1. **Agent registry** — register an agent with id, name,
   capabilities (which task types it can do) and permissions.
2. **Identity verification** — each agent gets a token at
   registration (SHA-256 hashed, stored hashed only). Every task
   message must carry a valid agent token; unknown/forged tokens
   are rejected and logged.
3. **Task bus** — dispatcher assigns a task only to an agent whose
   capabilities + permissions match. Task states:
   pending → running → done / failed.
4. **Scheduler** — one-time tasks in v1, plus retry scheduling.
   Recurring tasks are Phase 2.
5. **Audit log** — append-only log in SQLite: who did what, when,
   with what result.
6. **Failed-agent recovery** — heartbeat + timeout. If an agent
   stops responding, its running task is re-queued to another
   capable agent (max 3 attempts), then moved to a dead-letter
   list instead of being lost silently.
7. **Demo agents (safe, local, deterministic)** —
   EchoAgent (echoes a message), CalculatorAgent (arithmetic),
   LogAnalyzerAgent (counts error lines in a given sample log).
8. **API + CLI** — FastAPI: GET /health, POST /agents/register,
   GET /agents, POST /tasks, GET /tasks/{id}, GET /audit.
   CLI demo script runs the whole flow end to end.
9. **Storage** — SQLite only. Dependencies: FastAPI + uvicorn
   (same pattern as Creox Aegis Defense).

## Stack decision (needs Akash's lock)
Original idea listed Python, Rust, FastAPI, SQLite. Proposed v1:
**Python + FastAPI + SQLite only, Rust deferred to Phase 2.**
Reason: v1 must be testable on his laptop with the tools he
already runs (Python 3.14, `python -m pip`). A Rust worker in v1
would add a second toolchain before the mesh itself is proven.

## Out of scope for v1
- Real LLM agents, internet-facing mesh, cross-machine mesh.
- BAOS agents or BAOS integration of any kind.
- Automatic actions on the host system (files, network, accounts).
- Recurring scheduler, web dashboard (FastAPI API first, like
  Aegis Phase 3 came after its core).

## v1 success test (on HIS laptop only, guide-only)
1. Register 3 demo agents.
2. Submit one task per agent type — all 3 complete, audit shows
   every step.
3. Simulate one agent failing (stop its heartbeat) — its task is
   re-assigned and completes, dead-letter stays empty.
4. Submit a task with a wrong token — rejected + logged, nothing runs.
5. Submit a task no agent is permitted for — denied + logged.

## Locked answers (2026-10-29)
1. Python-only v1, Rust in Phase 2 — LOCKED.
2. Demo agents above — LOCKED.
3. Local-only first — LOCKED.
