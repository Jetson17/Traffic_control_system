/**
 * Traffic Signal Control System — Frontend Controller
 * Intelligent Traffic Monitoring & Analysis
 * Pure Vanilla JavaScript & Fetch API
 */

// Application State
const state = {
  pollingInterval: null,
  isPollingActive: true,
  lastState: null,
  activeQueueTab: 'North',
  selectedVisualizerQueue: 'North',
  graphData: null,
  activeRoutePath: [],
  animatedDepartedIds: new Set(),
  isInitialLoad: true,
  prevQueueCounts: {}
};

// Vehicle Type Emoji Map
const VEHICLE_ICONS = {
  'Car': '🚗',
  'Bus': '🚌',
  'Truck': '🚚',
  'Bike': '🏍️',
  'Ambulance': '🚑',
  'Fire Engine': '🚒',
  'Police Vehicle': '🚓'
};

// DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  fetchInitialGraph();
  fetchComparisonData();
  startPolling();
});

// ---------------------------------------------------------------------------
// Polling & Real-time State Synchronization
// ---------------------------------------------------------------------------
function startPolling() {
  if (state.pollingInterval) clearInterval(state.pollingInterval);
  fetchSimulationState();
  state.pollingInterval = setInterval(fetchSimulationState, 800);
}

async function fetchSimulationState() {
  try {
    const response = await fetch('/api/state');
    if (!response.ok) throw new Error(`HTTP error: ${response.status}`);
    const data = await response.json();
    state.lastState = data;

    renderStatusAndTelemetry(data);
    renderIntersectionSignals(data);
    renderIntersectionVehicles(data);
    renderStatistics(data.statistics);
    renderDirectionalQueues(data.queues);
    renderCircularQueueVisualizer(data.queues[state.selectedVisualizerQueue]);
    renderEvents(data.recent_events);
  } catch (err) {
    console.warn('Simulation state poll error:', err.message);
  }
}

// ---------------------------------------------------------------------------
// Telemetry & Header Rendering
// ---------------------------------------------------------------------------
function renderStatusAndTelemetry(data) {
  const badge = document.getElementById('status-badge');
  const statusText = document.getElementById('status-text');
  const status = data.status || 'STOPPED';

  statusText.textContent = status;
  badge.className = `nav-status-badge status-${status.toLowerCase()}`;

  // Time formatting
  const mins = String(Math.floor(data.sim_time / 60)).padStart(2, '0');
  const secs = String(data.sim_time % 60).padStart(2, '0');
  document.getElementById('telemetry-time').textContent = `${mins}:${secs}`;

  document.getElementById('telemetry-direction').textContent = data.active_direction;
  
  const phaseEl = document.getElementById('telemetry-phase');
  phaseEl.textContent = `${data.current_phase} (${data.remaining_phase_time}s)`;
  if (data.current_phase === 'GREEN') {
    phaseEl.style.color = '#34d399';
  } else if (data.current_phase === 'YELLOW') {
    phaseEl.style.color = '#facc15';
  } else {
    phaseEl.style.color = '#f87171';
  }

  // Button states
  document.getElementById('btn-start').disabled = (status === 'RUNNING');
  document.getElementById('btn-pause').disabled = (status !== 'RUNNING');
  document.getElementById('btn-resume').disabled = (status !== 'PAUSED');
}

// ---------------------------------------------------------------------------
// Statistics Cards
// ---------------------------------------------------------------------------
function renderStatistics(stats) {
  if (!stats) return;

  document.getElementById('stat-total-waiting').textContent = stats.total_waiting;
  document.getElementById('stat-total-served').textContent = stats.total_served;
  document.getElementById('stat-avg-wait').textContent = `${stats.average_waiting_time}s`;
  document.getElementById('stat-throughput').textContent = `${stats.traffic_throughput_per_min}/m`;
  
  const emgCard = document.getElementById('stat-card-emergency');
  const emgVal = document.getElementById('stat-emergency-count');
  emgVal.textContent = stats.emergency_waiting;
  if (stats.emergency_waiting > 0) {
    emgCard.classList.add('stat-emergency');
  } else {
    emgCard.classList.remove('stat-emergency');
  }
}

// ---------------------------------------------------------------------------
// 4-Way Intersection Traffic Lights
// ---------------------------------------------------------------------------
function renderIntersectionSignals(data) {
  const signals = data.signals || {};

  ['North', 'East', 'South', 'West'].forEach(dir => {
    const color = signals[dir] || 'RED';
    const fixture = document.getElementById(`light-${dir.toLowerCase()}`);
    if (!fixture) return;

    const rBulb = fixture.querySelector('.bulb-red');
    const yBulb = fixture.querySelector('.bulb-yellow');
    const gBulb = fixture.querySelector('.bulb-green');

    rBulb.classList.remove('active');
    yBulb.classList.remove('active');
    gBulb.classList.remove('active');

    if (color === 'GREEN') gBulb.classList.add('active');
    else if (color === 'YELLOW') yBulb.classList.add('active');
    else rBulb.classList.add('active');

    // Update approach queue badge count
    const qCountBadge = document.getElementById(`approach-count-${dir.toLowerCase()}`);
    if (qCountBadge && data.queues && data.queues[dir]) {
      qCountBadge.textContent = `${data.queues[dir].size}/${data.queues[dir].capacity}`;
    }
  });
}

// ---------------------------------------------------------------------------
// Crossing Vehicle Animation (Green Phase Authorized Departure)
// ---------------------------------------------------------------------------
function animateVehicleCrossing(vehicle) {
  const crossingLayer = document.getElementById('intersection-crossing-layer');
  if (!crossingLayer || !vehicle || !vehicle.direction) return;

  const dir = vehicle.direction;
  const chip = document.createElement('div');
  chip.className = `vehicle-crossing-chip dir-${dir.toLowerCase()} ${vehicle.is_emergency ? 'emergency' : ''}`;
  const icon = VEHICLE_ICONS[vehicle.type] || '🚗';
  chip.innerHTML = `<span>${icon}</span> <span>${vehicle.id}</span>`;

  crossingLayer.appendChild(chip);

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      chip.classList.add('crossing-active');
    });
  });

  setTimeout(() => {
    if (chip.parentNode) chip.remove();
  }, 900);
}

// ---------------------------------------------------------------------------
// Render Waiting Vehicles on Visual Intersection Roads Behind Stop Lines
// ---------------------------------------------------------------------------
function renderIntersectionVehicles(data) {
  if (!data || !data.queues) return;

  // Trigger crossing animations for newly departed vehicles during RUNNING simulation
  const departures = data.recent_departures || [];
  if (state.isInitialLoad) {
    departures.forEach(v => state.animatedDepartedIds.add(v.id));
    state.isInitialLoad = false;
  } else if (data.status === 'RUNNING') {
    departures.forEach(v => {
      if (!state.animatedDepartedIds.has(v.id)) {
        state.animatedDepartedIds.add(v.id);
        animateVehicleCrossing(v);
      }
    });
  }

  // Render waiting vehicles in each directional approach lane
  ['North', 'East', 'South', 'West'].forEach(dir => {
    const laneContainer = document.getElementById(`lane-${dir.toLowerCase()}`);
    if (!laneContainer) return;

    const queueData = data.queues[dir];
    const fifoVehicles = queueData.fifo_items || [];
    const prevCount = state.prevQueueCounts[dir] ?? -1;
    const countChanged = (prevCount !== fifoVehicles.length);
    state.prevQueueCounts[dir] = fifoVehicles.length;

    // Clear lane container
    laneContainer.innerHTML = '';

    if (fifoVehicles.length === 0) {
      return;
    }

    const createChip = (v, queueIndex) => {
      const chip = document.createElement('div');
      chip.className = `vehicle-mini-chip ${v.is_emergency ? 'emergency' : ''}`;
      chip.setAttribute('data-id', v.id);
      chip.title = `${v.type} (${v.id}) — Queue Pos: #${queueIndex + 1}`;
      const icon = VEHICLE_ICONS[v.type] || '🚗';
      chip.innerHTML = `<span>${icon}</span> <span>${v.id}</span> <span class="chip-pos">#${queueIndex + 1}</span>`;
      return chip;
    };

    if (dir === 'North') {
      // NORTH: Approach travels SOUTH (↓).
      // Stop line is at the bottom of lane-north.
      // Vehicle 1 (fifoVehicles[0]) is nearest to the stop line (at the bottom).
      const spacer = document.createElement('div');
      spacer.className = 'lane-spacer';
      laneContainer.appendChild(spacer);

      for (let i = fifoVehicles.length - 1; i >= 0; i--) {
        laneContainer.appendChild(createChip(fifoVehicles[i], i));
      }

      if (countChanged) {
        laneContainer.scrollTop = laneContainer.scrollHeight;
      }

    } else if (dir === 'South') {
      // SOUTH: Approach travels NORTH (↑).
      // Stop line is at the top of lane-south.
      // Vehicle 1 (fifoVehicles[0]) is nearest to the stop line (at the top).
      for (let i = 0; i < fifoVehicles.length; i++) {
        laneContainer.appendChild(createChip(fifoVehicles[i], i));
      }
      const spacer = document.createElement('div');
      spacer.className = 'lane-spacer';
      laneContainer.appendChild(spacer);

      if (countChanged) {
        laneContainer.scrollTop = 0;
      }

    } else if (dir === 'East') {
      // EAST: Approach travels WEST (←).
      // Stop line is at the left of lane-east.
      // Vehicle 1 (fifoVehicles[0]) is nearest to the stop line (at the left).
      for (let i = 0; i < fifoVehicles.length; i++) {
        laneContainer.appendChild(createChip(fifoVehicles[i], i));
      }
      const spacer = document.createElement('div');
      spacer.className = 'lane-spacer';
      laneContainer.appendChild(spacer);

      if (countChanged) {
        laneContainer.scrollLeft = 0;
      }

    } else if (dir === 'West') {
      // WEST: Approach travels EAST (→).
      // Stop line is at the right of lane-west.
      // Vehicle 1 (fifoVehicles[0]) is nearest to the stop line (at the right).
      const spacer = document.createElement('div');
      spacer.className = 'lane-spacer';
      laneContainer.appendChild(spacer);

      for (let i = fifoVehicles.length - 1; i >= 0; i--) {
        laneContainer.appendChild(createChip(fifoVehicles[i], i));
      }

      if (countChanged) {
        laneContainer.scrollLeft = laneContainer.scrollWidth;
      }
    }
  });
}

// ---------------------------------------------------------------------------
// Directional Queues Tabs & List
// ---------------------------------------------------------------------------
function renderDirectionalQueues(queues) {
  if (!queues) return;

  // Update tab counters
  ['North', 'East', 'South', 'West'].forEach(dir => {
    const pill = document.getElementById(`tab-pill-${dir.toLowerCase()}`);
    if (pill && queues[dir]) {
      pill.textContent = queues[dir].size;
    }
  });

  const activeQueue = queues[state.activeQueueTab];
  const listContainer = document.getElementById('queue-items-list');
  if (!listContainer || !activeQueue) return;

  const items = activeQueue.fifo_items || [];
  if (items.length === 0) {
    listContainer.innerHTML = `
      <div class="queue-empty-placeholder">
        <span>No vehicles currently waiting at ${state.activeQueueTab} approach</span>
      </div>`;
    return;
  }

  listContainer.innerHTML = '';
  items.forEach((v, index) => {
    const row = document.createElement('div');
    row.className = `queue-item-row ${v.is_emergency ? 'is-emergency' : ''}`;

    const icon = VEHICLE_ICONS[v.type] || '🚗';
    const waitTime = state.lastState ? Math.max(0, state.lastState.sim_time - v.arrival_time) : 0;

    row.innerHTML = `
      <div class="queue-item-left">
        <span class="vehicle-type-badge">${icon}</span>
        <div>
          <div class="vehicle-id-tag">${v.id}</div>
          <div style="font-size:0.72rem; color:var(--text-dim);">${v.type} • Queue Pos: #${index + 1}</div>
        </div>
      </div>
      <div style="text-align:right;">
        <span class="metric-tag" style="${v.is_emergency ? 'background:rgba(239,68,68,0.2); color:#f87171;' : ''}">
          ${v.is_emergency ? '🚨 PRIORITY ' + v.priority : 'Normal'}
        </span>
        <div style="font-size:0.72rem; color:var(--text-muted); margin-top:2px;">Wait: ${waitTime}s</div>
      </div>
    `;
    listContainer.appendChild(row);
  });
}

// ---------------------------------------------------------------------------
// Circular Queue DSA Live Visualizer
// ---------------------------------------------------------------------------
function renderCircularQueueVisualizer(queueData) {
  if (!queueData) return;

  document.getElementById('dsa-capacity-val').textContent = queueData.capacity;
  document.getElementById('dsa-size-val').textContent = queueData.size;
  document.getElementById('dsa-front-val').textContent = queueData.front;
  document.getElementById('dsa-rear-val').textContent = queueData.rear;

  // Wrap around detection
  const wrapNotice = document.getElementById('wrap-around-notice');
  if (queueData.front > queueData.rear && queueData.rear !== -1) {
    wrapNotice.style.display = 'flex';
    wrapNotice.innerHTML = `
      <span>🔄 <strong>Modulo Wrap-Around Active!</strong> Rear index (<strong>${queueData.rear}</strong>) has wrapped around array capacity (<strong>${queueData.capacity}</strong>) ahead of Front (<strong>${queueData.front}</strong>) via <code>(rear + 1) % ${queueData.capacity}</code>.</span>
    `;
  } else {
    wrapNotice.style.display = 'flex';
    wrapNotice.innerHTML = `
      <span>📌 Array Capacity: <strong>${queueData.capacity}</strong> slots. Modulo indexing guarantees <strong>O(1)</strong> enqueue & dequeue without shifting elements.</span>
    `;
  }

  const grid = document.getElementById('array-slots-grid');
  grid.innerHTML = '';

  (queueData.slots || []).forEach(slot => {
    const box = document.createElement('div');
    const isEmg = slot.item && slot.item.is_emergency;

    box.className = `array-slot-box ${slot.is_occupied ? (isEmg ? 'emergency-occupied' : 'occupied') : ''}`;

    let pointersHtml = '';
    if (slot.is_front) pointersHtml += `<span class="pointer-badge pointer-front">▲ FRONT</span>`;
    if (slot.is_rear) pointersHtml += `<span class="pointer-badge pointer-rear">▼ REAR</span>`;

    const icon = slot.item ? (VEHICLE_ICONS[slot.item.type] || '🚗') : '';
    const label = slot.item ? `${icon} ${slot.item.id}` : '<span style="color:var(--text-dim);">[Empty]</span>';

    box.innerHTML = `
      <div class="slot-index-label">Index [${slot.index}]</div>
      <div class="slot-content-val">${label}</div>
      <div style="display:flex; flex-direction:column; gap:2px; align-items:center;">
        ${pointersHtml}
      </div>
    `;
    grid.appendChild(box);
  });
}

// ---------------------------------------------------------------------------
// Recent Audit Events Log
// ---------------------------------------------------------------------------
function renderEvents(events) {
  const container = document.getElementById('event-feed-container');
  if (!container || !events) return;

  container.innerHTML = '';
  events.slice(0, 15).reverse().forEach(evt => {
    const item = document.createElement('div');
    item.className = `event-log-item event-${evt.type}`;
    item.innerHTML = `
      <span style="font-family:var(--font-mono); color:var(--text-dim); font-size:0.7rem;">[#${evt.cycle || 0}]</span>
      <span>${evt.message}</span>
    `;
    container.appendChild(item);
  });
}

// ---------------------------------------------------------------------------
// Graph-Based Traffic Flow Network (SVG)
// ---------------------------------------------------------------------------
async function fetchInitialGraph() {
  try {
    const res = await fetch('/api/graph');
    if (!res.ok) throw new Error('Failed to load graph data');
    const data = await res.json();
    state.graphData = data;

    populateGraphSelects(data.nodes);
    renderGraphSVG(data, state.activeRoutePath);
  } catch (err) {
    console.error('Graph fetch error:', err);
  }
}

function populateGraphSelects(nodes) {
  const srcSelect = document.getElementById('route-source-select');
  const dstSelect = document.getElementById('route-target-select');
  if (!srcSelect || !dstSelect || !nodes) return;

  srcSelect.innerHTML = '';
  dstSelect.innerHTML = '';

  nodes.forEach((n, idx) => {
    const optSrc = new Option(`${n.id}: ${n.name}`, n.id);
    const optDst = new Option(`${n.id}: ${n.name}`, n.id);
    srcSelect.add(optSrc);
    dstSelect.add(optDst);
  });

  // Pick interesting default pair: Uptown Hospital (INT-6) to South Ring (INT-4)
  srcSelect.value = 'INT-6';
  dstSelect.value = 'INT-4';
}

function renderGraphSVG(graphData, highlightedPath = []) {
  const svg = document.getElementById('city-traffic-svg');
  if (!svg || !graphData) return;

  svg.innerHTML = '';

  const nodesMap = {};
  graphData.nodes.forEach(n => { nodesMap[n.id] = n; });

  // Draw Edges
  const drawnEdges = new Set();
  (graphData.edges || []).forEach(edge => {
    const pairKey = [edge.from, edge.to].sort().join('--');
    if (drawnEdges.has(pairKey)) return;
    drawnEdges.add(pairKey);

    const u = nodesMap[edge.from];
    const v = nodesMap[edge.to];
    if (!u || !v) return;

    // Check if this edge is part of the highlighted route path
    let isPathEdge = false;
    for (let i = 0; i < highlightedPath.length - 1; i++) {
      if ((highlightedPath[i] === edge.from && highlightedPath[i+1] === edge.to) ||
          (highlightedPath[i] === edge.to && highlightedPath[i+1] === edge.from)) {
        isPathEdge = true;
        break;
      }
    }

    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', u.x);
    line.setAttribute('y1', u.y);
    line.setAttribute('x2', v.x);
    line.setAttribute('y2', v.y);
    line.setAttribute('stroke', isPathEdge ? '#38bdf8' : edge.stroke_color);
    line.setAttribute('stroke-width', isPathEdge ? '5' : '3');
    if (isPathEdge) {
      line.setAttribute('stroke-dasharray', '8,4');
      line.setAttribute('filter', 'drop-shadow(0 0 8px #0ea5e9)');
    } else {
      line.setAttribute('stroke-opacity', '0.75');
    }
    svg.appendChild(line);

    // Edge label (distance & cost)
    const midX = (u.x + v.x) / 2;
    const midY = (u.y + v.y) / 2;
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', midX);
    text.setAttribute('y', midY - 6);
    text.setAttribute('fill', '#94a3b8');
    text.setAttribute('font-size', '9');
    text.setAttribute('font-family', 'ui-monospace, monospace');
    text.setAttribute('text-anchor', 'middle');
    text.textContent = `${edge.distance_km}km (${edge.congestion_status})`;
    svg.appendChild(text);
  });

  // Draw Nodes (Intersections)
  graphData.nodes.forEach(node => {
    const isNodeInPath = highlightedPath.includes(node.id);

    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    group.setAttribute('cursor', 'pointer');

    // Outer glow circle
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', node.x);
    circle.setAttribute('cy', node.y);
    circle.setAttribute('r', isNodeInPath ? '18' : '14');
    circle.setAttribute('fill', isNodeInPath ? '#0284c7' : '#1e293b');
    circle.setAttribute('stroke', isNodeInPath ? '#38bdf8' : '#0ea5e9');
    circle.setAttribute('stroke-width', isNodeInPath ? '3' : '2');
    if (isNodeInPath) {
      circle.setAttribute('filter', 'drop-shadow(0 0 10px #38bdf8)');
    }
    group.appendChild(circle);

    // Node ID text
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', node.x);
    text.setAttribute('y', node.y + 4);
    text.setAttribute('fill', '#ffffff');
    text.setAttribute('font-size', '9');
    text.setAttribute('font-weight', '700');
    text.setAttribute('font-family', 'ui-monospace, monospace');
    text.setAttribute('text-anchor', 'middle');
    text.textContent = node.id.replace('INT-', 'J');
    group.appendChild(text);

    // Node Name label
    const nameText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    nameText.setAttribute('x', node.x);
    nameText.setAttribute('y', node.y + 28);
    nameText.setAttribute('fill', '#cbd5e1');
    nameText.setAttribute('font-size', '10');
    nameText.setAttribute('font-weight', '600');
    nameText.setAttribute('text-anchor', 'middle');
    nameText.textContent = node.name;
    group.appendChild(nameText);

    svg.appendChild(group);
  });
}

// ---------------------------------------------------------------------------
// Route Calculation Handler (BFS vs Dijkstra)
// ---------------------------------------------------------------------------
async function handleCalculateRoute() {
  const source = document.getElementById('route-source-select').value;
  const destination = document.getElementById('route-target-select').value;
  const algorithm = document.querySelector('input[name="route-algo"]:checked').value;
  const resultBox = document.getElementById('route-result-container');

  resultBox.innerHTML = '<div style="color:var(--text-muted);">Calculating route...</div>';

  try {
    const res = await fetch('/api/graph/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source, destination, algorithm })
    });

    const data = await res.json();
    if (!res.ok || !data.found) {
      resultBox.innerHTML = `
        <div style="color:#f87171;">⚠️ ${data.error || 'No route could be found.'}</div>`;
      state.activeRoutePath = [];
      renderGraphSVG(state.graphData, []);
      return;
    }

    state.activeRoutePath = data.path;
    renderGraphSVG(state.graphData, data.path);

    const pathSequence = data.path_names.join(' ➔ ');
    resultBox.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:0.5rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="color:#38bdf8; font-size:0.9rem;">${data.algorithm}</strong>
          <span class="metric-tag">${data.hops} Hops</span>
        </div>
        <div style="background:rgba(0,0,0,0.3); padding:0.5rem; border-radius:4px; font-size:0.78rem;">
          ${pathSequence}
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem; font-size:0.75rem;">
          <div>Distance: <strong>${data.total_distance_km} km</strong></div>
          <div>Estimated Travel Time: <strong>${data.total_cost_minutes} min</strong></div>
        </div>
        <div style="font-size:0.72rem; color:var(--text-muted); font-style:italic;">
          ${data.explanation}
        </div>
      </div>
    `;
  } catch (err) {
    resultBox.innerHTML = `<div style="color:#f87171;">Error: ${err.message}</div>`;
  }
}

// ---------------------------------------------------------------------------
// Queue-Based vs Graph-Based Comparison Fetch
// ---------------------------------------------------------------------------
async function fetchComparisonData() {
  try {
    const res = await fetch('/api/comparison');
    if (!res.ok) return;
    const comp = await res.json();
    renderComparisonTable(comp);
  } catch (e) {
    console.warn('Comparison fetch error:', e);
  }
}

function renderComparisonTable(data) {
  const container = document.getElementById('comparison-table-content');
  if (!container || !data) return;

  const q = data.micro_level_queue;
  const g = data.macro_level_graph;

  container.innerHTML = `
    <table class="comparison-table">
      <thead>
        <tr>
          <th>Comparison Dimension</th>
          <th>Queue-Based Scheduling (Micro Layer)</th>
          <th>Graph-Based Analysis (Macro Layer)</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Purpose</strong></td>
          <td>${q.purpose}</td>
          <td>${g.purpose}</td>
        </tr>
        <tr>
          <td><strong>Data Structure</strong></td>
          <td><span class="metric-tag">${q.data_structure}</span></td>
          <td><span class="metric-tag">${g.data_structure}</span></td>
        </tr>
        <tr>
          <td><strong>Operational Scope</strong></td>
          <td>${q.operational_scope}</td>
          <td>${g.operational_scope}</td>
        </tr>
        <tr>
          <td><strong>Time Complexity</strong></td>
          <td><code>${q.time_complexity}</code></td>
          <td><code>${g.time_complexity}</code></td>
        </tr>
        <tr>
          <td><strong>Space Complexity</strong></td>
          <td><code>${q.space_complexity}</code></td>
          <td><code>${g.space_complexity}</code></td>
        </tr>
        <tr>
          <td><strong>Live Evaluation Metrics</strong></td>
          <td>Total Served: <strong>${q.current_live_metrics.total_served}</strong> | Avg Wait: <strong>${q.current_live_metrics.avg_waiting_time_sec}s</strong></td>
          <td>Intersections: <strong>${g.current_live_metrics.total_intersections}</strong> | Congestion: <strong>${g.current_live_metrics.city_congestion_score}</strong></td>
        </tr>
      </tbody>
    </table>
    <div style="margin-top:0.75rem; font-size:0.78rem; color:var(--text-muted); font-style:italic;">
      💡 ${data.educational_synthesis}
    </div>
  `;
}

// ---------------------------------------------------------------------------
// UI Event Handlers & API Calls
// ---------------------------------------------------------------------------
function initEventListeners() {
  // Simulation Controls
  document.getElementById('btn-start').addEventListener('click', () => postAction('/api/simulation/start'));
  document.getElementById('btn-pause').addEventListener('click', () => postAction('/api/simulation/pause'));
  document.getElementById('btn-resume').addEventListener('click', () => postAction('/api/simulation/resume'));
  document.getElementById('btn-reset').addEventListener('click', async () => {
    await postAction('/api/simulation/reset');
    state.animatedDepartedIds.clear();
    state.prevQueueCounts = {};
    const layer = document.getElementById('intersection-crossing-layer');
    if (layer) layer.innerHTML = '';
  });
  document.getElementById('btn-step').addEventListener('click', () => postAction('/api/simulation/step', { dt: 1 }));
  document.getElementById('btn-batch-add').addEventListener('click', () => postAction('/api/vehicles/batch', { count: 4 }));

  // Quick Approach Buttons
  document.querySelectorAll('.approach-btn-mini').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const dir = e.target.getAttribute('data-dir');
      const isEmg = e.target.getAttribute('data-emg') === 'true';
      const type = isEmg ? 'Ambulance' : 'Car';
      postAction('/api/vehicles/add', { direction: dir, vehicle_type: type });
    });
  });

  // Manual Dispatcher Form
  const dispatchBtn = document.getElementById('btn-dispatch-vehicle');
  if (dispatchBtn) {
    dispatchBtn.addEventListener('click', () => {
      const dir = document.getElementById('dispatch-direction-select').value;
      const type = document.getElementById('dispatch-type-select').value;
      postAction('/api/vehicles/add', { direction: dir, vehicle_type: type });
    });
  }

  // Queue Direction Tabs
  document.querySelectorAll('.queue-tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.queue-tab-btn').forEach(b => b.classList.remove('active'));
      const targetBtn = e.currentTarget;
      targetBtn.classList.add('active');
      state.activeQueueTab = targetBtn.getAttribute('data-direction');
      if (state.lastState) renderDirectionalQueues(state.lastState.queues);
    });
  });

  // DSA Visualizer Selector
  const dsaSelect = document.getElementById('dsa-visualizer-select');
  if (dsaSelect) {
    dsaSelect.addEventListener('change', (e) => {
      state.selectedVisualizerQueue = e.target.value;
      if (state.lastState && state.lastState.queues) {
        renderCircularQueueVisualizer(state.lastState.queues[state.selectedVisualizerQueue]);
      }
    });
  }

  // Route Calculate Button
  const calcRouteBtn = document.getElementById('btn-calculate-route');
  if (calcRouteBtn) {
    calcRouteBtn.addEventListener('click', handleCalculateRoute);
  }

  // Settings Modal Handlers
  const configBtn = document.getElementById('btn-open-config');
  const modal = document.getElementById('config-modal');
  const closeBtn = document.getElementById('btn-close-config');
  const saveConfigBtn = document.getElementById('btn-save-config');

  if (configBtn && modal) {
    configBtn.addEventListener('click', () => modal.classList.add('open'));
    closeBtn.addEventListener('click', () => modal.classList.remove('open'));
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.classList.remove('open');
    });

    saveConfigBtn.addEventListener('click', async () => {
      const green = parseInt(document.getElementById('input-green-duration').value, 10);
      const yellow = parseInt(document.getElementById('input-yellow-duration').value, 10);
      const strategy = document.getElementById('input-strategy-select').value;

      await postAction('/api/simulation/config', {
        green_duration: green,
        yellow_duration: yellow,
        strategy: strategy
      });
      modal.classList.remove('open');
    });
  }
}

async function postAction(endpoint, payload = {}) {
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.error || data.message || 'Operation failed');
    }
    fetchSimulationState();
  } catch (err) {
    console.error(`Error requesting ${endpoint}:`, err);
  }
}
