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

        if self.strategy == SchedulingStrategy.ROUND_ROBIN:
            self.emergency_streak_count[rr_next] = 0
            return rr_next, "Round-robin scheduled switch"

        # Adaptive Priority Mode
        # Step 1: Scan for waiting emergency vehicles
        emergency_candidates = []
        for direction in DIRECTIONS:
            q = queues[direction]
            if not q.is_empty():
                fifo_items = q.get_fifo_items()
                for item in fifo_items:
                    if item.get("is_emergency", False):
                        priority = item.get("priority", 3)
                        arrival = item.get("arrival_time", current_sim_time)
                        emergency_candidates.append((direction, priority, arrival))
                        break

        if emergency_candidates:
            # Sort by priority (ascending: 1 = Ambulance, 2 = Fire Engine, 3 = Police) then arrival
            emergency_candidates.sort(key=lambda x: (x[1], x[2]))
            target_dir = emergency_candidates[0][0]

            # Starvation prevention check:
            # If target direction has already received consecutive emergency extensions
            # and another non-empty direction has waited too long, grant service to avoid total starvation.
            if self.emergency_streak_count[target_dir] >= self.max_emergency_consecutive:
                # Find most starved waiting non-emergency queue
                starved_dir = None
                max_starve_time = -1
                for d in DIRECTIONS:
                    if d != target_dir and not queues[d].is_empty():
                        oldest_veh = queues[d].peek()
                        wait = current_sim_time - oldest_veh.get("arrival_time", current_sim_time)
                        if wait > max_starve_time:
                            max_starve_time = wait
                            starved_dir = d

                if starved_dir and max_starve_time > 15:
                    self.emergency_streak_count[target_dir] = 0
                    self.log_event(
                        "STARVATION_PREVENTION",
                        f"Normal traffic at {starved_dir} given green to prevent indefinite starvation after emergency priority.",
                        {"starved_direction": starved_dir, "wait_time": max_starve_time}
                    )
                    return starved_dir, f"Starvation prevention override for {starved_dir}"

            self.emergency_streak_count[target_dir] += 1
            # Reset other directions streak
            for d in DIRECTIONS:
                if d != target_dir:
                    self.emergency_streak_count[d] = 0

            self.log_event(
                "EMERGENCY_PRIORITY",
                f"Emergency vehicle detected at {target_dir}! Prioritizing green phase.",
                {"direction": target_dir, "streak": self.emergency_streak_count[target_dir]}
            )
            return target_dir, f"Emergency vehicle priority at {target_dir}"

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
        self.phase_elapsed_time += dt
        transition_occurred = False
        action_note = "Normal phase progression"

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

        return {
            "active_direction": self.active_direction,
            "current_phase": self.current_phase.value,
            "phase_elapsed_time": self.phase_elapsed_time,
            "signals": self.get_signal_states(),
            "transition_occurred": transition_occurred,
            "action_note": action_note
        }

    def reset(self) -> None:
        """Reset the scheduler to initial state."""
        self.active_direction = "North"
        self.current_phase = SignalState.GREEN
        self.phase_elapsed_time = 0
        self.total_cycle_count = 0
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
                (self.green_duration - self.phase_elapsed_time)
                if self.current_phase == SignalState.GREEN
                else (self.yellow_duration - self.phase_elapsed_time)
            ),
            "strategy": self.strategy.value,
            "total_cycles": self.total_cycle_count,
            "signals": self.get_signal_states(),
            "emergency_streaks": self.emergency_streak_count,
            "recent_events": self.event_log[-15:]
        }
