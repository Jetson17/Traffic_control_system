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

const VEHICLE_COLORS = {
  'Car': '#2563eb',
  'Bus': '#d97706',
  'Truck': '#475569',
  'Bike': '#0f766e',
  'Ambulance': '#dc2626',
  'Fire Engine': '#b91c1c',
  'Police Vehicle': '#334155'
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

    renderSimulationControls(data);
    renderIntersectionSignals(data);
    renderIntersectionVehicles(data);
    renderStatistics(data.statistics);
    renderDirectionalQueues(data.queues);
    renderCircularQueueVisualizer(data.queues[state.selectedVisualizerQueue]);
  } catch (err) {
    console.warn('Simulation state poll error:', err.message);
  }
}

// ---------------------------------------------------------------------------
// Telemetry & Header Rendering
// ---------------------------------------------------------------------------
function renderSimulationControls(data) {
  const status = data.status || 'STOPPED';

  // Button states
  document.getElementById('btn-start').disabled = (status === 'RUNNING');
  document.getElementById('btn-pause').disabled = (status !== 'RUNNING');
  document.getElementById('btn-start').lastChild.textContent = status === 'PAUSED' ? 'Resume' : 'Start';
}

// ---------------------------------------------------------------------------
// Statistics Cards
// ---------------------------------------------------------------------------
function renderStatistics(stats) {
  if (!stats) return;

  document.getElementById('stat-total-waiting').textContent = stats.total_waiting;
  document.getElementById('stat-total-served').textContent = stats.total_served;
  document.getElementById('stat-avg-wait').textContent = `${stats.average_waiting_time}s`;
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

  });
}

function vehicleArtwork(vehicle) {
  const color = VEHICLE_COLORS[vehicle.type] || VEHICLE_COLORS.Car;
  const isBike = vehicle.type === 'Bike';
  const isLarge = vehicle.type === 'Bus' || vehicle.type === 'Truck' || vehicle.type === 'Fire Engine';
  const body = isBike
    ? '<path d="M20 10h8l4 12-4 42h-8l-4-42z"/>'
    : isLarge
      ? '<rect x="9" y="5" width="30" height="66" rx="5"/><rect x="14" y="10" width="20" height="28" rx="2" fill="#cbd5e1"/><rect x="14" y="44" width="20" height="20" rx="2" fill="#e2e8f0"/>'
      : '<path d="M15 5h18l7 13v39l-7 14H15L8 57V18z"/><path d="M15 22q1-5 6-5h6q5 0 6 5l3 12H12z" fill="#bfdbfe"/><path d="M13 49h22l-4 10H17z" fill="#dbeafe"/>';
  const emergencyMark = vehicle.is_emergency
    ? '<path d="M21 39h6v-5h5v5h5v6h-5v5h-5v-5h-6z" fill="#fff"/>'
    : '';
  return `<svg class="vehicle-art" viewBox="0 0 48 76" aria-hidden="true">
    <rect x="4" y="18" width="5" height="14" rx="2" fill="#1e293b"/>
    <rect x="39" y="18" width="5" height="14" rx="2" fill="#1e293b"/>
    <rect x="4" y="48" width="5" height="14" rx="2" fill="#1e293b"/>
    <rect x="39" y="48" width="5" height="14" rx="2" fill="#1e293b"/>
    <g fill="${color}" stroke="#fff" stroke-opacity=".8" stroke-width="1.5">${body}</g>
    ${emergencyMark}
    <circle cx="17" cy="9" r="2" fill="#fde68a"/><circle cx="31" cy="9" r="2" fill="#fde68a"/>
  </svg>`;
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
  chip.innerHTML = vehicleArtwork(vehicle);
  chip.title = `${vehicle.type} (${vehicle.id})`;

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

    const createChip = v => {
      const chip = document.createElement('div');
      chip.className = `vehicle-mini-chip ${v.is_emergency ? 'emergency' : ''}`;
      chip.setAttribute('data-id', v.id);
      chip.title = `${v.type} (${v.id})`;
      chip.setAttribute('aria-label', `${v.type} ${v.id}${v.is_emergency ? ', emergency vehicle' : ''}`);
      chip.innerHTML = vehicleArtwork(v);
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
        laneContainer.appendChild(createChip(fifoVehicles[i]));
      }

      if (countChanged) {
        laneContainer.scrollTop = laneContainer.scrollHeight;
      }

    } else if (dir === 'South') {
      // SOUTH: Approach travels NORTH (↑).
      // Stop line is at the top of lane-south.
      // Vehicle 1 (fifoVehicles[0]) is nearest to the stop line (at the top).
      for (let i = 0; i < fifoVehicles.length; i++) {
        laneContainer.appendChild(createChip(fifoVehicles[i]));
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
        laneContainer.appendChild(createChip(fifoVehicles[i]));
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
        laneContainer.appendChild(createChip(fifoVehicles[i]));
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

  const activeQueue = queues[state.activeQueueTab];
  const listContainer = document.getElementById('queue-items-list');
  if (!listContainer || !activeQueue) return;

  const items = activeQueue.fifo_items || [];
  if (items.length === 0) {
    listContainer.innerHTML = '<div class="queue-empty-placeholder">No waiting vehicles</div>';
    return;
  }

  listContainer.innerHTML = '';
  items.forEach(v => {
    const row = document.createElement('div');
    row.className = `queue-item-row ${v.is_emergency ? 'is-emergency' : ''}`;
    const vehicle = document.createElement('span');
    vehicle.className = `queue-vehicle ${v.is_emergency ? 'emergency' : ''}`;
    vehicle.innerHTML = vehicleArtwork(v);
    vehicle.setAttribute('aria-hidden', 'true');
    const details = document.createElement('div');
    details.className = 'queue-vehicle-details';
    const id = document.createElement('strong');
    id.textContent = v.id;
    const type = document.createElement('span');
    type.textContent = v.type;
    details.append(id, type);
    row.append(vehicle, details);
    if (v.is_emergency) {
      const emergency = document.createElement('span');
      emergency.className = 'queue-emergency-label';
      emergency.textContent = 'Emergency';
      row.appendChild(emergency);
    }
    listContainer.appendChild(row);
  });
}

// ---------------------------------------------------------------------------
// Circular Queue DSA Live Visualizer
// ---------------------------------------------------------------------------
function renderCircularQueueVisualizer(queueData) {
  if (!queueData) return;

  document.getElementById('dsa-front-val').textContent = queueData.front;
  document.getElementById('dsa-rear-val').textContent = queueData.rear;

  // Report when the live circular buffer has wrapped.
  const wrapNotice = document.getElementById('wrap-around-notice');
  if (queueData.front > queueData.rear && queueData.rear !== -1) {
    wrapNotice.textContent = 'Circular wrap-around';
  } else {
    wrapNotice.textContent = '';
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

    const label = slot.item ? slot.item.id : '';

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
    line.setAttribute('stroke', isPathEdge ? '#2563eb' : edge.stroke_color);
    line.setAttribute('stroke-width', isPathEdge ? '5' : '3');
    if (isPathEdge) {
      line.setAttribute('stroke-dasharray', '8,4');
      line.setAttribute('filter', 'drop-shadow(0 0 5px rgba(37, 99, 235, 0.35))');
    } else {
      line.setAttribute('stroke-opacity', '0.75');
    }
    svg.appendChild(line);

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
    circle.setAttribute('fill', isNodeInPath ? '#2563eb' : '#ffffff');
    circle.setAttribute('stroke', isNodeInPath ? '#1d4ed8' : '#64748b');
    circle.setAttribute('stroke-width', isNodeInPath ? '3' : '2');
    if (isNodeInPath) {
      circle.setAttribute('filter', 'drop-shadow(0 2px 4px rgba(37, 99, 235, 0.3))');
    }
    group.appendChild(circle);

    // Node ID text
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', node.x);
    text.setAttribute('y', node.y + 4);
    text.setAttribute('fill', isNodeInPath ? '#ffffff' : '#172033');
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
    nameText.setAttribute('fill', '#475569');
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

  resultBox.textContent = 'Calculating route...';

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

    const route = document.createElement('p');
    route.className = 'route-sequence';
    route.textContent = data.path_names.join(' → ');
    const distance = document.createElement('strong');
    distance.textContent = `${data.total_distance_km} km`;
    resultBox.replaceChildren(route, distance);
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
        <tr><th></th><th>Circular Queue</th><th>Graph Analysis</th></tr>
      </thead>
      <tbody>
        <tr>
          <th scope="row">Purpose</th>
          <td>${q.purpose}</td>
          <td>${g.purpose}</td>
        </tr>
        <tr>
          <th scope="row">Structure</th>
          <td>${q.data_structure}</td>
          <td>${g.data_structure}</td>
        </tr>
        <tr>
          <th scope="row">Scope</th>
          <td>${q.operational_scope}</td>
          <td>${g.operational_scope}</td>
        </tr>
      </tbody>
    </table>
  `;
}

// ---------------------------------------------------------------------------
// UI Event Handlers & API Calls
// ---------------------------------------------------------------------------
function initEventListeners() {
  // Simulation Controls
  document.getElementById('btn-start').addEventListener('click', () => {
    const endpoint = state.lastState && state.lastState.status === 'PAUSED'
      ? '/api/simulation/resume'
      : '/api/simulation/start';
    postAction(endpoint);
  });
  document.getElementById('btn-pause').addEventListener('click', () => postAction('/api/simulation/pause'));
  document.getElementById('btn-reset').addEventListener('click', async () => {
    await postAction('/api/simulation/reset');
    state.animatedDepartedIds.clear();
    state.prevQueueCounts = {};
    const layer = document.getElementById('intersection-crossing-layer');
    if (layer) layer.innerHTML = '';
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

  const emergencyBtn = document.getElementById('btn-dispatch-emergency');
  if (emergencyBtn) {
    emergencyBtn.addEventListener('click', () => {
      const direction = document.getElementById('dispatch-direction-select').value;
      postAction('/api/vehicles/add', {
        direction,
        vehicle_type: 'Ambulance'
      });
    });
  }

  document.querySelectorAll('.dashboard-tab').forEach(tab => {
    tab.addEventListener('click', () => activateDashboardTab(tab));
    tab.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const tabs = Array.from(document.querySelectorAll('.dashboard-tab'));
      const index = tabs.indexOf(tab);
      const nextIndex = event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? tabs.length - 1
          : (index + (event.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length;
      activateDashboardTab(tabs[nextIndex]);
      tabs[nextIndex].focus();
    });
  });

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

}

function activateDashboardTab(activeTab) {
  const activePanelId = activeTab.getAttribute('aria-controls');

  document.querySelectorAll('.dashboard-tab').forEach(tab => {
    const selected = tab === activeTab;
    tab.classList.toggle('active', selected);
    tab.setAttribute('aria-selected', String(selected));
    tab.tabIndex = selected ? 0 : -1;
  });

  document.querySelectorAll('.tab-panel').forEach(panel => {
    panel.hidden = panel.id !== activePanelId;
  });
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
