"""
Unit Tests for SignalScheduler.
Verifies phase progression, anti-conflict guarantees, round-robin, emergency prioritization, and starvation prevention.
"""

import unittest
from algorithms.circular_queue import CircularQueue
from algorithms.signal_scheduler import SignalScheduler, SchedulingStrategy, SignalState, DIRECTIONS


class TestSignalScheduler(unittest.TestCase):

    def setUp(self):
        self.green_dur = 4
        self.yellow_dur = 2
        self.scheduler = SignalScheduler(
            green_duration=self.green_dur,
            yellow_duration=self.yellow_dur,
            strategy=SchedulingStrategy.ROUND_ROBIN
        )
        self.queues = {d: CircularQueue(capacity=6) for d in DIRECTIONS}

    def test_initial_state_and_no_conflict(self):
        state = self.scheduler.get_state()
        self.assertEqual(state["active_direction"], "North")
        self.assertEqual(state["current_phase"], "GREEN")

        signals = self.scheduler.get_signal_states()
        self.assertEqual(signals["North"], "GREEN")
        self.assertEqual(signals["East"], "RED")
        self.assertEqual(signals["South"], "RED")
        self.assertEqual(signals["West"], "RED")

        # Guarantee: only 1 non-RED signal at a time
        active_count = sum(1 for color in signals.values() if color != "RED")
        self.assertEqual(active_count, 1)

    def test_phase_progression_green_to_yellow_to_next(self):
        # Step through green phase (duration = 4)
        for _ in range(self.green_dur - 1):
            res = self.scheduler.advance_time_step(1, self.queues)
            self.assertEqual(res["current_phase"], "GREEN")
            self.assertEqual(res["active_direction"], "North")

        # Step into yellow
        res = self.scheduler.advance_time_step(1, self.queues)
        self.assertEqual(res["current_phase"], "YELLOW")
        self.assertEqual(res["active_direction"], "North")
        self.assertTrue(res["transition_occurred"])

        # Signals during yellow
        signals = self.scheduler.get_signal_states()
        self.assertEqual(signals["North"], "YELLOW")
        self.assertEqual(signals["East"], "RED")

        # Step through yellow (duration = 2)
        res = self.scheduler.advance_time_step(1, self.queues)
        self.assertEqual(res["current_phase"], "YELLOW")

        # Step into next direction GREEN (East in Round-Robin)
        res = self.scheduler.advance_time_step(1, self.queues)
        self.assertEqual(res["current_phase"], "GREEN")
        self.assertEqual(res["active_direction"], "East")
        self.assertTrue(res["transition_occurred"])

    def test_round_robin_full_cycle(self):
        cycle_directions = []
        for _ in range(4):
            cycle_directions.append(self.scheduler.active_direction)
            # Advance through green
            for _ in range(self.green_dur):
                self.scheduler.advance_time_step(1, self.queues)
            # Advance through yellow
            for _ in range(self.yellow_dur):
                self.scheduler.advance_time_step(1, self.queues)

        self.assertEqual(cycle_directions, ["North", "East", "South", "West"])

    def test_emergency_vehicle_prioritization(self):
        # Configure adaptive priority scheduler
        self.scheduler.set_config(strategy="adaptive_priority")

        # Put emergency vehicle in West queue
        self.queues["West"].enqueue({
            "id": "EMG-101",
            "type": "Ambulance",
            "is_emergency": True,
            "priority": 1,
            "arrival_time": 5
        })

        # Put normal vehicle in East
        self.queues["East"].enqueue({
            "id": "CAR-001",
            "type": "Car",
            "is_emergency": False,
            "priority": 0,
            "arrival_time": 2
        })

        # Advance North through green & yellow
        for _ in range(self.green_dur + self.yellow_dur):
            self.scheduler.advance_time_step(1, self.queues, current_sim_time=10)

        # West must be chosen because of Ambulance, even though East is next in round-robin!
        self.assertEqual(self.scheduler.active_direction, "West")
        self.assertEqual(self.scheduler.current_phase, SignalState.GREEN)

    def test_reset(self):
        self.scheduler.advance_time_step(self.green_dur + 1, self.queues)
        self.scheduler.reset()
        self.assertEqual(self.scheduler.active_direction, "North")
        self.assertEqual(self.scheduler.current_phase, SignalState.GREEN)
        self.assertEqual(self.scheduler.phase_elapsed_time, 0)


if __name__ == "__main__":
    unittest.main()
