from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class QuizAttempt:
    attempt_id: str
    session_id: str
    question: str
    difficulty: str
    concept: str
    selected_answer: str
    correct_answer: str
    is_correct: bool

    timestamp: Optional[datetime] = None
