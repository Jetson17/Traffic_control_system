"""
Circular Queue Implementation for Traffic Signal Control System.

Module: algorithms.circular_queue
Time Complexities:
    - enqueue: O(1)
    - dequeue: O(1)
    - peek:    O(1)
    - is_empty: O(1)
    - is_full:  O(1)
Space Complexity: O(capacity)
"""

from typing import Any, List, Optional, Dict


class QueueOverflowError(Exception):
    """Raised when an enqueue operation is attempted on a full circular queue."""
    pass


class QueueUnderflowError(Exception):
    """Raised when a dequeue or peek operation is attempted on an empty circular queue."""
    pass


class CircularQueue:
    """
    Circular Queue implemented with a fixed-size array and front/rear index pointers.
    Utilizes modulo arithmetic to reuse deallocated slots without shifting elements.
    """

    def __init__(self, capacity: int = 8):
        """
        Initialize the circular queue with a fixed capacity.

        :param capacity: Maximum number of elements the queue can hold (must be >= 1).
        """
        if capacity <= 0:
            raise ValueError("Capacity must be a positive integer greater than 0.")

        self.capacity: int = int(capacity)
        self.array: List[Optional[Any]] = [None] * self.capacity
        self.front: int = -1
        self.rear: int = -1
        self.size: int = 0

    def is_empty(self) -> bool:
        """
        Check if the circular queue contains zero elements.
        Time Complexity: O(1)
        """
        return self.size == 0

    def is_full(self) -> bool:
        """
        Check if the circular queue has reached its maximum allocated capacity.
        Time Complexity: O(1)
        """
        return self.size == self.capacity

    def enqueue(self, item: Any) -> bool:
        """
        Insert an element at the rear of the circular queue using modulo arithmetic.

        :param item: The vehicle or item to enqueue.
        :raises QueueOverflowError: If the queue is already full.
        :return: True on successful insertion.
        Time Complexity: O(1)
        """
        if self.is_full():
            raise QueueOverflowError(
                f"Queue Overflow: Cannot enqueue item. Capacity of {self.capacity} reached."
            )

        if self.is_empty():
            self.front = 0
            self.rear = 0
        else:
            self.rear = (self.rear + 1) % self.capacity

        self.array[self.rear] = item
        self.size += 1
        return True

    def dequeue(self) -> Any:
        """
        Remove and return the element at the front of the circular queue.

        :raises QueueUnderflowError: If the queue is empty.
        :return: The dequeued element.
        Time Complexity: O(1)
        """
        if self.is_empty():
            raise QueueUnderflowError(
                "Queue Underflow: Cannot dequeue from an empty circular queue."
            )

        item = self.array[self.front]
        self.array[self.front] = None  # Clear reference for clean slot representation

        if self.front == self.rear:
            # Queue becomes empty after removing the only element
            self.front = -1
            self.rear = -1
        else:
            self.front = (self.front + 1) % self.capacity

        self.size -= 1
        return item

    def peek(self) -> Any:
        """
        Return the element at the front of the circular queue without removing it.

        :raises QueueUnderflowError: If the queue is empty.
        :return: The front element.
        Time Complexity: O(1)
        """
        if self.is_empty():
            raise QueueUnderflowError("Queue is empty. Cannot peek front element.")
        return self.array[self.front]

    def get_fifo_items(self) -> List[Any]:
        """
        Return all active elements in true FIFO order from front to rear.
        Time Complexity: O(N) where N is current size <= capacity.
        """
        if self.is_empty():
            return []

        items = []
        curr = self.front
        for _ in range(self.size):
            items.append(self.array[curr])
            curr = (curr + 1) % self.capacity
        return items

    def clear(self) -> None:
        """Reset the circular queue to an initial empty state."""
        self.array = [None] * self.capacity
        self.front = -1
        self.rear = -1
        self.size = 0

    def get_state(self) -> Dict[str, Any]:
        """
        Export complete, JSON-serializable internal state for live UI visualization,
        showing exact slot index, pointers, empty/occupied states, and FIFO order.
        """
        slots = []
        for i in range(self.capacity):
            slot_item = self.array[i]
            slots.append({
                "index": i,
                "is_occupied": slot_item is not None,
                "is_front": (i == self.front and not self.is_empty()),
                "is_rear": (i == self.rear and not self.is_empty()),
                "item": slot_item
            })

        return {
            "capacity": self.capacity,
            "size": self.size,
            "front": self.front,
            "rear": self.rear,
            "is_empty": self.is_empty(),
            "is_full": self.is_full(),
            "slots": slots,
            "fifo_items": self.get_fifo_items()
        }

    def __len__(self) -> int:
        return self.size

    def __repr__(self) -> str:
        return f"CircularQueue(capacity={self.capacity}, size={self.size}, front={self.front}, rear={self.rear})"
