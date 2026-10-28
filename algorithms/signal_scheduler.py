"""
Signal Scheduler Implementation for Traffic Signal Control System.

Module: algorithms.signal_scheduler
Features:
    - 4 Directions: North, East, South, West
    - Configurable GREEN and YELLOW durations
    - Deterministic phase transitions (GREEN -> YELLOW -> Next Direction GREEN)
    - Anti-collision guarantee: Strictly one movement group in green/yellow; others are RED.
    - Baseline fairness: Round-Robin scheduling
    - Adaptive Queue & Waiting-Time Dynamic Scheduling
    - Emergency vehicle prioritization with starvation-prevention safeguards
    - Audit event log for phase transitions and priority overrides
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from algorithms.circular_queue import CircularQueue


class SignalState(Enum):
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"


class SchedulingStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    ADAPTIVE_PRIORITY = "adaptive_priority"


class EmergencyPriorityState(Enum):
    NORMAL = "NORMAL"
    EMERGENCY_PREPARATION = "EMERGENCY_PREPARATION"
    EMERGENCY_ACTIVE = "EMERGENCY_ACTIVE"
    RESUME_NORMAL = "RESUME_NORMAL"


DIRECTIONS = ["North", "East", "South", "West"]

# Opposite / Conflicting mapping:
# In this standard 4-way single-phase controller, each direction moves exclusively.
# Therefore, when any direction is GREEN or YELLOW, all other 3 directions are RED.


class SignalScheduler:
    """
    Traffic Signal Scheduler managing signal states, safe transitions,
    and adaptive decision making across four directional approaches.
    """

    def __init__(
        self,
        green_duration: int = 8,
        yellow_duration: int = 3,
        strategy: SchedulingStrategy = SchedulingStrategy.ADAPTIVE_PRIORITY,
        max_emergency_consecutive: int = 2
    ):
        self.green_duration = max(2, int(green_duration))
        self.yellow_duration = max(1, int(yellow_duration))
        self.strategy = strategy
        self.max_emergency_consecutive = max_emergency_consecutive

        # Active state
        self.active_direction: str = "North"
        self.current_phase: SignalState = SignalState.GREEN
        self.phase_elapsed_time: int = 0
        self.total_cycle_count: int = 0
        self.priority_state = EmergencyPriorityState.NORMAL
        self.emergency_direction: Optional[str] = None
        self.emergency_vehicle_id: Optional[str] = None

        # Starvation tracking
        self.emergency_streak_count: Dict[str, int] = {d: 0 for d in DIRECTIONS}
        self.direction_last_served_step: Dict[str, int] = {d: 0 for d in DIRECTIONS}

        # Event log
        self.event_log: List[Dict[str, Any]] = []

    def set_config(
        self,
        green_duration: Optional[int] = None,
        yellow_duration: Optional[int] = None,
        strategy: Optional[str] = None,
        max_emergency_consecutive: Optional[int] = None
    ) -> None:
        """Update scheduler configuration parameters dynamically."""
        if green_duration is not None:
            self.green_duration = max(2, int(green_duration))
        if yellow_duration is not None:
            self.yellow_duration = max(1, int(yellow_duration))
        if strategy is not None:
            try:
                self.strategy = SchedulingStrategy(strategy)
            except ValueError:
                pass
        if max_emergency_consecutive is not None:
            self.max_emergency_consecutive = max(1, int(max_emergency_consecutive))

    def get_signal_states(self) -> Dict[str, str]:
        """
        Return the current visual signal color for every direction.
        Guarantees: Exactly one direction is GREEN or YELLOW; remaining are RED.
        """
        signals = {}
        for direction in DIRECTIONS:
            if direction == self.active_direction:
                signals[direction] = self.current_phase.value
            else:
                signals[direction] = SignalState.RED.value
        return signals

    def log_event(self, event_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Record a timestamped event into the sliding audit log."""
        log_entry = {
            "type": event_type,
            "message": message,
            "details": details or {},
            "cycle": self.total_cycle_count
        }
        self.event_log.append(log_entry)
        if len(self.event_log) > 100:
            self.event_log.pop(0)

    @staticmethod
    def _find_emergency_vehicles(
        queues: Dict[str, CircularQueue],
        current_sim_time: int = 0
    ) -> List[Tuple[int, int, str, str]]:
        """Return waiting emergencies ordered by arrival time, then generated ID."""
        candidates = []
        insertion_order = 0
        for direction in DIRECTIONS:
            for vehicle in queues[direction].get_fifo_items():
                vehicle_type = str(vehicle.get("type", vehicle.get("vehicle_type", ""))).casefold()
                if vehicle.get("is_emergency", False) or vehicle_type == "ambulance":
                    try:
                        arrival_time = int(vehicle.get("arrival_time", current_sim_time))
                    except (TypeError, ValueError):
                        arrival_time = current_sim_time
                    vehicle_id = str(vehicle.get("id", ""))
                    id_suffix = vehicle_id.rsplit("-", 1)[-1]
                    try:
                        sequence = int(id_suffix)
                    except ValueError:
                        sequence = insertion_order
                    candidates.append((arrival_time, sequence, direction, vehicle_id))
                insertion_order += 1
        return sorted(candidates)

    def update_emergency_priority(
        self,
        queues: Dict[str, CircularQueue],
        current_sim_time: int = 0
    ) -> None:
        """Refresh emergency state immediately after a queue change or vehicle departure."""
        candidates = self._find_emergency_vehicles(queues, current_sim_time)
        if not candidates:
            if self.priority_state in (
                EmergencyPriorityState.EMERGENCY_PREPARATION,
                EmergencyPriorityState.EMERGENCY_ACTIVE
            ):
                self.priority_state = EmergencyPriorityState.RESUME_NORMAL
                self.phase_elapsed_time = 0
                self.log_event(
                    "EMERGENCY_CLEARED",
                    "Emergency vehicle cleared; normal scheduling will resume.",
                    {"direction": self.emergency_direction, "vehicle_id": self.emergency_vehicle_id}
                )
            return

        selected = next(
            (candidate for candidate in candidates if candidate[3] == self.emergency_vehicle_id),
            None
        ) if self.priority_state == EmergencyPriorityState.EMERGENCY_ACTIVE else None
        if selected is None:
            selected = candidates[0]
        _, _, direction, vehicle_id = selected

        if (
            self.priority_state == EmergencyPriorityState.EMERGENCY_ACTIVE
            and direction == self.emergency_direction
            and vehicle_id == self.emergency_vehicle_id
        ):
            return

        previous_state = self.priority_state
        self.emergency_direction = direction
        self.emergency_vehicle_id = vehicle_id

        if (
            self.current_phase == SignalState.GREEN
            and self.active_direction == direction
            and previous_state != EmergencyPriorityState.EMERGENCY_PREPARATION
        ):
            self.priority_state = EmergencyPriorityState.EMERGENCY_ACTIVE
            if previous_state != EmergencyPriorityState.EMERGENCY_ACTIVE:
                self.phase_elapsed_time = 0
                self.log_event(
                    "EMERGENCY_ACTIVE",
                    f"Emergency vehicle {vehicle_id} has priority at {direction}.",
                    {"direction": direction, "vehicle_id": vehicle_id}
                )
            return

        if previous_state != EmergencyPriorityState.EMERGENCY_PREPARATION:
            if self.current_phase == SignalState.GREEN:
                # Departures are atomic per simulation tick; this yellow interval
                # is the available all-clear because in-junction occupancy is not modeled.
                self.current_phase = SignalState.YELLOW
                self.phase_elapsed_time = 0
            self.priority_state = EmergencyPriorityState.EMERGENCY_PREPARATION
            self.log_event(
                "EMERGENCY_PREPARATION",
                f"Emergency vehicle detected at {direction}; clearing the current approach.",
                {"direction": direction, "vehicle_id": vehicle_id}
            )

    def select_next_direction(
        self,
        queues: Dict[str, CircularQueue],
        current_sim_time: int = 0
    ) -> Tuple[str, str]:
        """
        Determine the next direction to receive green light.

        Returns:
            Tuple of (next_direction, reason_description)
        """
        # Baseline next index for round-robin
        curr_idx = DIRECTIONS.index(self.active_direction)
        rr_next = DIRECTIONS[(curr_idx + 1) % len(DIRECTIONS)]

        emergency_candidates = self._find_emergency_vehicles(queues, current_sim_time)
        if emergency_candidates:
            _, _, target_dir, vehicle_id = emergency_candidates[0]
            self.emergency_streak_count[target_dir] += 1
            for d in DIRECTIONS:
                if d != target_dir:
                    self.emergency_streak_count[d] = 0

            self.log_event(
                "EMERGENCY_PRIORITY",
                f"Emergency vehicle detected at {target_dir}; prioritizing its approach.",
                {"direction": target_dir, "vehicle_id": vehicle_id}
            )
            return target_dir, f"Emergency vehicle priority at {target_dir}"

        if self.strategy == SchedulingStrategy.ROUND_ROBIN:
            self.emergency_streak_count[rr_next] = 0
            return rr_next, "Round-robin scheduled switch"

        # Reset emergency streak counts
        for d in DIRECTIONS:
            self.emergency_streak_count[d] = 0

        # Step 2: Queue demand & wait-time balancing
        candidates = []
        for d in DIRECTIONS:
            q_len = len(queues[d])
            if q_len > 0:
                oldest_item = queues[d].peek()
                wait_time = current_sim_time - oldest_item.get("arrival_time", current_sim_time)
                # Weighted urgency score: 60% queue length, 40% waiting time
                score = (q_len * 2.5) + (wait_time * 1.0)
                candidates.append((d, score, q_len, wait_time))

        if not candidates:
            # All queues empty, proceed round-robin
            return rr_next, "Round-robin default (idle queues)"

        # Sort by urgency score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_dir, best_score, q_size, w_time = candidates[0]

        # Prevent immediate re-selection of current direction if others are also waiting
        if best_dir == self.active_direction and len(candidates) > 1:
            second_best = candidates[1][0]
            return second_best, f"Balanced demand switch to {second_best}"

        return best_dir, f"Highest traffic demand at {best_dir} (queue: {q_size})"

    def advance_time_step(
        self,
        dt: int,
        queues: Dict[str, CircularQueue],
        current_sim_time: int = 0
    ) -> Dict[str, Any]:
        """
        Advance scheduler clock by dt seconds.
        Manages GREEN -> YELLOW -> switch direction transitions safely.
        """
        self.update_emergency_priority(queues, current_sim_time)
        if self.priority_state == EmergencyPriorityState.RESUME_NORMAL:
            self.priority_state = EmergencyPriorityState.NORMAL
            self.emergency_direction = None
            self.emergency_vehicle_id = None
            self.log_event("NORMAL_RESUMED", "Normal signal scheduling resumed.", {})

        self.phase_elapsed_time += dt
        transition_occurred = False
        action_note = "Normal phase progression"

        if self.priority_state == EmergencyPriorityState.EMERGENCY_PREPARATION:
            if self.phase_elapsed_time >= self.yellow_duration:
                emergency_candidates = self._find_emergency_vehicles(queues, current_sim_time)
                if emergency_candidates:
                    _, _, direction, vehicle_id = next(
                        (candidate for candidate in emergency_candidates
                         if candidate[3] == self.emergency_vehicle_id),
                        emergency_candidates[0]
                    )
                    self.active_direction = direction
                    self.emergency_direction = direction
                    self.emergency_vehicle_id = vehicle_id
                    self.current_phase = SignalState.GREEN
                    self.phase_elapsed_time = 0
                    self.priority_state = EmergencyPriorityState.EMERGENCY_ACTIVE
                    transition_occurred = True
                    action_note = f"Emergency approach {direction} granted GREEN."
                    self.log_event(
                        "EMERGENCY_ACTIVE",
                        f"Emergency vehicle {vehicle_id} granted priority at {direction}.",
                        {"direction": direction, "vehicle_id": vehicle_id}
                    )
            return self._step_result(transition_occurred, action_note)

        if self.priority_state == EmergencyPriorityState.EMERGENCY_ACTIVE:
            return self._step_result(transition_occurred, "Emergency approach retains GREEN priority.")

        if self.current_phase == SignalState.GREEN:
            # Check if green phase has elapsed
            if self.phase_elapsed_time >= self.green_duration:
                # Transition to YELLOW
                self.current_phase = SignalState.YELLOW
                self.phase_elapsed_time = 0
                transition_occurred = True
                action_note = f"Signal at {self.active_direction} switched to YELLOW (caution phase)"
                self.log_event("PHASE_CHANGE", action_note, {
                    "direction": self.active_direction,
                    "new_phase": "YELLOW"
                })

        elif self.current_phase == SignalState.YELLOW:
            # Check if yellow transition has elapsed
            if self.phase_elapsed_time >= self.yellow_duration:
                # Select next direction safely
                prev_dir = self.active_direction
                next_dir, reason = self.select_next_direction(queues, current_sim_time)

                self.active_direction = next_dir
                self.current_phase = SignalState.GREEN
                self.phase_elapsed_time = 0
                self.total_cycle_count += 1
                self.direction_last_served_step[next_dir] = current_sim_time
                transition_occurred = True
                action_note = f"Signal switched from {prev_dir} to {next_dir} GREEN: {reason}"
                self.log_event("PHASE_CHANGE", action_note, {
                    "previous_direction": prev_dir,
                    "new_direction": next_dir,
                    "reason": reason
                })

        return self._step_result(transition_occurred, action_note)

    def _step_result(self, transition_occurred: bool, action_note: str) -> Dict[str, Any]:
        return {
            "active_direction": self.active_direction,
            "current_phase": self.current_phase.value,
            "phase_elapsed_time": self.phase_elapsed_time,
            "signals": self.get_signal_states(),
            "priority_state": self.priority_state.value,
            "emergency_direction": self.emergency_direction,
            "emergency_vehicle_id": self.emergency_vehicle_id,
            "transition_occurred": transition_occurred,
            "action_note": action_note
        }

    def reset(self) -> None:
        """Reset the scheduler to initial state."""
        self.active_direction = "North"
        self.current_phase = SignalState.GREEN
        self.phase_elapsed_time = 0
        self.total_cycle_count = 0
        self.priority_state = EmergencyPriorityState.NORMAL
        self.emergency_direction = None
        self.emergency_vehicle_id = None
        self.emergency_streak_count = {d: 0 for d in DIRECTIONS}
        self.direction_last_served_step = {d: 0 for d in DIRECTIONS}
        self.event_log.clear()
        self.log_event("SYSTEM", "Scheduler reset to initial state.", {})

    def get_state(self) -> Dict[str, Any]:
        """Export JSON-serializable scheduler state."""
        return {
            "active_direction": self.active_direction,
            "current_phase": self.current_phase.value,
            "phase_elapsed_time": self.phase_elapsed_time,
            "green_duration": self.green_duration,
            "yellow_duration": self.yellow_duration,
            "remaining_phase_time": (
                None
                if self.priority_state == EmergencyPriorityState.EMERGENCY_ACTIVE
                else max(0, self.green_duration - self.phase_elapsed_time)
                if self.current_phase == SignalState.GREEN
                else max(0, self.yellow_duration - self.phase_elapsed_time)
            ),
            "strategy": self.strategy.value,
            "total_cycles": self.total_cycle_count,
            "signals": self.get_signal_states(),
            "priority_state": self.priority_state.value,
            "emergency_direction": self.emergency_direction,
            "emergency_vehicle_id": self.emergency_vehicle_id,
            "emergency_streaks": self.emergency_streak_count,
            "recent_events": self.event_log[-15:]
        }
