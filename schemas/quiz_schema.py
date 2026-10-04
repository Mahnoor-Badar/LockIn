from pydantic import BaseModel, Field
from typing import List, Literal

# Allowed subjects catalog
CompulsorySubjects = Literal["Maths", "English", "Urdu", "Islamiat"]
JuniorSubjects = Literal["Science", "Social Studies"]
SeniorSubjects = Literal["Biology", "Physics", "Chemistry", "Pak Studies", "Computer Science"]

class Question(BaseModel):
    id: int = Field(description="Unique ID for question (1 to 2)")
    difficulty: Literal["easy", "medium", "hard"] = Field(description="Question difficulty level: easy, medium, or hard")
    question: str = Field(description="The question text in Urdish")
    options: List[str] = Field(description="Exactly 4 choices")
    correct_answer: str = Field(description="Exact string matching one option")
    concept_tag: str = Field(description="Short concept tested")

class QuizSchema(BaseModel):
    subject: str = Field(description="Subject name")
    topic: str = Field(description="Topic name")
    grade: str = Field(description="Class grade (Class 1 to 10)")
    questions: List[Question] = Field(description="Exactly 2 questions for the current adaptive difficulty stage")

class EvaluationResult(BaseModel):
    question_id: int
    is_correct: bool
    user_answer: str
    correct_answer: str
    remediation_analogy: str = ""

class OverallEvaluation(BaseModel):
    score: int
    total: int
    passed: bool
    evaluations: List[EvaluationResult]
    perceived_understanding_level: str