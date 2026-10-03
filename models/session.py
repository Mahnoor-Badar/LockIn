from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class LearningSession:
    session_id: str
    user_id: str
    student_class: str
    board: str
    subject: str
    topic: str

    current_stage: str = "learning"

    easy_score: int = 0
    medium_score: int = 0
    hard_score: int = 0
    final_score: int = 0

    mastery_level: Optional[str] = None

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
