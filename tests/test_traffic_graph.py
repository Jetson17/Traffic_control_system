"""
Unit Tests for TrafficGraph.
Covers BFS traversal, Dijkstra routing, disconnected components, and congestion scoring.
"""

import unittest
from algorithms.traffic_graph import TrafficGraph, create_sample_city_network


class TestTrafficGraph(unittest.TestCase):

    def setUp(self):
        self.graph = create_sample_city_network()

    def test_sample_network_initialization(self):
        export = self.graph.export_graph_data()
        self.assertEqual(len(export["nodes"]), 7)
        self.assertGreater(len(export["edges"]), 10)
        self.assertGreater(export["network_congestion_score"], 0)
        self.assertTrue(export["connectivity"]["is_fully_connected"])

    def test_bfs_shortest_path_found(self):
        # Route from Uptown Hospital (INT-6) to Central Junction (INT-1)
        res = self.graph.bfs_shortest_path("INT-6", "INT-1")
        self.assertTrue(res["found"])
        self.assertEqual(res["algorithm"], "Breadth-First Search (BFS)")
        self.assertEqual(res["path"][0], "INT-6")
        self.assertEqual(res["path"][-1], "INT-1")
        # Direct route has 2 hops: INT-6 -> INT-2 -> INT-1 or INT-6 -> INT-5 -> INT-1
        self.assertEqual(res["hops"], 2)
        self.assertGreater(res["total_distance_km"], 0)
        self.assertGreater(res["total_cost_minutes"], 0)

    def test_bfs_same_source_and_destination(self):
        res = self.graph.bfs_shortest_path("INT-1", "INT-1")
        self.assertTrue(res["found"])
        self.assertEqual(res["hops"], 0)
        self.assertEqual(res["path"], ["INT-1"])

    def test_bfs_disconnected_node(self):
        # Add an isolated node
        self.graph.add_intersection("INT-ISOLATED", "Remote Island", 600, 50, "Isolated")
        res = self.graph.bfs_shortest_path("INT-1", "INT-ISOLATED")
        self.assertFalse(res["found"])
        self.assertIn("No accessible route", res["error"])

    def test_dijkstra_path(self):
        res = self.graph.dijkstra_shortest_path("INT-6", "INT-4")
        self.assertTrue(res["found"])
        self.assertEqual(res["path"][0], "INT-6")
        self.assertEqual(res["path"][-1], "INT-4")
        self.assertGreater(res["total_cost_minutes"], 0)

    def test_connectivity_analysis(self):
        conn = self.graph.analyze_connectivity()
        self.assertEqual(conn["total_intersections"], 7)
        self.assertEqual(conn["total_connected_components"], 1)
        self.assertTrue(conn["is_fully_connected"])

        # Add an isolated node and re-check
        self.graph.add_intersection("INT-99", "Far Outpost", 900, 900)
        conn2 = self.graph.analyze_connectivity()
        self.assertEqual(conn2["total_connected_components"], 2)
        self.assertFalse(conn2["is_fully_connected"])

    def test_invalid_node_handling(self):
        res = self.graph.bfs_shortest_path("INVALID_1", "INT-1")
        self.assertFalse(res["found"])


if __name__ == "__main__":
    unittest.main()
