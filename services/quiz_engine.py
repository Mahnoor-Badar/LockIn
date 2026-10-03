
from typing import Dict, List

from google import genai
from google.genai import types

from config import get_gemini_api_key
from schemas.quiz_schema import (
    QuizSchema,
    OverallEvaluation,
    EvaluationResult,
)


SYSTEM_INSTRUCTION = """
You are "LockIn AI", a friendly and age-appropriate educational tutor
for Pakistani school students in Grades 1 to 10.

STRICT RULES:
1. Stay strictly within educational topics and school concepts.
2. Use clean, age-appropriate academic language.
3. Use simple everyday examples when helpful.
4. For biological concepts, use clean academic terminology only.
5. Do not answer inappropriate, adult, vulgar, political, or non-educational questions.
6. Use respectful, encouraging, family-friendly Urdish
   (Roman Urdu + English technical terms).
7. Match every question to the student's selected grade and subject.
"""


class QuizEngine:

    def __init__(self):
        api_key = get_gemini_api_key()
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-3.8-flash"

    def _get_safety_settings(self) -> list[types.SafetySetting]:
        return [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
        ]

    def generate_quiz(
        self,
        topic: str,
        grade: str,
        subject: str = "General",
        difficulty: str = "easy",
    ) -> QuizSchema:
        """
        Generate exactly 2 MCQs for the requested adaptive stage.

        AdaptiveEngine controls progression.
        Gemini only generates the questions.
        """

        prompt = f"""
Create EXACTLY 2 multiple-choice questions in Urdish
(Roman Urdu + English technical terms).

Student information:
- Grade: {grade}
- Subject: {subject}
- Topic: {topic}
- Difficulty: {difficulty}

Difficulty rules:
- easy = basic understanding and recall
- medium = application, comparison, or simple reasoning
- hard = deeper reasoning or challenging application

Requirements:
- Exactly 2 questions.
- Exactly 4 options per question.
- Exactly 1 correct answer.
- correct_answer must exactly match one option.
- Give each question a concise concept_tag.
- Each question's difficulty must be exactly "{difficulty}".
- Questions must be appropriate for the selected grade.
- Questions must stay within the selected subject.
- The returned quiz subject field must be exactly "{subject}".
- The returned quiz topic field must be exactly "{topic}".
- The returned quiz grade field must be exactly "{grade}".
- Return only the structured quiz data.
"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    safety_settings=self._get_safety_settings(),
                    response_mime_type="application/json",
                    response_schema=QuizSchema,
                    temperature=0.2,
                ),
            )

            quiz = QuizSchema.model_validate_json(response.text)

            if len(quiz.questions) != 2:
                raise ValueError(
                    f"Expected exactly 2 questions, "
                    f"received {len(quiz.questions)}."
                )

            return quiz

        except Exception as e:
            raise ValueError(
                f"Quiz generation failed due to safety filters "
                f"or parsing error: {e}"
            )

    def evaluate_quiz(
        self,
        quiz: QuizSchema,
        user_answers: Dict[int, str],
    ) -> OverallEvaluation:
        """
        Evaluate the student's answers for the current stage.

        Stage progression is handled separately by AdaptiveEngine.
        """

        evaluations: List[EvaluationResult] = []
        score = 0
        total = len(quiz.questions)

        for q in quiz.questions:

            user_ans = user_answers.get(q.id, "").strip()

            is_correct = (
                user_ans.lower()
                == q.correct_answer.strip().lower()
            )

            remediation = ""

            if is_correct:
                score += 1
            else:
                remediation = self._generate_targeted_analogy(
                    topic=quiz.topic,
                    question=q.question,
                    concept=q.concept_tag,
                    user_answer=user_ans,
                    correct_answer=q.correct_answer,
                )

            evaluations.append(
                EvaluationResult(
                    question_id=q.id,
                    is_correct=is_correct,
                    user_answer=user_ans,
                    correct_answer=q.correct_answer,
                    remediation_analogy=remediation,
                )
            )

        if score == total:
            understanding_level = "Advanced"
        elif score >= 1:
            understanding_level = "Intermediate"
        else:
            understanding_level = "Beginner"

        return OverallEvaluation(
            score=score,
            total=total,
            passed=(score == total),
            evaluations=evaluations,
            perceived_understanding_level=understanding_level,
        )

    def _generate_targeted_analogy(
        self,
        topic: str,
        question: str,
        concept: str,
        user_answer: str,
        correct_answer: str,
    ) -> str:

        prompt = f"""
A student missed a question about '{topic}'.

Concept: {concept}
Question: {question}
Student answer: {user_answer}
Correct answer: {correct_answer}

Explain why the correct answer is right.

Rules:
- Use simple Urdish.
- Use a very simple everyday, plant, animal, or nature analogy.
- Keep it under 3-4 sentences.
- Be encouraging.
- Keep it appropriate for a school child.
"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    safety_settings=self._get_safety_settings(),
                    temperature=0.3,
                ),
            )

            return response.text.strip()

        except Exception:
            return (
                "Sahi jawab yeh tha kyunke yeh concept ek basic rule "
                "par depend karta hai. Chalen isay dobara samajh kar "
                "phir try karte hain!"
            )


print("QuizEngine updated successfully. ✅")
