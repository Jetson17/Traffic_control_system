# Algorithmic Documentation — Traffic Signal Control System

**Course Outcomes:** CO1 (Abstract Data Types & Queues), CO2 (Graph Representations & Traversal), CO5 (Algorithm Performance Analysis)  
**Microproject Number:** 10  
**Focus:** Smart Cities & Intelligent Transportation Systems  

---

## 1. Circular Queue Implementation

### 1.1 Problem Statement & Rationale
In a physical traffic intersection, vehicles arrive at an approach lane and must be served in First-In, First-Out (FIFO) sequence. If implemented using a standard linear array or dynamic list:
- Dequeuing an element from index `0` forces every subsequent element to shift left by one position, resulting in an expensive $O(N)$ time complexity per vehicle clearance.
- Alternatively, moving pointers forward without wrapping leads to **false overflow**, where memory at the front of the array is wasted while the rear hits the boundary.

A **Circular Queue** solves both limitations by connecting the last index back to the first index using modulo arithmetic:
$$\text{next\_index} = (\text{current\_index} + 1) \pmod{\text{capacity}}$$

This guarantees strictly $O(1)$ time complexity for both `enqueue` and `dequeue` operations with zero element shifting.

### 1.2 Mathematical Formulation & Invariants

Let $C$ denote the fixed array capacity, $A$ be the underlying array of length $C$, $f$ be the front pointer, and $r$ be the rear pointer.

- **Initial Empty State:**
  $$f = -1, \quad r = -1, \quad \text{size} = 0$$

- **Empty Condition:**
  $$\text{is\_empty}() \iff \text{size} = 0$$

- **Full Condition:**
  $$\text{is\_full}() \iff \text{size} = C$$

- **Enqueue Operation ($O(1)$):**
  If $\text{is\_full}()$, raise `QueueOverflowError`.  
  If $\text{is\_empty}()$:
  $$f \leftarrow 0, \quad r \leftarrow 0$$
  Else:
  $$r \leftarrow (r + 1) \pmod{C}$$
  $$A[r] \leftarrow \text{item}, \quad \text{size} \leftarrow \text{size} + 1$$

- **Dequeue Operation ($O(1)$):**
  If $\text{is\_empty}()$, raise `QueueUnderflowError`.  
  $$\text{item} \leftarrow A[f], \quad A[f] \leftarrow \text{None}$$
  If $f = r$ (last remaining element removed):
  $$f \leftarrow -1, \quad r \leftarrow -1$$
  Else:
  $$f \leftarrow (f + 1) \pmod{C}$$
  $$\text{size} \leftarrow \text{size} - 1$$
  $$\text{return item}$$

- **Modulo Wrap-Around Demonstration:**
  When $r = C - 1$ and a slot has been freed at index $0$ by prior dequeues, the next insertion executes:
  $$r_{\text{new}} = (C - 1 + 1) \pmod{C} = 0$$
  The new element occupies index `0` while front remains at an index $> 0$, maximizing memory utilization within a fixed memory footprint.

---

## 2. Signal Scheduling & Safety Algorithm

### 2.1 Four-Phase State Machine
The traffic signal scheduler governs four directional approaches:
$$\mathcal{D} = \{\text{North}, \text{East}, \text{South}, \text{West}\}$$

To ensure complete physical safety, the controller enforces the **Single-Active-Movement Group Safety Invariant**:

$$\forall d \in \mathcal{D}, \quad \text{Signal}(d) \in \{\text{GREEN}, \text{YELLOW}\} \iff \forall d' \in \mathcal{D} \setminus \{d\}, \; \text{Signal}(d') = \text{RED}$$

Under no condition can two intersecting lanes display GREEN or YELLOW simultaneously.

### 2.2 Phase Progression
1. **GREEN Phase ($\tau_{\text{green}}$):** Active direction holds GREEN. Waiting vehicles in that direction's circular queue are served and dequeued at a measured clearance rate.
2. **YELLOW Transition Phase ($\tau_{\text{yellow}}$):** Light changes to YELLOW for the active direction. Clearance ceases; trailing vehicles must stop.
3. **Phase Handover:** After $\tau_{\text{yellow}}$ completes, the scheduler evaluates the next direction based on the selected scheduling policy and switches that direction to GREEN.

### 2.3 Priority Scheduling & Starvation Prevention

- **Emergency Preemption:** Emergency vehicles (Ambulances: Priority 1, Fire Engines: Priority 2, Police Cruisers: Priority 3) preempt normal round-robin ordering.
- **Starvation Safeguard:** To prevent infinite starvation of standard commuter traffic:
  - The controller tracks consecutive emergency grants per approach: $\kappa(d)$.
  - If $\kappa(d) \ge \kappa_{\max}$ (default: 2 consecutive cycles) and another approach has a normal queue waiting beyond a threshold ($\Delta t_{\text{starve}} > 15\text{s}$), the starved approach is granted a mandatory green cycle before further emergency prioritization resumes.

---

## 3. Graph-Based Traffic Flow Analysis

### 3.1 Network Topology & Adjacency List
The smart-city road network is modeled as a directed, weighted graph $G = (V, E)$:
- **Vertices $V$:** Traffic intersections/junctions (e.g., Central Junction, North Metro, East Tech Corridor).
- **Edges $E$:** Roadways with attributes: length $d_{uv}$ (km), capacity $c_{uv}$ (veh/hr), current volume $v_{uv}$, and speed limit $s_{uv}$ (km/h).

### 3.2 Dynamic Delay Function (BPR Formula)
Effective travel time across road $(u, v)$ is calculated using the Bureau of Public Roads (BPR) delay formulation:
$$t_{uv} = t_{0, uv} \cdot \left[1 + \alpha \cdot \left(\frac{v_{uv}}{c_{uv}}\right)^\beta\right]$$
Where:
- $t_{0, uv} = \frac{d_{uv}}{s_{uv}} \times 60$ (free-flow travel time in minutes)
- $\alpha = 1.2$, $\beta = 2.0$ (congestion penalty coefficients)

### 3.3 Traversal & Shortest-Path Algorithms

#### A. Breadth-First Search (BFS)
- **Objective:** Find path with minimum intermediate intersections (minimum edge hops) in an unweighted view of the graph.
- **Data Structure:** First-In, First-Out Queue.
- **Time Complexity:** $O(|V| + |E|)$
- **Space Complexity:** $O(|V|)$

#### B. Dijkstra's Algorithm
- **Objective:** Find path minimizing dynamic travel time, routing vehicles away from congested road corridors.
- **Data Structure:** Min-Heap / Priority Queue (`heapq`).
- **Time Complexity:** $O((|V| + |E|) \log |V|)$
- **Space Complexity:** $O(|V|)$

---

## 4. Complexity & Theoretical Summary

| Component | Operation / Algorithm | Time Complexity (Best) | Time Complexity (Worst) | Space Complexity |
| :--- | :--- | :--- | :--- | :--- |
| **Circular Queue** | `enqueue(item)` | $O(1)$ | $O(1)$ | $O(C)$ |
| **Circular Queue** | `dequeue()` | $O(1)$ | $O(1)$ | $O(C)$ |
| **Circular Queue** | `peek()` | $O(1)$ | $O(1)$ | $O(1)$ |
| **Signal Scheduler**| Phase Advance | $O(1)$ | $O(1)$ | $O(1)$ |
| **Signal Scheduler**| Next Direction Selection | $O(|\mathcal{D}|) = O(1)$ | $O(|\mathcal{D}|) = O(1)$ | $O(1)$ |
| **Traffic Graph** | BFS Shortest Path | $O(1)$ (Source = Target) | $O(|V| + |E|)$ | $O(|V|)$ |
| **Traffic Graph** | Dijkstra Shortest Path | $O(|V| \log |V|)$ | $O((|V| + |E|) \log |V|)$ | $O(|V|)$ |
| **Traffic Graph** | Connectivity Analysis | $O(|V| + |E|)$ | $O(|V| + |E|)$ | $O(|V|)$ |
