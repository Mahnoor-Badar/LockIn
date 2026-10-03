from typing import Dict, List
from google import genai
from google.genai import types
from config import get_gemini_api_key
from schemas.quiz_schema import (
    QuizSchema, 
    OverallEvaluation, 
    EvaluationResult, 
    Question
)

# Shared system instruction to maintain educational boundaries and age-appropriate tone
SYSTEM_INSTRUCTION = """
You are "LockIn AI", a dedicated, friendly, and age-appropriate virtual tutor for Pakistani school students (Grades 1 to 12).

STRICT RULES:
1. DOMAIN BOUNDARY: You MUST strictly stick to educational topics, school curriculum, and student concepts.
2. BIOLOGY & SENSITIVE TOPICS RULE: For biological concepts (e.g., cell reproduction, digestive system, plant fertilization, organ systems), use strictly clean, pure academic terms. NEVER use vulgar, suggestive, or slang language.
3. PREFERRED ANALOGIES: Use dead-simple, nature-inspired analogies wherever possible — such as flowers, plants, garden ecosystems, or familiar animals (e.g., ants working as a team, roots absorbing water like a straw, bees transferring pollen).
4. OFF-TOPIC RULE: If asked about inappropriate, adult, vulgar, political, or non-educational topics, politely refuse in Urdish: "Main sirf aap ki parhai aur educational topics mein madad kar sakta hu. Chalen wapis topic par aate hain!"
5. LANGUAGE & TONE: Always use respectful, encouraging, clean, and family-friendly Urdish (Roman Urdu + English terms).
6. TARGET AUDIENCE: Write all explanations, analogies, and questions to be completely safe and appropriate for young school children.
"""

class QuizEngine:
    def __init__(self):
        api_key = get_gemini_api_key()
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def _get_safety_settings(self) -> list[types.SafetySetting]:
        """
        Configures strict API-level content moderation filters.
        """
        return [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_MEDIUM_OR_HIGH,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_MEDIUM_OR_HIGH,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_MEDIUM_OR_HIGH,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_MEDIUM_OR_HIGH,
            ),
        ]

    def generate_quiz(self, topic: str, grade: str) -> QuizSchema:
        """
        Generates a 3-question structured quiz using Gemini JSON Schema mode with safety filters.
        """
        prompt = f"""
        Create a 3-question multiple-choice quiz in Urdish (Roman Urdu + English terms) 
        testing core concepts of '{topic}' for Grade '{grade}'.

        Ensure:
        - 4 options per question.
        - Exactly 1 correct option string matching one of the options.
        - A concise concept_tag identifying what is tested.
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
                    temperature=0.2
                )
            )
            return QuizSchema.model_validate_json(response.text)
        except Exception as e:
            raise ValueError(f"Quiz generation failed due to safety filters or parsing error: {e}")

    def evaluate_quiz(self, quiz: QuizSchema, user_answers: Dict[int, str]) -> OverallEvaluation:
        """
        Evaluates student responses, cross-verifies correct answers,
        and generates simplest nature-based Urdish analogies strictly for missed concepts.
        """
        evaluations: List[EvaluationResult] = []
        score = 0
        total = len(quiz.questions)

        for q in quiz.questions:
            user_ans = user_answers.get(q.id, "").strip()
            is_correct = (user_ans.lower() == q.correct_answer.strip().lower())

            remediation = ""
            if is_correct:
                score += 1
            else:
                # Generate a dead-simple, targeted nature/animal/flower Urdish analogy for missed answer
                remediation = self._generate_targeted_analogy(
                    topic=quiz.topic,
                    question=q.question,
                    concept=q.concept_tag,
                    user_answer=user_ans,
                    correct_answer=q.correct_answer
                )

            evaluations.append(
                EvaluationResult(
                    question_id=q.id,
                    is_correct=is_correct,
                    user_answer=user_ans,
                    correct_answer=q.correct_answer,
                    remediation_analogy=remediation
                )
            )

        passed = (score == total)
        understanding_level = "Advanced" if score == total else ("Intermediate" if score >= 1 else "Beginner")

        return OverallEvaluation(
            score=score,
            total=total,
            passed=passed,
            evaluations=evaluations,
            perceived_understanding_level=understanding_level
        )

    def _generate_targeted_analogy(
        self, topic: str, question: str, concept: str, user_answer: str, correct_answer: str
    ) -> str:
        """
        Internal LLM call: Generates nature/flower/animal-based Urdish analogies for wrong answers.
        """
        prompt = f"""
        A student missed a question on '{topic}' ({concept}).
        
        - Question: {question}
        - Student's Answer: {user_answer}
        - Correct Answer: {correct_answer}

        Tasks:
        1. Explain WHY the correct answer is right using a dead-simple, gentle analogy from nature, flowers, gardening, or animal examples (e.g., bees, ants, plants, birds) in clean Urdish (Roman Urdu).
        2. Keep it under 3-4 sentences.
        3. Do NOT lecture or sound harsh; keep it completely respectful, safe, encouraging, and intuitive for a school child.
        """

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    safety_settings=self._get_safety_settings(),
                    temperature=0.3
                )
            )
            return response.text.strip()
        except Exception:
            return "Sahi jawab yeh tha kyunke yeh concept basic rule par chalta hai. Chalen aglay sawal par try karte hain!"