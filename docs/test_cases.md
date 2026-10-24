# Automated Test Cases & Verification Report — Traffic Signal Control System

**Microproject Number:** 10  
**Testing Framework:** Python `unittest`  
**Execution Command:** `python -m unittest discover -s tests -v`  
**Total Tests:** 36 Passed, 0 Failed, 0 Errors  

---

## 1. Circular Queue Unit Tests (`tests/test_circular_queue.py`)

| Test Case ID | Test Method | Test Objective | Input Data | Expected Output | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-CQ-01** | `test_initial_state` | Verify initialized queue pointers and empty condition | Empty queue of capacity 5 | `front == -1`, `rear == -1`, `size == 0`, `is_empty == True` | Pointers match invariant | **PASS** |
| **TC-CQ-02** | `test_enqueue_and_fifo_order` | Verify sequential enqueues and FIFO integrity | Enqueue `"V1"`, `"V2"`, `"V3"` | `size == 3`, `front == 0`, `rear == 2`, FIFO: `["V1", "V2", "V3"]` | Correct FIFO order | **PASS** |
| **TC-CQ-03** | `test_dequeue` | Verify element extraction from front pointer | Dequeue from `["A", "B", "C"]` | Returns `"A"`, `front == 1`, remaining `["B", "C"]` | Returned `"A"`, front advanced | **PASS** |
| **TC-CQ-04** | `test_full_queue_and_overflow` | Verify overflow exception when inserting into full queue | Fill capacity 5; insert 6th item | Raises `QueueOverflowError` | Raised `QueueOverflowError` | **PASS** |
| **TC-CQ-05** | `test_empty_queue_underflow` | Verify underflow exception when dequeuing or peeking empty queue | Empty queue | Raises `QueueUnderflowError` | Raised `QueueUnderflowError` | **PASS** |
| **TC-CQ-06** | `test_wrap_around_modulo` | Verify modulo pointer wrap-around when inserting after dequeues | Fill 5, dequeue 2 (vacate 0, 1), enqueue 2 | `rear` wraps around to `0` then `1`; `is_full == True` | Wrapped modulo index correctly | **PASS** |
| **TC-CQ-07** | `test_drain_to_empty_resets_pointers` | Verify pointers reset to `-1` when last item dequeued | Enqueue 1 item, then dequeue | `front == -1`, `rear == -1`, `is_empty == True` | Pointers reset to -1 | **PASS** |
| **TC-CQ-08** | `test_get_state_structure` | Verify JSON serialization of memory slots for live visualizer | Enqueue 1 vehicle object | Valid dictionary with capacity, size, pointers, and slot booleans | Correct structure exported | **PASS** |

---

## 2. Signal Scheduler Unit Tests (`tests/test_signal_scheduler.py`)

| Test Case ID | Test Method | Test Objective | Input Data | Expected Output | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-SS-01** | `test_initial_state_and_no_conflict` | Verify initial green direction and zero conflicting signals | Scheduler at $t=0$ | North GREEN; East/South/West strictly RED | Exactly 1 non-RED light | **PASS** |
| **TC-SS-02** | `test_phase_progression_green_to_yellow_to_next` | Verify mandatory yellow transition before green handover | Advance through green duration (4s), then yellow (2s) | GREEN (0-3s) $\to$ YELLOW (4-5s) $\to$ East GREEN (6s) | Transitions verified | **PASS** |
| **TC-SS-03** | `test_round_robin_full_cycle` | Verify deterministic round-robin cycle over 4 approaches | 4 full signal cycles | Sequence: North $\to$ East $\to$ South $\to$ West | Sequence strictly followed | **PASS** |
| **TC-SS-04** | `test_emergency_vehicle_prioritization` | Verify emergency vehicle preemption at next cycle switch | Ambulance queued at West; normal car at East | West receives green next instead of East | West prioritized safely | **PASS** |
| **TC-SS-05** | `test_reset` | Verify clean reset of scheduler timers, phase, and state | Advanced scheduler; trigger reset | North GREEN, elapsed time = 0, event log cleared | Fully restored | **PASS** |

---

## 3. Traffic Graph Network Unit Tests (`tests/test_traffic_graph.py`)

| Test Case ID | Test Method | Test Objective | Input Data | Expected Output | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-TG-01** | `test_sample_network_initialization` | Verify 7 intersections and road edges in sample city network | Sample city network builder | 7 nodes, $\ge 10$ connecting edges, fully connected | 7 nodes, connected | **PASS** |
| **TC-TG-02** | `test_bfs_shortest_path_found` | Verify BFS calculates minimum-hop path | Route from INT-6 to INT-1 | Path found, 2 hops (INT-6 $\to$ INT-2 $\to$ INT-1) | Valid 2-hop route | **PASS** |
| **TC-TG-03** | `test_bfs_same_source_and_destination` | Verify zero-hop route when origin equals destination | INT-1 to INT-1 | Path `["INT-1"]`, 0 hops, 0 km | 0 hops | **PASS** |
| **TC-TG-04** | `test_bfs_disconnected_node` | Verify safe handling of disconnected graph vertex | Path to isolated node `INT-ISOLATED` | `found == False`, helpful error message | No crash; clean error | **PASS** |
| **TC-TG-05** | `test_dijkstra_path` | Verify Dijkstra calculates weighted minimum-delay route | INT-6 to INT-4 | Valid path with computed distance and travel cost | Path with BPR delay | **PASS** |
| **TC-TG-06** | `test_connectivity_analysis` | Verify connected components detection | 7 connected nodes; add 1 isolated node | Component count updates from 1 to 2; `is_fully_connected == False` | Accurately detected | **PASS** |
| **TC-TG-07** | `test_invalid_node_handling` | Verify rejection of non-existent node IDs | Invalid ID `"INVALID_1"` | `found == False`, validation error | Safely rejected | **PASS** |

---

## 4. Flask REST API Unit Tests (`tests/test_api.py`)

| Test Case ID | Test Method | Test Objective | Input Data | Expected Output | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-API-01** | `test_health_endpoint` | Verify `/api/health` response | GET `/api/health` | HTTP 200, status "healthy" | HTTP 200 OK | **PASS** |
| **TC-API-02** | `test_state_endpoint` | Verify full state synchronization payload | GET `/api/state` | HTTP 200, signals, queues, statistics | HTTP 200 OK | **PASS** |
| **TC-API-03** | `test_simulation_controls` | Verify Start, Pause, Resume, Reset endpoints | POST `/api/simulation/{action}` | HTTP 200, state matches commanded action | HTTP 200 OK | **PASS** |
| **TC-API-04** | `test_manual_step` | Verify deterministic single-step advancement | POST `/api/simulation/step` with `dt=2` | HTTP 200, `sim_time` advanced by 2s | HTTP 200 OK | **PASS** |
| **TC-API-05** | `test_add_vehicle_valid` | Verify vehicle insertion via REST API | POST vehicle: North, "Car" | HTTP 201, vehicle ID generated, queue incremented | HTTP 201 Created | **PASS** |
| **TC-API-06** | `test_add_emergency_vehicle` | Verify emergency vehicle insertion with priority | POST: East, "Ambulance" | HTTP 201, `is_emergency == True`, `priority == 1` | HTTP 201 Created | **PASS** |
| **TC-API-07** | `test_add_vehicle_invalid_direction`| Verify validation of directional names | POST direction: "NorthEast" | HTTP 400 Bad Request, descriptive error | HTTP 400 Bad Request | **PASS** |
| **TC-API-08** | `test_add_vehicle_invalid_type` | Verify validation of vehicle types | POST vehicle_type: "Airplane" | HTTP 400 Bad Request, descriptive error | HTTP 400 Bad Request | **PASS** |
| **TC-API-09** | `test_get_queues` | Verify detailed circular queue slot arrays | GET `/api/queues` | HTTP 200, 4 directional queues with 8 slots | HTTP 200 OK | **PASS** |
| **TC-API-10** | `test_get_analytics` | Verify computed performance statistics | GET `/api/analytics` | HTTP 200, total served, average wait | HTTP 200 OK | **PASS** |
| **TC-API-11** | `test_get_graph` | Verify city road network topology | GET `/api/graph` | HTTP 200, nodes and edges exported | HTTP 200 OK | **PASS** |
| **TC-API-12** | `test_graph_route_bfs` | Verify BFS route endpoint | POST `/api/graph/route` (BFS) | HTTP 200, path found | HTTP 200 OK | **PASS** |
| **TC-API-13** | `test_graph_route_dijkstra` | Verify Dijkstra route endpoint | POST `/api/graph/route` (Dijkstra) | HTTP 200, optimal weighted route | HTTP 200 OK | **PASS** |
| **TC-API-14** | `test_graph_route_invalid_node` | Verify route error on non-existent node | POST route with non-existent ID | HTTP 404 Not Found, `found == False` | HTTP 404 Not Found | **PASS** |
| **TC-API-15** | `test_get_comparison` | Verify comparative evaluation data | GET `/api/comparison` | HTTP 200, micro vs macro metrics | HTTP 200 OK | **PASS** |
| **TC-API-16** | `test_get_events` | Verify chronological audit log endpoint | GET `/api/events` | HTTP 200, event list returned | HTTP 200 OK | **PASS** |

---

## 5. Verification Summary
- **Total Test Cases Executed:** 36
- **Pass Rate:** 100% (36/36)
- **Zero Failures, Zero Regressions**
