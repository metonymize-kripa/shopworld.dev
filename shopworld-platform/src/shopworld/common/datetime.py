"""Simulated clock for deterministic time advancement."""

from datetime import datetime, timedelta
from typing import Optional


class SimulatedClock:
    """Deterministic clock that advances in discrete steps.
    
    Unlike real-time, the simulated clock only advances when the
    environment steps forward, enabling reproducible episode execution.
    """
    
    def __init__(self, start_time: Optional[datetime] = None, step_size_hours: int = 1):
        self.start_time = start_time or datetime(2024, 1, 1, 0, 0, 0)
        self.current_time = self.start_time
        self.step_size = timedelta(hours=step_size_hours)
        self.step_count = 0
    
    def step(self) -> datetime:
        """Advance the clock by one step."""
        self.current_time += self.step_size
        self.step_count += 1
        return self.current_time
    
    def advance(self, hours: int) -> datetime:
        """Advance the clock by specified hours."""
        self.current_time += timedelta(hours=hours)
        self.step_count += 1
        return self.current_time
    
    def now(self) -> datetime:
        """Get current simulated time."""
        return self.current_time
    
    def reset(self) -> None:
        """Reset clock to start time."""
        self.current_time = self.start_time
        self.step_count = 0
    
    def elapsed_hours(self) -> int:
        """Get total elapsed hours since start."""
        return int((self.current_time - self.start_time).total_seconds() / 3600)
    
    def is_business_hours(self) -> bool:
        """Check if current time is during business hours (9 AM - 6 PM, weekdays)."""
        if self.current_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        hour = self.current_time.hour
        return 9 <= hour < 18
    
    def __repr__(self) -> str:
        return f"SimulatedClock({self.current_time.isoformat()}, step={self.step_count})"
