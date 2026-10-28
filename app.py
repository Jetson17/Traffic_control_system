"""
Flask Web Application & REST API for Traffic Signal Control System.

System: Intelligent Traffic Monitoring & Analysis
Backend Stack: Python 3, Flask, REST APIs, Pure DSA Modules
"""

import os
from flask import Flask, jsonify, request, render_template
from algorithms.circular_queue import QueueUnderflowError
from algorithms.simulation import TrafficSimulationManager
from algorithms.signal_scheduler import DIRECTIONS

app = Flask(__name__)

# Initialize single central simulation manager instance
simulation = TrafficSimulationManager(queue_capacity=8)


# -------------------------------------------------------------------------
# Web Frontend Route
# -------------------------------------------------------------------------
@app.route("/")
def index():
    """Render the main Traffic Signal Control Dashboard."""
    return render_template("index.html")


# -------------------------------------------------------------------------
# Health & State Endpoints
# -------------------------------------------------------------------------
@app.route("/api/health", methods=["GET"])
def health():
    """Return backend server health and status."""
    return jsonify({
        "status": "healthy",
        "service": "Traffic Signal Control System API",
        "version": "1.0.0",
        "simulation_status": simulation.status
    }), 200


@app.route("/api/state", methods=["GET"])
def get_state():
    """Return complete simulation state for dashboard synchronization."""
    return jsonify(simulation.get_complete_state()), 200


# -------------------------------------------------------------------------
# Simulation Control Endpoints
# -------------------------------------------------------------------------
@app.route("/api/simulation/start", methods=["POST"])
def start_simulation():
    """Start real-time simulation background clock."""
    result = simulation.start()
    return jsonify(result), 200


@app.route("/api/simulation/pause", methods=["POST"])
def pause_simulation():
    """Pause real-time simulation clock."""
    result = simulation.pause()
    return jsonify(result), 200


@app.route("/api/simulation/resume", methods=["POST"])
def resume_simulation():
    """Resume paused simulation clock."""
    result = simulation.resume()
    return jsonify(result), 200


@app.route("/api/simulation/reset", methods=["POST"])
def reset_simulation():
    """Reset simulation back to initial clean state."""
    result = simulation.reset()
    return jsonify(result), 200


@app.route("/api/simulation/step", methods=["POST"])
def step_simulation():
    """Advance simulation deterministically by a single time-step (default dt=1s)."""
    data = request.get_json(silent=True) or {}
    dt = int(data.get("dt", 1))
    if dt < 1 or dt > 60:
        return jsonify({"error": "Step size 'dt' must be between 1 and 60 seconds."}), 400

    step_info = simulation.step(dt=dt)
    return jsonify({
        "success": True,
        "message": f"Advanced simulation by {dt} second(s).",
        "step_info": step_info,
        "state": simulation.get_complete_state()
    }), 200


@app.route("/api/simulation/config", methods=["POST"])
def update_config():
    """Update scheduler configurations (green/yellow durations, strategy)."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid or missing JSON payload."}), 400

    green_dur = data.get("green_duration")
    yellow_dur = data.get("yellow_duration")
    strategy = data.get("strategy")
    max_emg = data.get("max_emergency_consecutive")

    simulation.scheduler.set_config(
        green_duration=green_dur,
        yellow_duration=yellow_dur,
        strategy=strategy,
        max_emergency_consecutive=max_emg
    )

    return jsonify({
        "success": True,
        "message": "Configuration updated successfully.",
        "config": {
            "green_duration": simulation.scheduler.green_duration,
            "yellow_duration": simulation.scheduler.yellow_duration,
            "strategy": simulation.scheduler.strategy.value,
            "max_emergency_consecutive": simulation.scheduler.max_emergency_consecutive
        }
    }), 200


# -------------------------------------------------------------------------
# Vehicle Management Endpoints
# -------------------------------------------------------------------------
@app.route("/api/vehicles/add", methods=["POST"])
def add_vehicle():
    """
    Enqueue a vehicle into a directional circular queue.
    Validates direction and vehicle type.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    direction = data.get("direction")
    vehicle_type = data.get("vehicle_type", "Car")
    is_emergency = bool(data.get("is_emergency", False))
    try:
        priority = int(data.get("priority", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Priority must be an integer."}), 400

    if not direction or direction not in DIRECTIONS:
        return jsonify({
            "error": f"Invalid or missing direction '{direction}'. Valid options: {DIRECTIONS}."
        }), 400

    valid_types = ["Car", "Bus", "Truck", "Bike", "Ambulance", "Fire Engine", "Police Vehicle"]
    if vehicle_type not in valid_types:
        return jsonify({
            "error": f"Invalid vehicle type '{vehicle_type}'. Valid types: {valid_types}."
        }), 400

    if vehicle_type in ["Ambulance", "Fire Engine", "Police Vehicle"]:
        is_emergency = True

    result = simulation.add_vehicle(
        direction=direction,
        vehicle_type=vehicle_type,
        is_emergency=is_emergency,
        priority=priority
    )

    if not result.get("success", False):
        return jsonify(result), 400

    return jsonify(result), 201


@app.route("/api/vehicles/batch", methods=["POST"])
def add_vehicle_batch():
    """
    Add a generated batch of sample vehicles across multiple directions for rapid demonstration.
    """
    import random
    data = request.get_json(silent=True) or {}
    count = int(data.get("count", 4))
    count = max(1, min(12, count))

    types = ["Car", "Car", "Bus", "Truck", "Bike", "Ambulance", "Police Vehicle"]
    added = []

    for _ in range(count):
        d = random.choice(DIRECTIONS)
        v_type = random.choice(types)
        res = simulation.add_vehicle(direction=d, vehicle_type=v_type)
        if res.get("success"):
            added.append(res["vehicle"])

    return jsonify({
        "success": True,
        "added_count": len(added),
        "vehicles": added,
        "message": f"Successfully added {len(added)} vehicle(s) into directional queues."
    }), 201


@app.route("/api/queues/<direction>/dequeue", methods=["POST"])
def dequeue_vehicle(direction):
    """Remove and return the front vehicle from the shared directional queue."""
    if direction not in DIRECTIONS:
        return jsonify({"error": f"Invalid direction '{direction}'. Valid options: {DIRECTIONS}."}), 400

    with simulation.lock:
        queue = simulation.queues[direction]
        try:
            vehicle = queue.dequeue()
        except QueueUnderflowError as error:
            return jsonify({"error": str(error)}), 400

        simulation.scheduler.log_event(
            "VEHICLE_REMOVED",
            f"Vehicle {vehicle['id']} was dequeued from the {direction} queue.",
            {"vehicle_id": vehicle["id"], "direction": direction}
        )
        simulation.scheduler.update_emergency_priority(simulation.queues, simulation.sim_time)
        return jsonify({
            "success": True,
            "message": f"Dequeued {vehicle['id']} from the {direction} queue.",
            "vehicle": vehicle,
            "state": simulation.get_complete_state()
        }), 200


@app.route("/api/queues/<direction>/peek", methods=["POST"])
def peek_vehicle(direction):
    """Return the front vehicle from the shared directional queue without removing it."""
    if direction not in DIRECTIONS:
        return jsonify({"error": f"Invalid direction '{direction}'. Valid options: {DIRECTIONS}."}), 400

    with simulation.lock:
        try:
            vehicle = simulation.queues[direction].peek()
        except QueueUnderflowError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify({
            "success": True,
            "message": f"Front vehicle is {vehicle['id']} ({vehicle['type']}).",
            "vehicle": vehicle
        }), 200


@app.route("/api/queues/<direction>/clear", methods=["POST"])
def clear_queue(direction):
    """Clear a directional circular queue without changing the served-vehicle count."""
    if direction not in DIRECTIONS:
        return jsonify({"error": f"Invalid direction '{direction}'. Valid options: {DIRECTIONS}."}), 400

    with simulation.lock:
        queue = simulation.queues[direction]
        removed_count = len(queue)
        queue.clear()
        simulation.scheduler.update_emergency_priority(simulation.queues, simulation.sim_time)
        simulation.scheduler.log_event(
            "QUEUE_CLEARED",
            f"Cleared {removed_count} waiting vehicle(s) from the {direction} queue.",
            {"direction": direction, "removed_count": removed_count}
        )
        return jsonify({
            "success": True,
            "message": f"Cleared {removed_count} vehicle(s) from the {direction} queue.",
            "removed_count": removed_count,
            "state": simulation.get_complete_state()
        }), 200


# -------------------------------------------------------------------------
# Queues & Analytics Endpoints
# -------------------------------------------------------------------------
@app.route("/api/queues", methods=["GET"])
def get_queues():
    """Return detailed circular queue state, slot indices, front, rear, and FIFO lists."""
    with simulation.lock:
        queue_states = {d: simulation.queues[d].get_state() for d in DIRECTIONS}
    return jsonify({
        "capacity": simulation.queue_capacity,
        "queues": queue_states
    }), 200


@app.route("/api/analytics", methods=["GET"])
def get_analytics():
    """Return live computed traffic analytics and performance indicators."""
    state = simulation.get_complete_state()
    return jsonify({
        "statistics": state["statistics"],
        "signals": state["signals"],
        "active_direction": state["active_direction"],
        "current_phase": state["current_phase"],
        "sim_time": state["sim_time"],
        "config": state["config"]
    }), 200


# -------------------------------------------------------------------------
# Graph Road Network Endpoints
# -------------------------------------------------------------------------
@app.route("/api/graph", methods=["GET"])
def get_graph():
    """Return city road graph vertices, edges, congestion levels, and connectivity."""
    with simulation.lock:
        graph_data = simulation.graph.export_graph_data()
    return jsonify(graph_data), 200


@app.route("/api/graph/bfs", methods=["POST"])
def run_graph_bfs():
    """Run a complete BFS traversal without changing simulation state."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"found": False, "error": "Request body must be a JSON object."}), 400
    source = data.get("source")
    if not isinstance(source, str) or not source:
        return jsonify({"found": False, "error": "A starting intersection is required."}), 400

    with simulation.lock:
        result = simulation.graph.bfs_traversal(source)
    return jsonify(result), 200 if result.get("found") else 404


@app.route("/api/graph/route", methods=["POST"])
def get_graph_route():
    """
    Calculate route between source and destination using BFS or Dijkstra.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    source = data.get("source")
    destination = data.get("destination")
    algorithm = data.get("algorithm", "bfs").lower()

    if not source or not destination:
        return jsonify({"error": "Both 'source' and 'destination' intersection IDs are required."}), 400

    if algorithm == "dijkstra":
        result = simulation.graph.dijkstra_shortest_path(source, destination)
    elif algorithm == "bfs":
        result = simulation.graph.bfs_shortest_path(source, destination)
    else:
        return jsonify({"error": "Algorithm must be 'bfs' or 'dijkstra'."}), 400

    status_code = 200 if result.get("found", False) else 404
    return jsonify(result), status_code


# -------------------------------------------------------------------------
# Comparison & Audit Events Endpoints
# -------------------------------------------------------------------------
@app.route("/api/comparison", methods=["GET"])
def get_comparison():
    """
    Return implementation details and a live snapshot of queue and graph analytics.
    """
    source = request.args.get("source")
    destination = request.args.get("destination")
    with simulation.lock:
        result = simulation.run_experimental_comparison(source, destination)
    return jsonify(result), 200


@app.route("/api/events", methods=["GET"])
def get_events():
    """Return chronological audit log of phase changes, departures, and priority actions."""
    limit = int(request.args.get("limit", 50))
    limit = max(5, min(100, limit))
    with simulation.lock:
        recent = simulation.scheduler.event_log[-limit:]
    return jsonify({
        "total_events": len(recent),
        "events": list(reversed(recent))
    }), 200


# -------------------------------------------------------------------------
# Main Execution Entry Point
# -------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Runs local development server
    app.run(host="127.0.0.1", port=port, debug=False)
