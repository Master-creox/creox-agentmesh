"""CreoX seed agents — Akash's real projects, registered as mesh agents.

Each seed agent carries the demo task type it can actually run inside
the mesh (echo / log_analyze / calc). That is the honest scope of
this step: mesh registration + routing, NOT a live integration of
each project's real code. Live integration (each project running its
own adapter/server and joining the mesh) is Phase 2.

Deliberately NOT seeded:
- BAOS / baby-angle-baos — Akash's solo project, never touched here.
- CodeMentor-AI and codealpha_tasks — parked at his direction.
- Master-creox profile repo — not a project agent.
- Space Debris Cleanup — a standalone plan, not a software agent.
- Jarvis — design only so far, no repo/code to seed as an agent.
- BabyCoach Android apps — Android apps, not mesh agents.
"""
from __future__ import annotations

# (name, mesh task type it runs, what it is)
SEED_AGENTS = [
    ("Baby Angel", "echo", "voice companion"),
    ("Aegis Prime", "log_analyze", "HUD security partner"),
    ("SentinelAI", "log_analyze", "SOC threat detection"),
    ("ScamShield Global", "log_analyze", "scam protection"),
    ("Master CreoX API", "echo", "brain / chat gateway"),
    ("Advanced Network Sniffer", "log_analyze", "network analysis"),
    ("Basic Network Sniffer", "log_analyze", "network analysis"),
    ("CicadaLab 3301", "calc", "puzzle / cipher lab"),
    ("AI Cyber Account Lab", "log_analyze", "anomaly detection"),
    ("Creox Aegis Defense", "log_analyze", "defensive security"),
    ("Ethical Hacking Practice Lab", "echo", "practice coach"),
    ("Obdsss", "log_analyze", "PHP scanner"),
]
