"""
Unit Tests for CircularQueue Implementation.
Covers enqueue, dequeue, peek, FIFO order, wrap-around, overflow, underflow, and JSON state export.
"""

import unittest
from algorithms.circular_queue import CircularQueue, QueueOverflowError, QueueUnderflowError


class TestCircularQueue(unittest.TestCase):

    def setUp(self):
        self.capacity = 5
        self.queue = CircularQueue(capacity=self.capacity)

    def test_initial_state(self):
        self.assertTrue(self.queue.is_empty())
        self.assertFalse(self.queue.is_full())
        self.assertEqual(len(self.queue), 0)
        self.assertEqual(self.queue.front, -1)
        self.assertEqual(self.queue.rear, -1)
        self.assertEqual(self.queue.get_fifo_items(), [])

    def test_enqueue_and_fifo_order(self):
        items = ["V1", "V2", "V3"]
        for item in items:
            self.assertTrue(self.queue.enqueue(item))

        self.assertEqual(len(self.queue), 3)
        self.assertEqual(self.queue.front, 0)
        self.assertEqual(self.queue.rear, 2)
        self.assertEqual(self.queue.peek(), "V1")
        self.assertEqual(self.queue.get_fifo_items(), items)

    def test_dequeue(self):
        self.queue.enqueue("A")
        self.queue.enqueue("B")
        self.queue.enqueue("C")

        self.assertEqual(self.queue.dequeue(), "A")
        self.assertEqual(len(self.queue), 2)
        self.assertEqual(self.queue.front, 1)
        self.assertEqual(self.queue.rear, 2)
        self.assertEqual(self.queue.peek(), "B")
        self.assertEqual(self.queue.get_fifo_items(), ["B", "C"])

    def test_full_queue_and_overflow(self):
        for i in range(self.capacity):
            self.queue.enqueue(f"CAR_{i}")

        self.assertTrue(self.queue.is_full())
        self.assertEqual(len(self.queue), self.capacity)

        with self.assertRaises(QueueOverflowError):
            self.queue.enqueue("EXTRA_CAR")

    def test_empty_queue_underflow(self):
        with self.assertRaises(QueueUnderflowError):
            self.queue.dequeue()

        with self.assertRaises(QueueUnderflowError):
            self.queue.peek()

    def test_wrap_around_modulo(self):
        # Fill queue completely
        for i in range(self.capacity):
            self.queue.enqueue(f"ITEM_{i}")

        # Dequeue 2 items (indices 0 and 1 are now vacant)
        self.assertEqual(self.queue.dequeue(), "ITEM_0")
        self.assertEqual(self.queue.dequeue(), "ITEM_1")
        self.assertEqual(self.queue.front, 2)
        self.assertEqual(self.queue.rear, 4)
        self.assertEqual(len(self.queue), 3)

        # Enqueue new items: rear must wrap around to 0 then 1
        self.queue.enqueue("WRAP_A")
        self.assertEqual(self.queue.rear, 0)

        self.queue.enqueue("WRAP_B")
        self.assertEqual(self.queue.rear, 1)

        self.assertTrue(self.queue.is_full())
        self.assertEqual(
            self.queue.get_fifo_items(),
            ["ITEM_2", "ITEM_3", "ITEM_4", "WRAP_A", "WRAP_B"]
        )

    def test_drain_to_empty_resets_pointers(self):
        self.queue.enqueue("X")
        self.assertEqual(self.queue.dequeue(), "X")
        self.assertTrue(self.queue.is_empty())
        self.assertEqual(self.queue.front, -1)
        self.assertEqual(self.queue.rear, -1)

    def test_get_state_structure(self):
        self.queue.enqueue({"id": "V100", "type": "Car"})
        state = self.queue.get_state()
        self.assertEqual(state["capacity"], 5)
        self.assertEqual(state["size"], 1)
        self.assertEqual(state["front"], 0)
        self.assertEqual(state["rear"], 0)
        self.assertFalse(state["is_empty"])
        self.assertFalse(state["is_full"])
        self.assertEqual(len(state["slots"]), 5)
        self.assertTrue(state["slots"][0]["is_occupied"])
        self.assertTrue(state["slots"][0]["is_front"])
        self.assertTrue(state["slots"][0]["is_rear"])
        self.assertFalse(state["slots"][1]["is_occupied"])


if __name__ == "__main__":
    unittest.main()
