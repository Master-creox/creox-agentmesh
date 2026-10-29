"""AgentMesh v1 demo — full flow on a throwaway database.

Run:  python demo.py
Shows: register 3 demo agents -> submit 3 tasks -> execute all ->
audit log -> bad token rejected -> recovery of a stale task.
"""
from creox_agentmesh.mesh import Mesh


def main() -> None:
    mesh = Mesh(":memory:")
    echo = mesh.register_agent("EchoAgent", ["echo"], ["echo"])
    calc = mesh.register_agent("CalcAgent", ["calc"], ["calc"])
    loga = mesh.register_agent("LogAgent", ["log_analyze"], ["log_analyze"])
    calc2 = mesh.register_agent("CalcAgent2", ["calc"], ["calc"])
    print("agents:", [a["name"] for a in mesh.list_agents()])

    t1 = mesh.submit_task(echo["id"], echo["token"], "echo",
                          {"message": "hello mesh"})
    t2 = mesh.submit_task(echo["id"], echo["token"], "calc",
                          {"expression": "2 + 3 * 4"})
    t3 = mesh.submit_task(echo["id"], echo["token"], "log_analyze",
                          {"log": "ok\nERROR disk full\nok\nERROR timeout"})
    for task, agent in ((t1, echo), (t2, calc), (t3, loga)):
        done = mesh.execute_task(task["id"], agent["id"], agent["token"])
        print(f"task {task['id']} ({task['task_type']}):",
              done["status"], done["result"])

    try:
        mesh.submit_task(echo["id"], "bad-token", "echo", {"message": "x"})
    except Exception as e:
        print("bad token rejected as expected:", e)

    # Simulate a stale running task: submit, mark running, age the
    # worker's heartbeat, then recover it to another capable agent.
    running = mesh.submit_task(echo["id"], echo["token"], "calc",
                               {"expression": "1 + 1"})
    mesh.conn.execute("UPDATE tasks SET status='running' WHERE id=?",
                      (running["id"],))
    mesh.conn.execute("UPDATE agents SET last_heartbeat='2000-01-01T00:00:00Z'"
                      " WHERE id=?", (calc["id"],))
    mesh.conn.commit()
    print("recover stale:", [(t["id"], t["status"], t["assigned_agent_id"])
                             for t in mesh.recover_stale(timeout_seconds=60)])
    print("audit entries:", len(mesh.audit_log()))


if __name__ == "__main__":
    main()
