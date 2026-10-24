"""
Graph-Based Traffic Flow Analysis Implementation.

Module: algorithms.traffic_graph
Features:
    - Adjacency list representation of road intersections (vertices) and roads (edges)
    - Road capacity, current vehicle load, speed limits, and congestion metrics
    - Breadth-First Search (BFS) for minimum-hop unweighted path traversal
    - Dijkstra's Algorithm for weighted shortest/least-congested route calculation
    - Network connectivity analysis and congestion scoring
    - JSON export for interactive SVG rendering on the web dashboard
"""

from collections import deque
import heapq
from typing import Dict, List, Optional, Tuple, Any


class Intersection:
    """Represents a traffic junction / vertex in the road network."""

    def __init__(self, node_id: str, name: str, x: int, y: int, node_type: str = "Standard"):
        self.node_id = str(node_id)
        self.name = str(name)
        self.x = int(x)
        self.y = int(y)
        self.node_type = str(node_type)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.node_id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "type": self.node_type
        }


class RoadEdge:
    """Represents a connecting road / directed edge between two intersections."""

    def __init__(
        self,
        from_node: str,
        to_node: str,
        distance_km: float,
        capacity: int = 100,
        current_vehicles: int = 20,
        speed_limit_kmh: float = 50.0
    ):
        self.from_node = str(from_node)
        self.to_node = str(to_node)
        self.distance_km = float(distance_km)
        self.capacity = max(1, int(capacity))
        self.current_vehicles = max(0, int(current_vehicles))
        self.speed_limit_kmh = max(10.0, float(speed_limit_kmh))

    @property
    def congestion_ratio(self) -> float:
        """Volume to capacity ratio, clamped between 0.0 and 1.0 (or higher under jam)."""
        return round(self.current_vehicles / self.capacity, 2)

    @property
    def travel_cost_minutes(self) -> float:
        """
        Calculated effective travel time incorporating BPR (Bureau of Public Roads) delay formula:
        travel_time = free_flow_time * (1 + alpha * (volume/capacity)^beta)
        """
        free_flow_time = (self.distance_km / self.speed_limit_kmh) * 60.0
        congestion_penalty = 1.0 + (1.2 * (self.congestion_ratio ** 2))
        return round(free_flow_time * congestion_penalty, 2)

    def to_dict(self) -> Dict[str, Any]:
        ratio = self.congestion_ratio
        if ratio < 0.4:
            status = "Low"
            color = "#10b981"  # Emerald
        elif ratio < 0.75:
            status = "Moderate"
            color = "#f59e0b"  # Amber
        else:
            status = "Heavy"
            color = "#ef4444"  # Rose Red

        return {
            "from": self.from_node,
            "to": self.to_node,
            "distance_km": self.distance_km,
            "capacity": self.capacity,
            "current_vehicles": self.current_vehicles,
            "speed_limit_kmh": self.speed_limit_kmh,
            "congestion_ratio": ratio,
            "congestion_status": status,
            "stroke_color": color,
            "travel_cost_minutes": self.travel_cost_minutes
        }


class TrafficGraph:
    """
    Traffic Road Network represented via an Adjacency List.
    Provides graph algorithms for routing, congestion estimation, and topological analysis.
    """

    def __init__(self):
        self.nodes: Dict[str, Intersection] = {}
        self.adjacency: Dict[str, List[RoadEdge]] = {}

    def add_intersection(self, node_id: str, name: str, x: int, y: int, node_type: str = "Standard") -> None:
        """Add a vertex to the road graph."""
        self.nodes[node_id] = Intersection(node_id, name, x, y, node_type)
        if node_id not in self.adjacency:
            self.adjacency[node_id] = []

    def add_road(
        self,
        from_node: str,
        to_node: str,
        distance_km: float,
        capacity: int = 100,
        current_vehicles: int = 20,
        speed_limit_kmh: float = 50.0,
        bidirectional: bool = True
    ) -> None:
        """Add a road connection (directed or bidirectional) between two vertices."""
        if from_node not in self.nodes or to_node not in self.nodes:
            raise ValueError(f"Both nodes ({from_node}, {to_node}) must exist before adding a road.")

        edge_fwd = RoadEdge(from_node, to_node, distance_km, capacity, current_vehicles, speed_limit_kmh)
        self.adjacency[from_node].append(edge_fwd)

        if bidirectional:
            edge_rev = RoadEdge(to_node, from_node, distance_km, capacity, current_vehicles, speed_limit_kmh)
            self.adjacency[to_node].append(edge_rev)

    def update_road_traffic(self, from_node: str, to_node: str, vehicles_delta: int) -> None:
        """Dynamically update vehicle count on an existing road."""
        if from_node in self.adjacency:
            for edge in self.adjacency[from_node]:
                if edge.to_node == to_node:
                    edge.current_vehicles = max(0, edge.current_vehicles + vehicles_delta)

    def bfs_shortest_path(self, start_id: str, target_id: str) -> Dict[str, Any]:
        """
        Breadth-First Search (BFS) to find the path with the minimum number of intersections (hops).
        Time Complexity: O(V + E)
        Space Complexity: O(V)
        Notice: BFS computes the unweighted minimum-hop route, not the weighted minimum-cost route.
        """
        if start_id not in self.nodes or target_id not in self.nodes:
            return {
                "found": False,
                "error": f"One or both intersection IDs '{start_id}', '{target_id}' do not exist."
            }

        if start_id == target_id:
            return {
                "found": True,
                "algorithm": "Breadth-First Search (BFS)",
                "path": [start_id],
                "path_names": [self.nodes[start_id].name],
                "hops": 0,
                "edges": [],
                "total_distance_km": 0.0,
                "total_cost_minutes": 0.0,
                "average_congestion_ratio": 0.0,
                "traversal_order": [start_id],
                "explanation": "Origin and destination are identical."
            }

        queue = deque([start_id])
        visited = {start_id}
        parent: Dict[str, Tuple[Optional[str], Optional[RoadEdge]]] = {start_id: (None, None)}
        traversal_order = []

        while queue:
            curr = queue.popleft()
            traversal_order.append(curr)

            if curr == target_id:
                break

            for edge in self.adjacency.get(curr, []):
                neighbor = edge.to_node
                if neighbor not in visited:
                    visited.add(neighbor)
                    parent[neighbor] = (curr, edge)
                    queue.append(neighbor)

        if target_id not in parent or parent[target_id][0] is None and start_id != target_id:
            return {
                "found": False,
                "algorithm": "Breadth-First Search (BFS)",
                "error": f"No accessible route exists from {self.nodes[start_id].name} to {self.nodes[target_id].name}.",
                "traversal_order": traversal_order
            }

        # Reconstruct path from destination backwards
        path = []
        path_edges = []
        curr = target_id
        while curr is not None:
            path.append(curr)
            prev_node, edge = parent[curr]
            if edge is not None:
                path_edges.append(edge)
            curr = prev_node

        path.reverse()
        path_edges.reverse()

        total_distance = sum(e.distance_km for e in path_edges)
        total_cost = sum(e.travel_cost_minutes for e in path_edges)
        avg_congestion = (
            sum(e.congestion_ratio for e in path_edges) / len(path_edges)
            if path_edges else 0.0
        )

        return {
            "found": True,
            "algorithm": "Breadth-First Search (BFS)",
            "path": path,
            "path_names": [self.nodes[nid].name for nid in path],
            "hops": len(path) - 1,
            "edges": [e.to_dict() for e in path_edges],
            "total_distance_km": round(total_distance, 2),
            "total_cost_minutes": round(total_cost, 2),
            "average_congestion_ratio": round(avg_congestion, 2),
            "traversal_order": traversal_order,
            "explanation": "BFS optimizes for the fewest intermediate intersections (minimum hops in unweighted graph)."
        }

    def dijkstra_shortest_path(self, start_id: str, target_id: str, weight_key: str = "travel_cost") -> Dict[str, Any]:
        """
        Dijkstra's Algorithm to find the optimal weighted path based on travel time and congestion.
        Time Complexity: O((V + E) log V)
        Space Complexity: O(V)
        """
        if start_id not in self.nodes or target_id not in self.nodes:
            return {
                "found": False,
                "error": f"One or both intersection IDs '{start_id}', '{target_id}' do not exist."
            }

        distances = {node: float("inf") for node in self.nodes}
        distances[start_id] = 0.0
        parent: Dict[str, Tuple[Optional[str], Optional[RoadEdge]]] = {start_id: (None, None)}

        # Priority queue storing (cost, node_id)
        pq = [(0.0, start_id)]
        visited = set()

        while pq:
            curr_dist, curr_node = heapq.heappop(pq)

            if curr_node in visited:
                continue
            visited.add(curr_node)

            if curr_node == target_id:
                break

            for edge in self.adjacency.get(curr_node, []):
                neighbor = edge.to_node
                weight = edge.travel_cost_minutes if weight_key == "travel_cost" else edge.distance_km
                new_dist = curr_dist + weight

                if new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    parent[neighbor] = (curr_node, edge)
                    heapq.heappush(pq, (new_dist, neighbor))

        if target_id not in parent or (parent[target_id][0] is None and start_id != target_id):
            return {
                "found": False,
                "algorithm": "Dijkstra's Shortest Path",
                "error": f"No road connection exists from {self.nodes[start_id].name} to {self.nodes[target_id].name}."
            }

        # Reconstruct path
        path = []
        path_edges = []
        curr = target_id
        while curr is not None:
            path.append(curr)
            prev_node, edge = parent[curr]
            if edge is not None:
                path_edges.append(edge)
            curr = prev_node

        path.reverse()
        path_edges.reverse()

        total_distance = sum(e.distance_km for e in path_edges)
        total_cost = sum(e.travel_cost_minutes for e in path_edges)
        avg_congestion = (
            sum(e.congestion_ratio for e in path_edges) / len(path_edges)
            if path_edges else 0.0
        )

        return {
            "found": True,
            "algorithm": "Dijkstra's Algorithm (Weighted Optimization)",
            "path": path,
            "path_names": [self.nodes[nid].name for nid in path],
            "hops": len(path) - 1,
            "edges": [e.to_dict() for e in path_edges],
            "total_distance_km": round(total_distance, 2),
            "total_cost_minutes": round(total_cost, 2),
            "average_congestion_ratio": round(avg_congestion, 2),
            "explanation": "Dijkstra optimizes for minimum travel time by factoring real-time road congestion and delay."
        }

    def analyze_connectivity(self) -> Dict[str, Any]:
        """
        Analyze connected components and overall network reachability using BFS.
        """
        visited = set()
        components = []

        for node in self.nodes:
            if node not in visited:
                comp = []
                q = deque([node])
                visited.add(node)
                while q:
                    c = q.popleft()
                    comp.append(c)
                    for edge in self.adjacency.get(c, []):
                        if edge.to_node not in visited:
                            visited.add(edge.to_node)
                            q.append(edge.to_node)
                components.append(comp)

        is_connected = (len(components) == 1) if self.nodes else False
        return {
            "total_intersections": len(self.nodes),
            "total_connected_components": len(components),
            "is_fully_connected": is_connected,
            "components": components
        }

    def calculate_congestion_score(self) -> float:
        """
        Calculate city-wide average traffic congestion percentage (0.0% to 100.0%).
        """
        total_edges = 0
        sum_congestion = 0.0
        for edge_list in self.adjacency.values():
            for edge in edge_list:
                total_edges += 1
                sum_congestion += edge.congestion_ratio

        if total_edges == 0:
            return 0.0
        return round((sum_congestion / total_edges) * 100.0, 1)

    def export_graph_data(self) -> Dict[str, Any]:
        """Export comprehensive graph topology, nodes, edges, and metrics for UI rendering."""
        edge_dicts = []
        seen_pairs = set()

        for u, edges in self.adjacency.items():
            for edge in edges:
                pair = tuple(sorted([edge.from_node, edge.to_node]))
                edge_dicts.append(edge.to_dict())

        return {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": edge_dicts,
            "network_congestion_score": self.calculate_congestion_score(),
            "connectivity": self.analyze_connectivity()
        }


def create_sample_city_network() -> TrafficGraph:
    """
    Construct a sample smart-city road network with 7 intersections,
    multiple alternate corridors, variable road capacities, and realistic congestion.
    """
    graph = TrafficGraph()

    # 7 Intersections with coordinates tailored for a 600x420 SVG canvas
    graph.add_intersection("INT-1", "Central Junction", 300, 210, "Central Hub")
    graph.add_intersection("INT-2", "North Metro Terminal", 300, 50, "Transit Hub")
    graph.add_intersection("INT-3", "East Tech Corridor", 520, 140, "Commercial Park")
    graph.add_intersection("INT-4", "South Ring Interchange", 300, 370, "Highway Exit")
    graph.add_intersection("INT-5", "West University Gate", 80, 270, "Education Sector")
    graph.add_intersection("INT-6", "Uptown Health City", 90, 80, "Emergency / Hospital")
    graph.add_intersection("INT-7", "Harbour Logistics Point", 510, 330, "Industrial Port")

    # Connect intersections with realistic road parameters (distance km, capacity, current_vehicles, speed km/h)
    # North Axis
    graph.add_road("INT-2", "INT-1", distance_km=3.2, capacity=120, current_vehicles=75, speed_limit_kmh=50)
    # South Axis
    graph.add_road("INT-1", "INT-4", distance_km=3.5, capacity=150, current_vehicles=60, speed_limit_kmh=60)
    # East Axis
    graph.add_road("INT-1", "INT-3", distance_km=4.0, capacity=100, current_vehicles=85, speed_limit_kmh=45)
    # West Axis
    graph.add_road("INT-1", "INT-5", distance_km=3.8, capacity=110, current_vehicles=40, speed_limit_kmh=50)

    # Perimeter / Alternate Bypass Routes
    # Uptown Hospital connects to North Metro and West University
    graph.add_road("INT-6", "INT-2", distance_km=2.6, capacity=90, current_vehicles=30, speed_limit_kmh=50)
    graph.add_road("INT-6", "INT-5", distance_km=3.1, capacity=80, current_vehicles=25, speed_limit_kmh=45)

    # East Tech connects to Harbour Port
    graph.add_road("INT-3", "INT-7", distance_km=3.4, capacity=130, current_vehicles=55, speed_limit_kmh=50)
    # Harbour Port connects to South Ring
    graph.add_road("INT-7", "INT-4", distance_km=3.9, capacity=160, current_vehicles=110, speed_limit_kmh=60)
    # West University connects to South Ring
    graph.add_road("INT-5", "INT-4", distance_km=4.2, capacity=100, current_vehicles=35, speed_limit_kmh=50)

    return graph
