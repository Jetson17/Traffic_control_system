"""Emergency preemption and recovery tests for the shared traffic simulation."""

import unittest

from algorithms.signal_scheduler import (
    DIRECTIONS,
    EmergencyPriorityState,
    SchedulingStrategy,
    SignalScheduler,
    SignalState,
)
from algorithms.simulation import TrafficSimulationManager


class TestEmergencyPriority(unittest.TestCase):

    def create_simulation(self, strategy=SchedulingStrategy.ROUND_ROBIN):
        simulation = TrafficSimulationManager(queue_capacity=8)
        for queue in simulation.queues.values():
            queue.clear()
        simulation.scheduler.reset()
        simulation.scheduler.set_config(
            green_duration=2,
            yellow_duration=1,
            strategy=strategy.value,
        )
        return simulation

    def test_normal_round_robin_is_unchanged_without_emergencies(self):
        simulation = self.create_simulation()

        simulation.step()
        simulation.step()
        self.assertEqual(simulation.scheduler.current_phase, SignalState.YELLOW)
        simulation.step()

        self.assertEqual(simulation.scheduler.active_direction, "East")
        self.assertEqual(simulation.scheduler.priority_state, EmergencyPriorityState.NORMAL)

    def test_ambulance_preempts_each_approach_and_only_that_approach_is_green(self):
        for direction in DIRECTIONS:
            with self.subTest(direction=direction):
                simulation = self.create_simulation()
                for other_direction in DIRECTIONS:
                    if other_direction != direction:
                        simulation.add_vehicle(other_direction, "Car")

                result = simulation.add_vehicle(direction, "Ambulance")
                self.assertTrue(result["success"])
                self.assertEqual(
                    simulation.scheduler.priority_state,
                    EmergencyPriorityState.EMERGENCY_ACTIVE
                    if direction == "North"
                    else EmergencyPriorityState.EMERGENCY_PREPARATION,
                )
                self.assertEqual(
                    simulation.get_complete_state()["emergency"]["direction"],
                    direction,
                )
                self.assertEqual(
                    sum(color != "RED" for color in simulation.scheduler.get_signal_states().values()),
                    1,
                )

                for _ in range(3):
                    if simulation.queues[direction].is_empty():
                        break
                    simulation.step()

                self.assertEqual(
                    simulation.departed_vehicles[-1]["type"],
                    "Ambulance",
                )
                for other_direction in DIRECTIONS:
                    if other_direction != direction:
                        self.assertEqual(len(simulation.queues[other_direction]), 1)

    def test_arrival_during_green_prepares_clearance_and_stops_conflicting_traffic(self):
        simulation = self.create_simulation()
        simulation.add_vehicle("North", "Car")
        simulation.add_vehicle("East", "Car")

        simulation.add_vehicle("East", "Ambulance")

        self.assertEqual(simulation.scheduler.current_phase, SignalState.YELLOW)
        self.assertEqual(simulation.scheduler.priority_state, EmergencyPriorityState.EMERGENCY_PREPARATION)
        self.assertEqual(simulation.scheduler.get_signal_states(), {
            "North": "YELLOW",
            "East": "RED",
            "South": "RED",
            "West": "RED",
        })
        simulation.step()
        self.assertEqual(simulation.scheduler.priority_state, EmergencyPriorityState.EMERGENCY_ACTIVE)
        self.assertEqual(simulation.departed_vehicles[-1]["type"], "Car")
        simulation.step()
        self.assertEqual(simulation.scheduler.priority_state, EmergencyPriorityState.RESUME_NORMAL)
        self.assertEqual(len(simulation.queues["North"]), 1)
        self.assertEqual(len(simulation.queues["East"]), 0)
        self.assertEqual(
            [vehicle["type"] for vehicle in simulation.departed_vehicles],
            ["Car", "Ambulance"],
        )

    def test_approach_fifo_is_preserved_and_ambulance_is_not_starved(self):
        simulation = self.create_simulation()
        simulation.add_vehicle("North", "Car")
        simulation.add_vehicle("North", "Ambulance")
        simulation.add_vehicle("East", "Car")

        simulation.step()
        self.assertEqual(simulation.departed_vehicles[-1]["type"], "Car")
        self.assertEqual(simulation.scheduler.priority_state, EmergencyPriorityState.EMERGENCY_ACTIVE)
        self.assertEqual(len(simulation.queues["East"]), 1)

        simulation.step()
        self.assertEqual(simulation.departed_vehicles[-1]["type"], "Ambulance")
        self.assertEqual(simulation.scheduler.priority_state, EmergencyPriorityState.RESUME_NORMAL)
        self.assertEqual(len(simulation.queues["East"]), 1)

        simulation.step()
        self.assertEqual(simulation.scheduler.priority_state, EmergencyPriorityState.NORMAL)

    def test_oldest_emergency_is_selected_before_other_waiting_emergencies(self):
        simulation = self.create_simulation()
        simulation.add_vehicle("East", "Ambulance", timestamp=5)
        east_id = simulation.queues["East"].get_fifo_items()[0]["id"]
        simulation.add_vehicle("West", "Ambulance", timestamp=4)
        west_id = simulation.queues["West"].get_fifo_items()[0]["id"]

        self.assertEqual(simulation.scheduler.emergency_direction, "West")
        simulation.step()

        self.assertEqual(simulation.departed_vehicles[-1]["id"], west_id)
        self.assertEqual(simulation.scheduler.priority_state, EmergencyPriorityState.EMERGENCY_PREPARATION)
        simulation.step()

        self.assertEqual(simulation.departed_vehicles[-1]["id"], east_id)
        self.assertEqual(simulation.scheduler.priority_state, EmergencyPriorityState.RESUME_NORMAL)

    def test_ambulance_detection_is_immediate_while_paused(self):
        simulation = self.create_simulation()
        simulation.status = "PAUSED"

        simulation.add_vehicle("South", "Ambulance")
        state = simulation.get_complete_state()

        self.assertEqual(state["priority_state"], "EMERGENCY_PREPARATION")
        self.assertEqual(state["emergency"]["direction"], "South")
        self.assertEqual(state["signals"]["North"], "YELLOW")
        self.assertEqual(state["signals"]["South"], "RED")

    def test_marked_emergency_vehicle_is_detected_even_without_ambulance_type(self):
        simulation = self.create_simulation()
        simulation.add_vehicle("West", "Car", is_emergency=True)

        self.assertEqual(simulation.scheduler.emergency_direction, "West")
        self.assertEqual(simulation.scheduler.priority_state, EmergencyPriorityState.EMERGENCY_PREPARATION)

    def test_multiple_vehicles_ahead_of_ambulance_keep_fifo_order(self):
        simulation = self.create_simulation()
        for vehicle_type in ("Car", "Bus", "Truck", "Ambulance"):
            simulation.add_vehicle("East", vehicle_type)

        for _ in range(4):
            simulation.step()

        self.assertEqual(
            [vehicle["type"] for vehicle in simulation.departed_vehicles],
            ["Car", "Bus", "Truck", "Ambulance"],
        )
        self.assertEqual(simulation.scheduler.priority_state, EmergencyPriorityState.RESUME_NORMAL)

    def test_reset_clears_emergency_state_and_waiting_emergencies(self):
        simulation = self.create_simulation()
        simulation.add_vehicle("West", "Ambulance")

        simulation.reset()
        state = simulation.get_complete_state()

        self.assertEqual(state["priority_state"], "NORMAL")
        self.assertIsNone(state["emergency"])
        self.assertEqual(state["current_phase"], "GREEN")
        self.assertEqual(state["signals"]["North"], "GREEN")
        self.assertEqual(state["statistics"]["emergency_waiting"], 0)


if __name__ == "__main__":
    unittest.main()
