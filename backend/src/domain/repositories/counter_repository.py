from abc import ABC, abstractmethod
from src.domain.entities.counter import Counter

class CounterRepository(ABC):
    @abstractmethod
    def get_next_sequence_value(self, counter_id: str) -> int:
        """Atomically read, increment, and return the next integer value for a given sequence counter."""
        pass
    
    @abstractmethod
    def initialize_counter(self, counter_id: str, prefix: str, padding: int, initial_value: int = 0) -> Counter:
        """Initialize a sequence counter document if it doesn't already exist."""
        pass
