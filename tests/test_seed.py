import unittest

from creox_agentmesh.mesh import Mesh
from creox_agentmesh.seed_agents import SEED_AGENTS


class TestSeed(unittest.TestCase):
    def test_seed_once_and_twice(self):
        m = Mesh(":memory:")
        first = m.seed_creox_agents()
        self.assertEqual(len(first["seeded"]), len(SEED_AGENTS))
        self.assertEqual(len(first["already_seeded"]), 0)
        self.assertTrue(all(a["token"].startswith("agm_")
                            for a in first["seeded"]))
        names = [a["name"] for a in m.list_agents()]
        self.assertIn("Baby Angel", names)
        self.assertIn("SentinelAI", names)
        self.assertIn("Muse", names)
        self.assertNotIn("BAOS", names)
        second = m.seed_creox_agents()
        self.assertEqual(len(second["seeded"]), 0)
        self.assertEqual(len(m.list_agents()), len(SEED_AGENTS))

    def test_task_routes_to_seeded_agent(self):
        m = Mesh(":memory:")
        seeded = m.seed_creox_agents()["seeded"]
        baby = [a for a in seeded if a["name"] == "Baby Angel"][0]
        task = m.submit_task(baby["id"], baby["token"], "echo",
                             {"message": "hi"})
        self.assertEqual(task["assigned_agent_id"], baby["id"])
        done = m.execute_task(task["id"], baby["id"], baby["token"])
        self.assertEqual(done["status"], "done")
        self.assertEqual(done["result"], {"echo": "hi"})


if __name__ == "__main__":
    unittest.main()
