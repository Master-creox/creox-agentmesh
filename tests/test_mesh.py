"""AgentMesh v1 tests (unittest, stdlib only for the core)."""
import unittest

from creox_agentmesh.mesh import Mesh, MeshError


def _mesh():
    return Mesh(":memory:")


def _agents(m):
    echo = m.register_agent("Echo", ["echo"], ["echo"])
    calc = m.register_agent("Calc", ["calc"], ["calc"])
    calc2 = m.register_agent("Calc2", ["calc"], ["calc"])
    loga = m.register_agent("Log", ["log_analyze"], ["log_analyze"])
    return echo, calc, calc2, loga


class TestMesh(unittest.TestCase):
    def test_register_and_token(self):
        m = _mesh()
        a = m.register_agent("Echo", ["echo"], ["echo"])
        self.assertTrue(a["token"].startswith("agm_"))
        self.assertTrue(m.verify_token(a["id"], a["token"]))
        self.assertFalse(m.verify_token(a["id"], "wrong"))
        names = [x["name"] for x in m.list_agents()]
        self.assertIn("Echo", names)
        # Token hashes, never plain tokens, are stored.
        row = m.conn.execute("SELECT token_hash FROM agents WHERE id=?",
                             (a["id"],)).fetchone()
        self.assertNotIn(a["token"], row[0])

    def test_echo_calc_log_flow(self):
        m = _mesh()
        echo, calc, _, loga = _agents(m)
        t = m.submit_task(echo["id"], echo["token"], "echo",
                          {"message": "hi"})
        self.assertEqual(m.execute_task(t["id"], echo["id"], echo["token"])["result"],
                         {"echo": "hi"})
        t = m.submit_task(echo["id"], echo["token"], "calc",
                          {"expression": "2 + 3 * 4"})
        self.assertEqual(m.execute_task(t["id"], calc["id"], calc["token"])["result"]["result"], 14)
        t = m.submit_task(echo["id"], echo["token"], "log_analyze",
                          {"log": "ok\nERROR a\nERROR b"})
        done = m.execute_task(t["id"], loga["id"], loga["token"])
        self.assertEqual(done["result"]["error_lines"], 2)

    def test_bad_token_and_wrong_agent_rejected(self):
        m = _mesh()
        echo, calc, _, _ = _agents(m)
        with self.assertRaises(MeshError):
            m.submit_task(echo["id"], "bad", "echo", {"message": "x"})
        t = m.submit_task(echo["id"], echo["token"], "calc",
                          {"expression": "1+1"})
        with self.assertRaises(MeshError):
            m.execute_task(t["id"], echo["id"], echo["token"])
        # Calc agent may execute its own assigned task.
        self.assertEqual(m.execute_task(t["id"], calc["id"], calc["token"])["status"], "done")

    def test_no_permission_means_unassigned(self):
        m = _mesh()
        echo = m.register_agent("EchoOnly", ["echo"], ["echo"])
        t = m.submit_task(echo["id"], echo["token"], "calc",
                          {"expression": "1+1"})
        self.assertEqual(t["status"], "unassigned")
        self.assertIsNone(t["assigned_agent_id"])

    def test_recovery_reassigns_and_dead_letters(self):
        m = _mesh()
        echo, calc, calc2, _ = _agents(m)
        t = m.submit_task(echo["id"], echo["token"], "calc",
                          {"expression": "5+5"})
        self.assertEqual(t["assigned_agent_id"], calc["id"])
        m.conn.execute("UPDATE tasks SET status='running' WHERE id=?", (t["id"],))
        m.conn.execute("UPDATE agents SET last_heartbeat='2000-01-01T00:00:00Z'"
                       " WHERE id=?", (calc["id"],))
        m.conn.commit()
        touched = m.recover_stale(timeout_seconds=60)
        self.assertEqual(touched[0]["assigned_agent_id"], calc2["id"])
        self.assertEqual(touched[0]["status"], "pending")
        # Single-agent mesh: repeated recovery ends in dead_letter.
        m2 = _mesh()
        solo = m2.register_agent("Solo", ["calc"], ["calc"])
        sub = m2.register_agent("Sub", ["echo"], ["echo"])
        t2 = m2.submit_task(sub["id"], sub["token"], "calc",
                            {"expression": "1+1"})
        for _ in range(3):
            m2.conn.execute("UPDATE tasks SET status='running' WHERE id=?",
                            (t2["id"],))
            m2.conn.execute("UPDATE agents SET last_heartbeat='2000-01-01T00:00:00Z'"
                            " WHERE id=?", (solo["id"],))
            m2.conn.commit()
            m2.recover_stale(timeout_seconds=60)
        self.assertEqual(m2.get_task(t2["id"])["status"], "dead_letter")

    def test_audit_records_flow(self):
        m = _mesh()
        echo, _, _, _ = _agents(m)
        t = m.submit_task(echo["id"], echo["token"], "echo", {"message": "x"})
        m.execute_task(t["id"], echo["id"], echo["token"])
        actions = [a["action"] for a in m.audit_log()]
        self.assertIn("task_submitted", actions)
        self.assertIn("task_done", actions)

    def test_calc_rejects_code_injection(self):
        m = _mesh()
        echo, calc, _, _ = _agents(m)
        t = m.submit_task(echo["id"], echo["token"], "calc",
                          {"expression": "__import__('os').system('echo pwned')"})
        done = m.execute_task(t["id"], calc["id"], calc["token"])
        self.assertEqual(done["status"], "failed")


if __name__ == "__main__":
    unittest.main()
