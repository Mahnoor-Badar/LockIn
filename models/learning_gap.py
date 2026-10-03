from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class LearningGap:
    gap_id: str
    session_id: str
    concept: str
    misconception: str
    difficulty: str
    attempt_count: int = 1
    resolved: bool = False
    timestamp: Optional[datetime] = field(default_factory=datetime.now)
