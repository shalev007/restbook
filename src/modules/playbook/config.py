from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class PlaybookStep:
    """Represents a single step in a playbook."""
    method: str
    endpoint: str
    headers: Dict[str, str] | None = None
    data: Dict[str, Any] | None = None


@dataclass
class PlaybookConfig:
    """Configuration for a playbook execution."""
    session_name: str
    steps: List[PlaybookStep]

    @classmethod
    def create_step(cls, step_dict: Dict[str, Any]) -> PlaybookStep:
        """Create a PlaybookStep from a dictionary."""
        return PlaybookStep(
            method=step_dict["method"],
            endpoint=step_dict["endpoint"],
            headers=step_dict.get("headers"),
            data=step_dict.get("data")
        ) 