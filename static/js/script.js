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
  selectedBfsStart: null,
  bfsResult: null,
  bfsStepIndex: -1,
  bfsTimer: null,
  bfsPlaying: false,
  animatedDepartedIds: new Set(),
  isInitialLoad: true,
  prevQueueCounts: {},
  notificationTimeout: null,
  comparisonInterval: null
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
  state.comparisonInterval = setInterval(fetchComparisonData, 2500);
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
  document.getElementById('btn-start').lastChild.textContent =
    status === 'PAUSED' ? ' Resume Simulation' : ' Start Simulation';
  document.getElementById('btn-pause').lastChild.textContent = ' Pause Simulation';
  const activeDirection = data.active_direction || '—';
  const phase = data.current_phase || '—';
  const statusLabel = document.getElementById('intersection-status');
  const priorityState = data.priority_state || 'NORMAL';
  const emergencyDirection = data.emergency && data.emergency.direction;
  statusLabel.classList.toggle(
    'emergency-state',
    priorityState !== 'NORMAL' && priorityState !== 'RESUME_NORMAL'
  );
  if (priorityState === 'EMERGENCY_PREPARATION') {
    statusLabel.textContent = `EMERGENCY DETECTED · ${emergencyDirection} · CLEARING`;
  } else if (priorityState === 'EMERGENCY_ACTIVE') {
    statusLabel.textContent = `EMERGENCY ACTIVE · ${emergencyDirection} · GREEN`;
  } else if (priorityState === 'RESUME_NORMAL') {
    statusLabel.textContent = 'Emergency crossed · normal scheduling resumes';
  } else {
    statusLabel.textContent = `${activeDirection} · ${phase} · ${status}`;
  }

  ['North', 'East', 'South', 'West'].forEach(direction => {
    const lane = document.getElementById(`lane-${direction.toLowerCase()}`);
    const fixture = document.getElementById(`light-${direction.toLowerCase()}`);
    const isEmergencyDirection = direction === emergencyDirection
      && priorityState !== 'NORMAL'
      && priorityState !== 'RESUME_NORMAL';
    lane?.classList.toggle('emergency-approach', isEmergencyDirection);
    fixture?.classList.toggle('emergency-priority', isEmergencyDirection);
  });
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
        if (v.is_emergency) {
          showNotification(`${v.type} ${v.id} crossed; normal scheduling is resuming.`, 'success');
        }
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

  document.querySelectorAll('[data-queue-count]').forEach(count => {
    const direction = count.getAttribute('data-queue-count');
    count.textContent = queues[direction] ? queues[direction].size : 0;
  });

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
  document.getElementById('dsa-size-val').textContent =
    `${queueData.size} / ${queueData.capacity}`;
  document.getElementById('dsa-status-val').textContent = queueData.is_full
    ? 'Full'
    : queueData.is_empty
      ? 'Empty'
      : 'Active';

  const wrapNotice = document.getElementById('wrap-around-notice');
  if (queueData.front > queueData.rear && queueData.rear !== -1) {
    wrapNotice.textContent = 'Wrap-around: the rear has looped to an earlier array slot.';
  } else {
    wrapNotice.textContent = '';
  }

  const grid = document.getElementById('array-slots-grid');
  grid.style.gridTemplateColumns = `repeat(${queueData.capacity}, minmax(0, 1fr))`;
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
    fetchComparisonData();
  } catch (err) {
    console.error('Graph fetch error:', err);
  }
}

function populateGraphSelects(nodes) {
  const srcSelect = document.getElementById('route-source-select');
  const dstSelect = document.getElementById('route-target-select');
  const bfsSelect = document.getElementById('bfs-start-select');
  if (!srcSelect || !dstSelect || !bfsSelect || !nodes) return;

  srcSelect.innerHTML = '';
  dstSelect.innerHTML = '';
  bfsSelect.innerHTML = '';

  nodes.forEach(n => {
    const optSrc = new Option(`${n.id}: ${n.name}`, n.id);
    const optDst = new Option(`${n.id}: ${n.name}`, n.id);
    const optBfs = new Option(`${n.id}: ${n.name}`, n.id);
    srcSelect.add(optSrc);
    dstSelect.add(optDst);
    bfsSelect.add(optBfs);
  });

  srcSelect.selectedIndex = 0;
  dstSelect.selectedIndex = Math.min(1, nodes.length - 1);
  bfsSelect.selectedIndex = 0;
  state.selectedBfsStart = bfsSelect.value || null;
  renderBfsPanel();
}

function renderGraphSVG(graphData, highlightedPath = []) {
  const svg = document.getElementById('city-traffic-svg');
  if (!svg || !graphData) return;

  svg.innerHTML = '';

  const nodesMap = {};
  graphData.nodes.forEach(n => { nodesMap[n.id] = n; });

  const showWeights = document.querySelector('input[name="route-algo"]:checked')?.value === 'dijkstra';
  const currentStep = state.bfsResult?.steps[state.bfsStepIndex];
  const activeNode = currentStep?.current;
  const visitedNodes = new Set((currentStep?.traversal_order || []).slice(0, -1));
  const discoveredNodes = new Set([
    ...(currentStep?.queue || []),
    ...(currentStep?.newly_discovered || [])
  ]);
  if (state.bfsResult && state.bfsStepIndex >= 0) {
    discoveredNodes.add(state.bfsResult.start);
  }

  // Draw edges and, for weighted routing, their current travel-time weights.
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

    if (showWeights) {
      const weight = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      weight.setAttribute('x', (u.x + v.x) / 2);
      weight.setAttribute('y', (u.y + v.y) / 2 - 5);
      weight.setAttribute('fill', '#334155');
      weight.setAttribute('stroke', '#ffffff');
      weight.setAttribute('stroke-width', '4');
      weight.setAttribute('paint-order', 'stroke');
      weight.setAttribute('font-size', '11');
      weight.setAttribute('font-weight', '600');
      weight.setAttribute('text-anchor', 'middle');
      weight.textContent = `${edge.travel_cost_minutes} min`;
      svg.appendChild(weight);
    }

  });

  // Draw Nodes (Intersections)
  graphData.nodes.forEach(node => {
    const isNodeInPath = highlightedPath.includes(node.id);
    const isActive = node.id === activeNode;
    const isVisited = visitedNodes.has(node.id);
    const isDiscovered = discoveredNodes.has(node.id);
    const isStart = node.id === (state.bfsResult?.start || state.selectedBfsStart);
    const fill = isActive ? '#f59e0b'
      : isVisited || isNodeInPath ? '#2563eb'
        : isDiscovered ? '#bfdbfe' : '#ffffff';
    const stroke = isActive ? '#b45309'
      : isStart ? '#1d4ed8'
        : isVisited || isNodeInPath ? '#1d4ed8'
          : isDiscovered ? '#2563eb' : '#64748b';

    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    group.setAttribute('cursor', 'pointer');
    group.setAttribute('class', `graph-node${isActive ? ' bfs-node-active' : ''}${isVisited ? ' bfs-node-visited' : ''}${isDiscovered ? ' bfs-node-discovered' : ''}${isStart ? ' bfs-node-start' : ''}`);
    group.setAttribute('tabindex', '0');
    group.setAttribute('role', 'button');
    group.setAttribute('aria-label', `${node.name}${isStart ? ', BFS start' : ''}`);
    group.addEventListener('click', () => selectBfsStart(node.id));
    group.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        selectBfsStart(node.id);
      }
    });

    // Outer glow circle
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', node.x);
    circle.setAttribute('cy', node.y);
    circle.setAttribute('r', isActive || isNodeInPath ? '18' : '14');
    circle.setAttribute('fill', fill);
    circle.setAttribute('stroke', stroke);
    circle.setAttribute('stroke-width', isActive || isStart || isNodeInPath ? '3' : '2');
    if (isNodeInPath || isActive) {
      circle.setAttribute('filter', 'drop-shadow(0 2px 4px rgba(37, 99, 235, 0.3))');
    }
    group.appendChild(circle);

    // Node ID text
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', node.x);
    text.setAttribute('y', node.y + 4);
    text.setAttribute('fill', isActive || isVisited || isNodeInPath ? '#ffffff' : '#172033');
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
    const lines = [];
    let line = '';
    node.name.split(/\s+/).forEach(word => {
      if (line && `${line} ${word}`.length > 16) {
        lines.push(line);
        line = word;
      } else {
        line = line ? `${line} ${word}` : word;
      }
    });
    if (line) lines.push(line);
    lines.forEach((label, index) => {
      const tspan = document.createElementNS('http://www.w3.org/2000/svg', 'tspan');
      tspan.setAttribute('x', node.x);
      tspan.setAttribute('dy', index === 0 ? '0' : '12');
      tspan.textContent = label;
      nameText.appendChild(tspan);
    });
    group.appendChild(nameText);

    svg.appendChild(group);
  });
}

function selectBfsStart(nodeId) {
  const select = document.getElementById('bfs-start-select');
  if (!select) return;
  select.value = nodeId;
  state.selectedBfsStart = nodeId;
  resetBfsTraversal();
}

async function runBfsTraversal() {
  const select = document.getElementById('bfs-start-select');
  const start = select?.value;
  const button = document.getElementById('btn-run-bfs');
  if (!start) {
    showNotification('Select a starting intersection.', 'error');
    return;
  }

  button.disabled = true;
  try {
    const response = await fetch('/api/graph/bfs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source: start })
    });
    const result = await response.json();
    if (!response.ok || !result.found) {
      throw new Error(result.error || 'Unable to run BFS.');
    }
    if (select.value !== start) return;

    stopBfsPlayback();
    state.activeRoutePath = [];
    state.bfsResult = result;
    state.bfsStepIndex = result.steps.length ? 0 : -1;
    renderBfsPanel();
    renderGraphSVG(state.graphData, []);
    showNotification(`BFS started from ${result.start_name}.`, 'success');
  } catch (error) {
    resetBfsTraversal();
    document.getElementById('bfs-connectivity-message').textContent = error.message;
    showNotification(error.message, 'error');
  } finally {
    button.disabled = false;
  }
}

function stepBfsForward() {
  if (!state.bfsResult || state.bfsStepIndex >= state.bfsResult.steps.length - 1) {
    stopBfsPlayback();
    return;
  }
  state.bfsStepIndex += 1;
  renderBfsPanel();
  renderGraphSVG(state.graphData, []);
}

function toggleBfsPlayback() {
  if (state.bfsPlaying) {
    stopBfsPlayback();
    return;
  }
  if (!state.bfsResult || state.bfsStepIndex >= state.bfsResult.steps.length - 1) return;
  state.bfsPlaying = true;
  const button = document.getElementById('btn-bfs-play');
  button.textContent = 'Pause';
  state.bfsTimer = setInterval(() => {
    if (state.bfsStepIndex >= state.bfsResult.steps.length - 1) {
      stopBfsPlayback();
      return;
    }
    stepBfsForward();
    if (state.bfsStepIndex >= state.bfsResult.steps.length - 1) stopBfsPlayback();
  }, 750);
}

function stopBfsPlayback() {
  if (state.bfsTimer) clearInterval(state.bfsTimer);
  state.bfsTimer = null;
  state.bfsPlaying = false;
  const button = document.getElementById('btn-bfs-play');
  if (button) button.textContent = 'Play';
}

function renderBfsPanel() {
  const result = state.bfsResult;
  const step = result?.steps[state.bfsStepIndex];
  const nodeNames = new Map((state.graphData?.nodes || []).map(node => [node.id, node.name]));
  const label = id => nodeNames.get(id) || id;
  const traversalList = document.getElementById('bfs-traversal-order');
  const queueList = document.getElementById('bfs-current-queue');
  const discoveredList = document.getElementById('bfs-newly-discovered');
  if (!traversalList || !queueList || !discoveredList) return;

  const populateList = (element, values, ordered = false) => {
    element.replaceChildren();
    values.forEach((id, index) => {
      const item = document.createElement('li');
      item.textContent = `${ordered ? `${index + 1}. ` : ''}${label(id)}`;
      element.appendChild(item);
    });
    if (!values.length) {
      const item = document.createElement('li');
      item.textContent = '—';
      item.className = 'bfs-empty-item';
      element.appendChild(item);
    }
  };

  const started = Boolean(result);
  const finished = Boolean(step && state.bfsStepIndex === result.steps.length - 1);
  const seen = step?.traversal_order || [];
  const selectedStart = state.selectedBfsStart
    ? `${state.selectedBfsStart}: ${label(state.selectedBfsStart)}`
    : '—';
  document.getElementById('bfs-start-name').textContent =
    result ? `${result.start}: ${result.start_name}` : selectedStart;
  document.getElementById('bfs-current-node').textContent = step ? label(step.current) : '—';
  document.getElementById('bfs-visited-count').textContent =
    `${seen.length} / ${result?.total_vertices || state.graphData?.nodes.length || 0}`;
  document.getElementById('bfs-step-count').textContent =
    `Step ${step ? state.bfsStepIndex + 1 : 0} of ${result?.steps.length || 0}`;
  populateList(traversalList, seen, true);
  populateList(queueList, step?.queue || []);
  populateList(discoveredList, step?.newly_discovered || []);

  document.getElementById('btn-bfs-step').disabled = !started || finished;
  document.getElementById('btn-bfs-play').disabled = !started || finished;

  const message = document.getElementById('bfs-connectivity-message');
  const reachableCount = document.getElementById('bfs-reachable-count');
  const reachableList = document.getElementById('bfs-reachable-list');
  const unreachableList = document.getElementById('bfs-unreachable-list');
  if (!started) {
    message.textContent = 'Run BFS to explore intersections reachable from the selected start.';
    reachableCount.textContent = '—';
    reachableList.textContent = '—';
    unreachableList.textContent = '—';
  } else if (finished) {
    const allReachable = result.is_fully_reachable;
    message.textContent = allReachable
      ? 'Every intersection is reachable from this starting point.'
      : 'This road network is disconnected; BFS visits only intersections reachable from the starting point.';
    reachableCount.textContent = `${result.vertices_visited} / ${result.total_vertices}`;
    reachableList.textContent = result.reachable_names.join(', ') || 'None';
    unreachableList.textContent = result.unreachable_names.join(', ') || 'None';
  } else {
    message.textContent = `BFS is exploring from ${result.start_name}. Connectivity results appear when traversal completes.`;
    reachableCount.textContent = `${seen.length + (step?.queue.length || 0)} / ${result.total_vertices} discovered`;
    reachableList.textContent = 'Traversal in progress';
    unreachableList.textContent = '—';
  }
}

function resetBfsTraversal() {
  stopBfsPlayback();
  state.bfsResult = null;
  state.bfsStepIndex = -1;
  renderBfsPanel();
  if (state.graphData) renderGraphSVG(state.graphData, state.activeRoutePath);
}

// ---------------------------------------------------------------------------
// Route Calculation Handler (BFS vs Dijkstra)
// ---------------------------------------------------------------------------
async function handleCalculateRoute() {
  const source = document.getElementById('route-source-select').value;
  const destination = document.getElementById('route-target-select').value;
  const algorithm = document.querySelector('input[name="route-algo"]:checked').value;
  const resultBox = document.getElementById('route-result-container');

  resultBox.textContent = 'Calculating route…';
  const calculateButton = document.getElementById('btn-calculate-route');
  calculateButton.disabled = true;

  try {
    const graphResponse = await fetch('/api/graph');
    if (!graphResponse.ok) throw new Error('Unable to refresh the road network.');
    state.graphData = await graphResponse.json();

    const res = await fetch('/api/graph/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source, destination, algorithm })
    });

    const data = await res.json();
    if (!res.ok || !data.found) {
      resultBox.textContent = data.error || 'No route could be found.';
      state.activeRoutePath = [];
      renderGraphSVG(state.graphData, []);
      showNotification(data.error || 'No route available.', 'error');
      return;
    }

    state.activeRoutePath = data.path;
    renderGraphSVG(state.graphData, data.path);

    const algorithmName = document.createElement('strong');
    algorithmName.textContent = data.algorithm;
    const route = document.createElement('p');
    route.className = 'route-sequence';
    route.textContent = data.path_names.join(' → ');
    const details = document.createElement('p');
    details.textContent = algorithm === 'dijkstra'
      ? `Total cost: ${data.total_cost_minutes} min · Distance: ${data.total_distance_km} km`
      : `Hops: ${data.hops} · Distance: ${data.total_distance_km} km`;
    resultBox.replaceChildren(algorithmName, route, details);

    if (algorithm === 'bfs' && Array.isArray(data.traversal_order)) {
      const traversal = document.createElement('p');
      traversal.className = 'route-traversal';
      traversal.textContent = `BFS traversal: ${data.traversal_order.join(' → ')}`;
      resultBox.appendChild(traversal);
    }
    showNotification('Route calculated.', 'success');
  } catch (err) {
    resultBox.textContent = `Unable to calculate route: ${err.message}`;
    showNotification(err.message, 'error');
  } finally {
    calculateButton.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Queue-Based vs Graph-Based Comparison Fetch
// ---------------------------------------------------------------------------
async function fetchComparisonData() {
  const source = document.getElementById('route-source-select').value;
  const destination = document.getElementById('route-target-select').value;
  const params = new URLSearchParams();
  if (source) params.set('source', source);
  if (destination) params.set('destination', destination);

  try {
    const res = await fetch(`/api/comparison?${params.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const comp = await res.json();
    renderComparisonTable(comp);
  } catch (error) {
    console.warn('Comparison fetch error:', error.message);
    const bfs = document.getElementById('comparison-bfs-result');
    const dijkstra = document.getElementById('comparison-dijkstra-result');
    if (bfs) bfs.textContent = 'Live graph analytics unavailable.';
    if (dijkstra) dijkstra.textContent = 'Live graph analytics unavailable.';
  }
}

function renderComparisonTable(data) {
  const container = document.getElementById('comparison-table-content');
  if (!container || !data) return;

  const q = data.micro_level_queue;
  const g = data.macro_level_graph;
  const live = data.live_analytics;
  if (!q || !g || !live) return;

  document.getElementById('comparison-queue-capacity').textContent =
    live.queue_capacity_per_direction ?? '—';
  document.querySelector('#comparison-queue-capacity + small').textContent =
    `${live.queue_capacity_total ?? '—'} total · vehicles per approach`;
  document.getElementById('comparison-queue-waiting').textContent =
    live.vehicles_waiting ?? '—';
  document.getElementById('comparison-queue-served').textContent =
    live.vehicles_served ?? '—';
  document.getElementById('comparison-queue-utilization').textContent =
    live.queue_utilization_percent == null ? '—' : `${live.queue_utilization_percent}%`;
  document.getElementById('comparison-graph-vertices').textContent = live.vertices ?? '—';
  document.getElementById('comparison-graph-edges').textContent = live.road_links ?? '—';

  const origin = live.origin;
  const destination = live.destination;
  document.getElementById('comparison-route-selection').textContent =
    origin && destination
      ? `${origin.name || origin.id || 'Unknown'} → ${destination.name || destination.id || 'Unknown'}`
      : 'Select a route in Graph Analysis';
  renderComparisonRoute('comparison-bfs-result', live.bfs, 'bfs');
  renderComparisonRoute('comparison-dijkstra-result', live.dijkstra, 'dijkstra');

  const rows = [
    ['Purpose', q.purpose, g.purpose],
    ['Data structure', q.data_structure, g.data_structure],
    ['Main operations', q.main_operations, g.main_operations],
    ['Algorithm', q.algorithm, g.algorithm],
    ['Time complexity', q.time_complexity, g.time_complexity],
    ['Space complexity', q.space_complexity, g.space_complexity],
    ['Application in this project', q.application, g.application]
  ];

  const table = document.createElement('table');
  table.className = 'comparison-table';
  table.innerHTML = '<thead><tr><th scope="col">Aspect</th><th scope="col">Circular Queue</th><th scope="col">Graph Analysis</th></tr></thead>';
  const body = document.createElement('tbody');
  rows.forEach(([label, queueValue, graphValue]) => {
    const row = document.createElement('tr');
    [label, queueValue, graphValue].forEach((value, index) => {
      const cell = document.createElement(index === 0 ? 'th' : 'td');
      if (index === 0) cell.setAttribute('scope', 'row');
      cell.textContent = value;
      row.appendChild(cell);
    });
    body.appendChild(row);
  });
  table.appendChild(body);
  container.replaceChildren(table);
}

function renderComparisonRoute(elementId, result, algorithm) {
  const container = document.getElementById(elementId);
  if (!container) return;
  if (!result) {
    container.textContent = 'Choose an origin and destination in Graph Analysis.';
    return;
  }
  if (!result.found) {
    container.textContent = result.error || 'No route is available for this selection.';
    return;
  }

  const path = document.createElement('p');
  path.className = 'comparison-route-path';
  path.textContent = (result.path_names || result.path || []).join(' → ');
  const details = document.createElement('p');
  details.className = 'comparison-route-details';
  details.textContent = algorithm === 'bfs'
    ? `${result.hops} hops · ${result.total_distance_km} km`
    : `${result.total_cost_minutes} min · ${result.total_distance_km} km`;
  container.replaceChildren(path, details);

  if (algorithm === 'bfs' && Array.isArray(result.traversal_order)) {
    const traversal = document.createElement('p');
    traversal.className = 'comparison-route-traversal';
    traversal.textContent = `Traversal: ${result.traversal_order.join(' → ')}`;
    container.appendChild(traversal);
  }
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
    await postAction('/api/simulation/reset', {}, 'Simulation reset.');
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

  document.getElementById('btn-queue-enqueue').addEventListener('click', () => {
    const vehicleType = document.getElementById('queue-enqueue-type').value;
    postAction('/api/vehicles/add', {
      direction: state.selectedVisualizerQueue,
      vehicle_type: vehicleType
    });
  });
  document.getElementById('btn-queue-dequeue').addEventListener('click', () => {
    postAction(`/api/queues/${state.selectedVisualizerQueue}/dequeue`);
  });
  document.getElementById('btn-queue-peek').addEventListener('click', () => {
    postAction(`/api/queues/${state.selectedVisualizerQueue}/peek`);
  });
  document.getElementById('btn-queue-clear').addEventListener('click', () => {
    postAction(`/api/queues/${state.selectedVisualizerQueue}/clear`);
  });

  // Route Calculate Button
  const calcRouteBtn = document.getElementById('btn-calculate-route');
  if (calcRouteBtn) {
    calcRouteBtn.addEventListener('click', handleCalculateRoute);
  }
  document.getElementById('btn-reset-route').addEventListener('click', resetRoute);
  document.getElementById('btn-run-bfs').addEventListener('click', runBfsTraversal);
  document.getElementById('btn-bfs-step').addEventListener('click', stepBfsForward);
  document.getElementById('btn-bfs-play').addEventListener('click', toggleBfsPlayback);
  document.getElementById('btn-bfs-reset').addEventListener('click', resetBfsTraversal);
  document.getElementById('bfs-start-select').addEventListener('change', event => {
    state.selectedBfsStart = event.target.value;
    resetBfsTraversal();
  });
  document.querySelectorAll('input[name="route-algo"]').forEach(option => {
    option.addEventListener('change', () => {
      resetRoute();
      if (state.graphData) renderGraphSVG(state.graphData, []);
    });
  });
  ['route-source-select', 'route-target-select'].forEach(id => {
    document.getElementById(id).addEventListener('change', () => {
      resetRoute();
      fetchComparisonData();
    });
  });

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

function resetRoute() {
  state.activeRoutePath = [];
  const resultBox = document.getElementById('route-result-container');
  resultBox.textContent = '';
  if (state.graphData) renderGraphSVG(state.graphData, []);
}

function showNotification(message, kind = 'success') {
  const notification = document.getElementById('app-notification');
  if (!notification || !message) return;
  notification.textContent = message;
  notification.dataset.kind = kind;
  notification.hidden = false;
  if (state.notificationTimeout) clearTimeout(state.notificationTimeout);
  state.notificationTimeout = setTimeout(() => {
    notification.hidden = true;
  }, 3000);
}

async function postAction(endpoint, payload = {}, successMessage = null) {
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) {
      showNotification(data.error || data.message || 'Operation failed.', 'error');
      return;
    }
    showNotification(successMessage || data.message || 'Operation completed.', 'success');
    await fetchSimulationState();
    fetchComparisonData();
  } catch (err) {
    console.error(`Error requesting ${endpoint}:`, err);
    showNotification(`Request failed: ${err.message}`, 'error');
  }
}
