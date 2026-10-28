"""
Simulation Engine for Traffic Signal Control System.

Module: algorithms.simulation
Features:
    - Centralized thread-safe simulation manager
    - Background simulation clock with Start, Pause, Resume, Reset, and Manual Step
    - Queue-based vehicle departure processing during Green phase
    - Emergency vehicle injection and priority tracking
    - Real-time performance metrics (waiting times, throughput, fairness)
    - Experimental queue vs graph comparison engine
"""

from datetime import datetime
import threading
import time
from typing import Dict, List, Optional, Any
from algorithms.circular_queue import CircularQueue, QueueOverflowError
from algorithms.signal_scheduler import (
    EmergencyPriorityState,
    SignalScheduler,
    SchedulingStrategy,
    DIRECTIONS,
    SignalState
)
from algorithms.traffic_graph import TrafficGraph, create_sample_city_network


class TrafficSimulationManager:
    """
    Central Coordinator managing directional circular queues, signal scheduler,
    traffic graph, simulation clock, and performance analytics.

    Emergency priority is approach-level: ordinary vehicles already ahead of an
    emergency vehicle retain FIFO order, then the emergency vehicle is served.
    """

    def __init__(self, queue_capacity: int = 8):
        self.queue_capacity = queue_capacity
        self.lock = threading.RLock()

        # Core DSA Components
        self.queues: Dict[str, CircularQueue] = {
            direction: CircularQueue(capacity=self.queue_capacity)
            for direction in DIRECTIONS
        }
        self.scheduler = SignalScheduler(
            green_duration=8,
            yellow_duration=3,
            strategy=SchedulingStrategy.ADAPTIVE_PRIORITY
        )
        self.graph: TrafficGraph = create_sample_city_network()

        # Simulation Clock & State
        self.status: str = "STOPPED"  # STOPPED, RUNNING, PAUSED
        self.sim_time: int = 0  # Simulated elapsed seconds
        self.vehicle_id_counter: int = 1
        self.emergency_id_counter: int = 1

        # Real-time Metrics
        self.total_arrived: int = 0
        self.total_served: int = 0
        self.total_waiting_time: float = 0.0
        self.directional_served: Dict[str, int] = {d: 0 for d in DIRECTIONS}
        self.directional_wait_sum: Dict[str, float] = {d: 0.0 for d in DIRECTIONS}
        self.departed_vehicles: List[Dict[str, Any]] = []

        # Background Thread Control
        self._ticker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Seed ordinary traffic only so emergency preemption is demonstrated on demand.
        self._seed_initial_vehicles()

    def _seed_initial_vehicles(self) -> None:
        """Seed a few realistic sample vehicles so the user immediately sees queues and state."""
        sample_batch = [
            ("North", "Car", False, 0),
            ("North", "Bus", False, 0),
            ("East", "Car", False, 0),
            ("East", "Car", False, 0),
            ("South", "Truck", False, 0),
            ("West", "Car", False, 0),
            ("West", "Car", False, 0),
        ]
        for direction, v_type, is_emg, prio in sample_batch:
            self.add_vehicle(direction, v_type, is_emergency=is_emg, priority=prio, timestamp=0)

    def add_vehicle(
        self,
        direction: str,
        vehicle_type: str,
        is_emergency: bool = False,
        priority: int = 0,
        timestamp: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create and enqueue a new vehicle into the specified directional circular queue.
        """
        with self.lock:
            if direction not in DIRECTIONS:
                raise ValueError(f"Invalid direction '{direction}'. Must be one of {DIRECTIONS}.")

            if timestamp is None:
                timestamp = self.sim_time

            # Generate unique ID
            if is_emergency or vehicle_type in ["Ambulance", "Fire Engine", "Police Vehicle"]:
                is_emergency = True
                prefix = "EMG"
                if vehicle_type == "Ambulance":
                    priority = 1
                elif vehicle_type == "Fire Engine":
                    priority = 2
                elif vehicle_type == "Police Vehicle":
                    priority = 3
                else:
                    priority = 1
                v_id = f"{prefix}-{self.emergency_id_counter:03d}"
                self.emergency_id_counter += 1
            else:
                v_id = f"VEH-{self.vehicle_id_counter:04d}"
                self.vehicle_id_counter += 1

            vehicle = {
                "id": v_id,
                "direction": direction,
                "type": vehicle_type,
                "is_emergency": is_emergency,
                "priority": priority,
                "arrival_time": timestamp,
                "created_at": datetime.now().strftime("%H:%M:%S")
            }

            queue = self.queues[direction]
            try:
                queue.enqueue(vehicle)
                self.total_arrived += 1
                self.scheduler.log_event(
                    "VEHICLE_ARRIVED",
                    f"{'🚨 EMERGENCY ' if is_emergency else ''}{vehicle_type} [{v_id}] queued at {direction}.",
                    {"vehicle_id": v_id, "direction": direction, "is_emergency": is_emergency}
                )
                self.scheduler.update_emergency_priority(self.queues, self.sim_time)
                return {
                    "success": True,
                    "vehicle": vehicle,
                    "queue_length": len(queue),
                    "message": f"Vehicle {v_id} queued at {direction}."
                }
            except QueueOverflowError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Queue at {direction} is at maximum capacity ({self.queue_capacity})."
                }

    def step(self, dt: int = 1) -> Dict[str, Any]:
        """
        Advance the simulation clock deterministically by dt seconds.
        Performs signal phase transitions, processes vehicle departures during GREEN,
        and computes updated metrics.
        """
        with self.lock:
            self.sim_time += dt

            # Advance signal scheduler
            sched_res = self.scheduler.advance_time_step(dt, self.queues, current_sim_time=self.sim_time)
            active_dir = sched_res["active_direction"]
            current_phase = sched_res["current_phase"]

            departed_this_step = []

            # Process vehicle service during GREEN phase
            if current_phase == SignalState.GREEN.value:
                active_queue = self.queues[active_dir]
                # Process vehicle departure at a safe clearance rate (e.g., 1 vehicle per 1-2 sec of green)
                # To provide dynamic visual movement, dequeue 1 vehicle if queue is non-empty
                if not active_queue.is_empty():
                    vehicle = active_queue.dequeue()
                    wait_time = max(0, self.sim_time - vehicle["arrival_time"])
                    vehicle["departure_time"] = self.sim_time
                    vehicle["waiting_time"] = wait_time

                    self.total_served += 1
                    self.total_waiting_time += wait_time
                    self.directional_served[active_dir] += 1
                    self.directional_wait_sum[active_dir] += wait_time

                    self.departed_vehicles.append(vehicle)
                    if len(self.departed_vehicles) > 50:
                        self.departed_vehicles.pop(0)

                    departed_this_step.append(vehicle)

                    self.scheduler.log_event(
                        "VEHICLE_DEPARTED",
                        f"Vehicle {vehicle['id']} ({vehicle['type']}) cleared {active_dir} intersection after {wait_time}s wait.",
                        {"vehicle_id": vehicle["id"], "direction": active_dir, "wait_time": wait_time}
                    )
                    self.scheduler.update_emergency_priority(self.queues, self.sim_time)

            # Sync road traffic with city graph for CBD intersection
            # INT-1 (Central Junction) reflects local queues
            self._update_graph_dynamics()

            sched_res.update({
                "active_direction": self.scheduler.active_direction,
                "current_phase": self.scheduler.current_phase.value,
                "signals": self.scheduler.get_signal_states(),
                "priority_state": self.scheduler.priority_state.value,
                "emergency_direction": self.scheduler.emergency_direction,
                "emergency_vehicle_id": self.scheduler.emergency_vehicle_id
            })

            return {
                "sim_time": self.sim_time,
                "status": self.status,
                "scheduler": sched_res,
                "departed_this_step": departed_this_step
            }

    def _update_graph_dynamics(self) -> None:
        """Propagate current intersection queue loads into road graph edges."""
        total_waiting = sum(len(q) for q in self.queues.values())
        # Update traffic load on connecting edges of INT-1
        self.graph.update_road_traffic("INT-2", "INT-1", 1 if total_waiting > 10 else -1)
        self.graph.update_road_traffic("INT-1", "INT-4", 1 if self.directional_served["South"] > 5 else 0)

    def start(self) -> Dict[str, Any]:
        """Start the background real-time simulation loop."""
        with self.lock:
            if self.status == "RUNNING":
                return {"message": "Simulation is already running.", "status": self.status}

            self.status = "RUNNING"
            self._stop_event.clear()

            if self._ticker_thread is None or not self._ticker_thread.is_alive():
                self._ticker_thread = threading.Thread(target=self._run_ticker, daemon=True)
                self._ticker_thread.start()

            self.scheduler.log_event("SYSTEM", "Simulation started.", {})
            return {"message": "Simulation started successfully.", "status": self.status}

    def pause(self) -> Dict[str, Any]:
        """Pause the running simulation."""
        with self.lock:
            if self.status == "PAUSED":
                return {"message": "Simulation is already paused.", "status": self.status}
            if self.status == "STOPPED":
                return {"message": "Simulation is stopped. Cannot pause.", "status": self.status}

            self.status = "PAUSED"
            self.scheduler.log_event("SYSTEM", "Simulation paused.", {})
            return {"message": "Simulation paused.", "status": self.status}

    def resume(self) -> Dict[str, Any]:
        """Resume a paused simulation."""
        with self.lock:
            if self.status == "RUNNING":
                return {"message": "Simulation is already running.", "status": self.status}

            self.status = "RUNNING"
            if self._ticker_thread is None or not self._ticker_thread.is_alive():
                self._stop_event.clear()
                self._ticker_thread = threading.Thread(target=self._run_ticker, daemon=True)
                self._ticker_thread.start()

            self.scheduler.log_event("SYSTEM", "Simulation resumed.", {})
            return {"message": "Simulation resumed.", "status": self.status}

    def reset(self) -> Dict[str, Any]:
        """Reset the simulation back to clean initial state."""
        with self.lock:
            self.status = "STOPPED"
            self._stop_event.set()

            self.sim_time = 0
            self.vehicle_id_counter = 1
            self.emergency_id_counter = 1
            self.total_arrived = 0
            self.total_served = 0
            self.total_waiting_time = 0.0
            self.directional_served = {d: 0 for d in DIRECTIONS}
            self.directional_wait_sum = {d: 0.0 for d in DIRECTIONS}
            self.departed_vehicles.clear()

            for q in self.queues.values():
                q.clear()

            self.scheduler.reset()
            self.graph = create_sample_city_network()
            self._seed_initial_vehicles()

            self.scheduler.log_event("SYSTEM", "Simulation reset to initial demonstration state.", {})
            return {"message": "Simulation reset successfully.", "status": self.status}

    def _run_ticker(self) -> None:
        """Background thread advancing simulation time step-by-step."""
        while not self._stop_event.is_set():
            time.sleep(1.0)
            if self.status == "RUNNING":
                try:
                    self.step(dt=1)
                except Exception as e:
                    print(f"Error in simulation ticker: {e}")

    def get_complete_state(self) -> Dict[str, Any]:
        """Export comprehensive simulation state for frontend polling."""
        with self.lock:
            total_waiting = sum(len(q) for q in self.queues.values())
            emergency_waiting = 0
            directional_waiting = {}

            for d in DIRECTIONS:
                q = self.queues[d]
                directional_waiting[d] = len(q)
                for item in q.get_fifo_items():
                    if (
                        item.get("is_emergency", False)
                        or str(item.get("type", item.get("vehicle_type", ""))).casefold() == "ambulance"
                    ):
                        emergency_waiting += 1

            avg_wait = (
                round(self.total_waiting_time / self.total_served, 2)
                if self.total_served > 0 else 0.0
            )

            # Throughput = vehicles served per simulated minute
            throughput = (
                round((self.total_served / max(1, self.sim_time)) * 60.0, 2)
                if self.sim_time > 0 else 0.0
            )

            dir_avg_wait = {}
            for d in DIRECTIONS:
                served_d = self.directional_served[d]
                dir_avg_wait[d] = (
                    round(self.directional_wait_sum[d] / served_d, 2)
                    if served_d > 0 else 0.0
                )

            return {
                "status": self.status,
                "sim_time": self.sim_time,
                "active_direction": self.scheduler.active_direction,
                "current_phase": self.scheduler.current_phase.value,
                "priority_state": self.scheduler.priority_state.value,
                "emergency": (
                    {
                        "state": self.scheduler.priority_state.value,
                        "direction": self.scheduler.emergency_direction,
                        "vehicle_id": self.scheduler.emergency_vehicle_id
                    }
                    if self.scheduler.priority_state != EmergencyPriorityState.NORMAL
                    else None
                ),
                "phase_elapsed": self.scheduler.phase_elapsed_time,
                "remaining_phase_time": (
                    None
                    if self.scheduler.priority_state == EmergencyPriorityState.EMERGENCY_ACTIVE
                    else max(0, self.scheduler.green_duration - self.scheduler.phase_elapsed_time)
                    if self.scheduler.current_phase == SignalState.GREEN
                    else max(0, self.scheduler.yellow_duration - self.scheduler.phase_elapsed_time)
                ),
                "signals": self.scheduler.get_signal_states(),
                "config": {
                    "green_duration": self.scheduler.green_duration,
                    "yellow_duration": self.scheduler.yellow_duration,
                    "strategy": self.scheduler.strategy.value,
                    "queue_capacity": self.queue_capacity,
                    "max_emergency_consecutive": self.scheduler.max_emergency_consecutive
                },
                "statistics": {
                    "total_waiting": total_waiting,
                    "total_served": self.total_served,
                    "total_arrived": self.total_arrived,
                    "average_waiting_time": avg_wait,
                    "emergency_waiting": emergency_waiting,
                    "traffic_throughput_per_min": throughput,
                    "directional_waiting": directional_waiting,
                    "directional_served": self.directional_served,
                    "directional_avg_wait": dir_avg_wait
                },
                "queues": {
                    d: self.queues[d].get_state()
                    for d in DIRECTIONS
                },
                "recent_departures": self.departed_vehicles[-10:],
                "recent_events": self.scheduler.event_log[-20:],
                "graph_summary": {
                    "congestion_score": self.graph.calculate_congestion_score(),
                    "total_nodes": len(self.graph.nodes)
                }
            }

    def run_experimental_comparison(
        self,
        source: Optional[str] = None,
        destination: Optional[str] = None
    ) -> Dict[str, Any]:
        """Return live queue analytics and routes from the current graph state."""
        queue_capacity = self.queue_capacity * len(DIRECTIONS)
        total_waiting = sum(len(queue) for queue in self.queues.values())
        adjacency_pairs = {
            (edge.from_node, edge.to_node)
            for edges in self.graph.adjacency.values()
            for edge in edges
        }
        road_link_keys = set()
        for start, end in adjacency_pairs:
            if (end, start) in adjacency_pairs:
                road_link_keys.add(tuple(sorted((start, end))))
            else:
                road_link_keys.add((start, end))
        road_links = len(road_link_keys)
        nodes = self.graph.nodes

        bfs_result = None
        dijkstra_result = None
        if source and destination:
            bfs_result = self.graph.bfs_shortest_path(source, destination)
            dijkstra_result = self.graph.dijkstra_shortest_path(source, destination)

        return {
            "micro_level_queue": {
                "purpose": "Manage waiting vehicles at each intersection approach in FIFO order.",
                "data_structure": "Fixed-capacity circular array queue (one queue per direction).",
                "main_operations": "Enqueue, dequeue, peek, clear, and check full/empty.",
                "algorithm": "O(1) circular-buffer FIFO operations; round-robin or adaptive signal selection.",
                "time_complexity": "Enqueue O(1); dequeue O(1); peek O(1).",
                "space_complexity": "O(C) per approach, where C is its fixed queue capacity.",
                "application": "Stores waiting vehicles in the four intersection approach queues."
            },
            "macro_level_graph": {
                "purpose": "Find routes between intersections by hop count or weighted travel cost.",
                "data_structure": "Weighted adjacency-list road network.",
                "main_operations": "Add intersections and roads; traverse neighbors; calculate routes.",
                "algorithm": "BFS for minimum-hop paths; heap-based Dijkstra for minimum travel-cost paths.",
                "time_complexity": "BFS O(V + E); Dijkstra O((V + E) log V).",
                "space_complexity": "Graph O(V + E); BFS auxiliary O(V); Dijkstra auxiliary O(V + E) worst case.",
                "application": "Models road connections and calculates routes for selected intersections."
            },
            "live_analytics": {
                "queue_capacity_per_direction": self.queue_capacity,
                "queue_capacity_total": queue_capacity,
                "vehicles_waiting": total_waiting,
                "vehicles_served": self.total_served,
                "queue_utilization_percent": round(total_waiting / queue_capacity * 100, 1)
                if queue_capacity else 0.0,
                "vertices": len(nodes),
                "road_links": road_links,
                "origin": {
                    "id": source,
                    "name": nodes[source].name if source in nodes else None
                },
                "destination": {
                    "id": destination,
                    "name": nodes[destination].name if destination in nodes else None
                },
                "bfs": bfs_result,
                "dijkstra": dijkstra_result
            }
        }
