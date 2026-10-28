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

    def test_queue_operations_use_shared_simulation_queue(self):
        front = self.client.post("/api/queues/North/peek").get_json()["vehicle"]
        response = self.client.post("/api/queues/North/dequeue")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["vehicle"]["id"], front["id"])
        state = self.client.get("/api/state").get_json()
        self.assertEqual(state["queues"]["North"]["size"], 1)
        self.assertEqual(state["queues"]["North"]["fifo_items"][0]["id"], "VEH-0002")
        self.assertEqual(state["statistics"]["total_served"], 0)

    def test_queue_operations_handle_empty_and_clear(self):
        self.client.post("/api/queues/North/clear")
        dequeue = self.client.post("/api/queues/North/dequeue")
        peek = self.client.post("/api/queues/North/peek")
        self.assertEqual(dequeue.status_code, 400)
        self.assertEqual(peek.status_code, 400)

        self.client.post("/api/vehicles/add", json={"direction": "North", "vehicle_type": "Car"})
        clear = self.client.post("/api/queues/North/clear")
        self.assertEqual(clear.status_code, 200)
        self.assertEqual(clear.get_json()["removed_count"], 1)
        state = self.client.get("/api/state").get_json()
        self.assertEqual(state["queues"]["North"]["size"], 0)
        self.assertEqual(state["statistics"]["total_served"], 0)

    def test_queue_enqueue_rejects_overflow_without_overwriting(self):
        self.client.post("/api/queues/North/clear")
        for _ in range(simulation.queue_capacity):
            response = self.client.post(
                "/api/vehicles/add",
                json={"direction": "North", "vehicle_type": "Car"}
            )
            self.assertEqual(response.status_code, 201)

        overflow = self.client.post(
            "/api/vehicles/add",
            json={"direction": "North", "vehicle_type": "Car"}
        )
        self.assertEqual(overflow.status_code, 400)
        queue = self.client.get("/api/queues").get_json()["queues"]["North"]
        self.assertTrue(queue["is_full"])
        self.assertEqual(queue["size"], simulation.queue_capacity)
        self.assertEqual(queue["fifo_items"][0]["id"], "VEH-0008")

    def test_ambulance_add_updates_live_emergency_signals(self):
        self.client.post("/api/simulation/start")
        response = self.client.post("/api/vehicles/add", json={
            "direction": "East",
            "vehicle_type": "Ambulance"
        })

        self.assertEqual(response.status_code, 201)
        state = self.client.get("/api/state").get_json()
        self.assertEqual(state["priority_state"], "EMERGENCY_PREPARATION")
        self.assertEqual(state["emergency"]["direction"], "East")
        self.assertEqual(state["signals"]["North"], "YELLOW")
        self.assertEqual(state["signals"]["East"], "RED")

        self.client.post("/api/simulation/reset")
        state = self.client.get("/api/state").get_json()
        self.assertEqual(state["priority_state"], "NORMAL")
        self.assertIsNone(state["emergency"])

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

    def test_graph_bfs_traversal(self):
        response = self.client.post("/api/graph/bfs", json={"source": "INT-6"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["found"])
        self.assertEqual(data["start"], "INT-6")
        self.assertEqual(data["traversal_order"][0], "INT-6")
        self.assertEqual(len(data["steps"]), data["vertices_visited"])
        self.assertEqual(data["reachable"], data["traversal_order"])

    def test_graph_bfs_rejects_missing_or_invalid_start(self):
        missing = self.client.post("/api/graph/bfs", json={})
        invalid = self.client.post("/api/graph/bfs", json={"source": "MISSING"})
        malformed = self.client.post("/api/graph/bfs", json={"source": []})
        non_object = self.client.post("/api/graph/bfs", json=[])
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(invalid.status_code, 404)
        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(non_object.status_code, 400)
        self.assertIn("error", invalid.get_json())

    def test_graph_bfs_reports_disconnected_vertices(self):
        simulation.graph.add_intersection("INT-ISOLATED", "Remote Island", 600, 50)
        response = self.client.post("/api/graph/bfs", json={"source": "INT-1"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data["is_fully_reachable"])
        self.assertEqual(data["unreachable"], ["INT-ISOLATED"])

    def test_graph_bfs_does_not_change_simulation_state(self):
        self.client.post("/api/vehicles/add", json={
            "direction": "East",
            "vehicle_type": "Ambulance"
        })
        before = self.client.get("/api/state").get_json()
        response = self.client.post("/api/graph/bfs", json={"source": "INT-4"})
        after = self.client.get("/api/state").get_json()
        self.assertEqual(response.status_code, 200)
        for key in ("queues", "signals", "statistics", "priority_state", "emergency",
                    "active_direction", "status"):
            self.assertEqual(after[key], before[key])

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

    def test_graph_route_rejects_unknown_algorithm(self):
        response = self.client.post("/api/graph/route", json={
            "source": "INT-6",
            "destination": "INT-1",
            "algorithm": "astar"
        })
        self.assertEqual(response.status_code, 400)

    def test_get_comparison(self):
        res = self.client.get("/api/comparison?source=INT-6&destination=INT-4")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("micro_level_queue", data)
        self.assertIn("macro_level_graph", data)
        analytics = data["live_analytics"]
        state = self.client.get("/api/state").get_json()
        self.assertEqual(analytics["queue_capacity_per_direction"], 8)
        self.assertEqual(analytics["queue_capacity_total"], 32)
        self.assertEqual(analytics["vehicles_waiting"], state["statistics"]["total_waiting"])
        self.assertEqual(analytics["vehicles_served"], state["statistics"]["total_served"])
        self.assertEqual(analytics["vertices"], 7)
        self.assertEqual(analytics["road_links"], 9)

        bfs = self.client.post("/api/graph/route", json={
            "source": "INT-6",
            "destination": "INT-4",
            "algorithm": "bfs"
        }).get_json()
        dijkstra = self.client.post("/api/graph/route", json={
            "source": "INT-6",
            "destination": "INT-4",
            "algorithm": "dijkstra"
        }).get_json()
        self.assertEqual(analytics["bfs"], bfs)
        self.assertEqual(analytics["dijkstra"], dijkstra)
        self.assertIn("minimum-hop", data["macro_level_graph"]["algorithm"])
        self.assertIn("minimum travel-cost", data["macro_level_graph"]["algorithm"])

    def test_comparison_handles_missing_route_nodes(self):
        response = self.client.get(
            "/api/comparison?source=missing&destination=INT-4"
        )
        self.assertEqual(response.status_code, 200)
        analytics = response.get_json()["live_analytics"]
        self.assertFalse(analytics["bfs"]["found"])
        self.assertFalse(analytics["dijkstra"]["found"])
        self.assertEqual(analytics["origin"]["id"], "missing")
        self.assertIsNone(analytics["origin"]["name"])

    def test_comparison_analytics_follow_live_queue_and_service_state(self):
        for direction in ("North", "East", "South", "West"):
            self.client.post(f"/api/queues/{direction}/clear")

        self.client.post("/api/vehicles/add", json={
            "direction": "North",
            "vehicle_type": "Car"
        })
        simulation.step()
        self.client.post("/api/vehicles/add", json={
            "direction": "East",
            "vehicle_type": "Bus"
        })

        analytics = self.client.get(
            "/api/comparison?source=INT-1&destination=INT-7"
        ).get_json()["live_analytics"]
        self.assertEqual(analytics["vehicles_waiting"], 1)
        self.assertEqual(analytics["vehicles_served"], 1)
        self.assertEqual(analytics["queue_utilization_percent"], 3.1)
        self.assertEqual(analytics["origin"]["id"], "INT-1")
        self.assertEqual(analytics["destination"]["id"], "INT-7")

        self.client.post("/api/queues/East/clear")
        empty_analytics = self.client.get(
            "/api/comparison?source=INT-1&destination=INT-7"
        ).get_json()["live_analytics"]
        self.assertEqual(empty_analytics["vehicles_waiting"], 0)
        self.assertEqual(empty_analytics["queue_utilization_percent"], 0)

    def test_get_events(self):
        res = self.client.get("/api/events")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("events", data)


if __name__ == "__main__":
    unittest.main()
