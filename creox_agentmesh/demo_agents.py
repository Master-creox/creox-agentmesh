"""Demo agents for AgentMesh v1 — safe, local, deterministic.

No LLM, no network, no host actions. Each function takes a dict
payload and returns a dict result, so the mesh can be proven
end to end on any laptop.
"""
from __future__ import annotations

import ast
import operator


def echo(payload: dict) -> dict:
    return {"echo": payload.get("message", "")}


_ALLOWED_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval(node.operand))
    raise ValueError("unsupported expression")


def calc(payload: dict) -> dict:
    expr = str(payload.get("expression", ""))
    if len(expr) > 200:
        raise ValueError("expression too long")
    tree = ast.parse(expr, mode="eval")
    return {"expression": expr, "result": _eval(tree)}


def log_analyze(payload: dict) -> dict:
    log = str(payload.get("log", ""))
    lines = log.splitlines()
    errors = [l for l in lines if "ERROR" in l]
    return {"total_lines": len(lines), "error_lines": len(errors),
            "errors": errors}


DEMO_AGENTS = {"echo": echo, "calc": calc, "log_analyze": log_analyze}
