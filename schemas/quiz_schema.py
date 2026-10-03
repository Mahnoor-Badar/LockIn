from pydantic import BaseModel, Field
from typing import List

class Question(BaseModel):
    id: int
    question: str = Field(description="Question text in Urdish")
    options: List[str] = Field(description="4 multiple-choice options")
    correct_answer: str = Field(description="The exact correct option string")
    concept_tag: str = Field(description="Sub-concept tested")

class QuizSchema(BaseModel):
    topic: str
    grade: str
    questions: List[Question]

class EvaluationResult(BaseModel):
    question_id: int
    is_correct: bool
    user_answer: str
    correct_answer: str
    remediation_analogy: str = Field(
        description="Simplest Urdish analogy for the missed concept, or empty if correct."
    )

class OverallEvaluation(BaseModel):
    score: int
    total: int
    passed: bool
    evaluations: List[EvaluationResult]
    perceived_understanding_level: str = Field(
        description="Estimated understanding level (Beginner/Intermediate/Advanced)"
    )