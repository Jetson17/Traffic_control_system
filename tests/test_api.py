"""
Unit Tests for Flask REST API Endpoints.
Covers health, state, simulation controls, vehicle additions, queue states,
graph routing (BFS and Dijkstra), comparison analytics, and error handling.
"""

import json
import unittest
from app import app, simulation


class TestApiEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        simulation.reset()

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("simulation_status", data)

    def test_state_endpoint(self):
        response = self.client.get("/api/state")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("status", data)
        self.assertIn("active_direction", data)
        self.assertIn("signals", data)
        self.assertIn("statistics", data)
        self.assertIn("queues", data)

    def test_simulation_controls(self):
        # Start
        res = self.client.post("/api/simulation/start")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(simulation.status, "RUNNING")

        # Pause
        res = self.client.post("/api/simulation/pause")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(simulation.status, "PAUSED")

        # Resume
        res = self.client.post("/api/simulation/resume")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(simulation.status, "RUNNING")

        # Reset
        res = self.client.post("/api/simulation/reset")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(simulation.status, "STOPPED")

    def test_manual_step(self):
        res = self.client.post("/api/simulation/step", json={"dt": 2})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(data["step_info"]["sim_time"], 2)

    def test_add_vehicle_valid(self):
        payload = {
            "direction": "North",
            "vehicle_type": "Car"
        }
        res = self.client.post("/api/vehicles/add", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["vehicle"]["direction"], "North")

    def test_add_emergency_vehicle(self):
        payload = {
            "direction": "East",
            "vehicle_type": "Ambulance"
        }
        res = self.client.post("/api/vehicles/add", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["vehicle"]["is_emergency"])
        self.assertEqual(data["vehicle"]["priority"], 1)

    def test_add_vehicle_invalid_direction(self):
        payload = {
            "direction": "NorthEast",
            "vehicle_type": "Car"
        }
        res = self.client.post("/api/vehicles/add", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)

    def test_add_vehicle_invalid_type(self):
        payload = {
            "direction": "South",
            "vehicle_type": "Airplane"
        }
        res = self.client.post("/api/vehicles/add", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)

    def test_get_queues(self):
        res = self.client.get("/api/queues")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["capacity"], 8)
        self.assertIn("North", data["queues"])
        self.assertIn("slots", data["queues"]["North"])

    def test_get_analytics(self):
        res = self.client.get("/api/analytics")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("statistics", data)
        self.assertIn("total_served", data["statistics"])

    def test_get_graph(self):
        res = self.client.get("/api/graph")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("nodes", data)
        self.assertIn("edges", data)
        self.assertGreater(len(data["nodes"]), 0)

    def test_graph_route_bfs(self):
        payload = {
            "source": "INT-6",
            "destination": "INT-1",
            "algorithm": "bfs"
        }
        res = self.client.post("/api/graph/route", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["found"])
        self.assertEqual(data["path"][0], "INT-6")
        self.assertEqual(data["path"][-1], "INT-1")

    def test_graph_route_dijkstra(self):
        payload = {
            "source": "INT-6",
            "destination": "INT-4",
            "algorithm": "dijkstra"
        }
        res = self.client.post("/api/graph/route", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["found"])
        self.assertEqual(data["algorithm"], "Dijkstra's Algorithm (Weighted Optimization)")

    def test_graph_route_invalid_node(self):
        payload = {
            "source": "NON_EXISTENT",
            "destination": "INT-1"
        }
        res = self.client.post("/api/graph/route", json=payload)
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertFalse(data["found"])

    def test_get_comparison(self):
        res = self.client.get("/api/comparison")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("micro_level_queue", data)
        self.assertIn("macro_level_graph", data)

    def test_get_events(self):
        res = self.client.get("/api/events")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("events", data)


if __name__ == "__main__":
    unittest.main()
