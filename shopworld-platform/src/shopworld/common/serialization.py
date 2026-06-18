"""State serialization for environment reset/save/load."""

import pickle
from dataclasses import dataclass
from typing import Any, Dict
from datetime import datetime


@dataclass
class StateSnapshot:
    """Immutable snapshot of world state at a point in time."""
    
    episode_id: str
    step_number: int
    timestamp: datetime
    database_state: Dict[str, Any]  # Serialized DB records
    hidden_state: Dict[str, Any]    # Latent actor variables
    clock_state: Dict[str, Any]   # SimulatedClock state
    metadata: Dict[str, Any]       # Episode metadata
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "step_number": self.step_number,
            "timestamp": self.timestamp.isoformat(),
            "database_state": self.database_state,
            "hidden_state": self.hidden_state,
            "clock_state": self.clock_state,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateSnapshot":
        return cls(
            episode_id=data["episode_id"],
            step_number=data["step_number"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            database_state=data["database_state"],
            hidden_state=data["hidden_state"],
            clock_state=data["clock_state"],
            metadata=data["metadata"],
        )


def serialize_state(obj: Any) -> bytes:
    """Serialize any state object to bytes."""
    return pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)


def deserialize_state(data: bytes) -> Any:
    """Deserialize bytes to state object."""
    return pickle.loads(data)


def state_diff(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """Compute differences between two state dictionaries.
    
    Returns a dict with keys: added, removed, modified, unchanged.
    """
    diff = {
        "added": {},
        "removed": {},
        "modified": {},
        "unchanged": {},
    }
    
    all_keys = set(before.keys()) | set(after.keys())
    
    for key in all_keys:
        if key not in before:
            diff["added"][key] = after[key]
        elif key not in after:
            diff["removed"][key] = before[key]
        elif before[key] != after[key]:
            diff["modified"][key] = {
                "before": before[key],
                "after": after[key],
            }
        else:
            diff["unchanged"][key] = before[key]
    
    return diff
