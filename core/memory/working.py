"""
Tier 1: Working Memory Engine
Fast in-memory circular buffer and active context scratchpad for current conversation state.
"""

from typing import List, Dict, Any, Optional
from collections import deque
from datetime import datetime, timezone


class WorkingMemory:
    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self._history: deque = deque(maxlen=max_turns)
        self._slots: Dict[str, Any] = {
            "current_project": None,
            "active_file": None,
            "current_topic": None,
            "last_action": None,
            "active_task_id": None
        }
        self._scratchpad: Dict[str, Any] = {}

    def add_turn(self, role: str, content: str, modality: str = "text"):
        """Appends a conversation turn to the working memory sliding window."""
        self._history.append({
            "role": role,
            "content": content,
            "modality": modality,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def get_recent_turns(self, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Returns the most recent conversation turns formatted for LLM context."""
        turns = list(self._history)
        if count:
            return turns[-count:]
        return turns

    def set_slot(self, key: str, value: Any):
        """Sets an active context slot (e.g. current_project = 'Autonomous Warehouse AI')."""
        self._slots[key] = value

    def get_slot(self, key: str, default: Any = None) -> Any:
        """Retrieves an active context slot."""
        return self._slots.get(key, default)

    def get_all_slots(self) -> Dict[str, Any]:
        """Returns all populated active slots."""
        return {k: v for k, v in self._slots.items() if v is not None}

    def write_scratchpad(self, key: str, value: Any):
        """Writes temporary state variable during task execution."""
        self._scratchpad[key] = value

    def read_scratchpad(self, key: str, default: Any = None) -> Any:
        return self._scratchpad.get(key, default)

    def clear(self):
        """Clears working memory for a fresh conversation session."""
        self._history.clear()
        self._scratchpad.clear()
        for k in self._slots:
            self._slots[k] = None


# Global singleton instance
working_memory = WorkingMemory()
