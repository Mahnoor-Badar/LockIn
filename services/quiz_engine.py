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
You are "LockIn AI", a dedicated, friendly, and age-appropriate virtual tutor for Pakistani school students (Classes 1 to 10).

STRICT RULES:
1. DOMAIN BOUNDARY: You MUST strictly stick to educational topics, school curriculum, and student concepts.
2. BIOLOGY & SENSITIVE TOPICS RULE: For biological concepts (e.g., cell reproduction, digestive system, plant fertilization, organ systems), use strictly clean, pure academic terms. NEVER use vulgar, suggestive, or slang language.
3. PREFERRED ANALOGIES: Use dead-simple, nature-inspired analogies wherever possible such as flowers, plants, garden ecosystems, or familiar animals (e.g., ants working as a team, roots absorbing water like a straw, bees transferring pollen).
4. OFF-TOPIC RULE: If asked about inappropriate, adult, vulgar, political, or non-educational topics, politely refuse in Urdish: "Main sirf aap ki parhai aur educational topics mein madad kar sakta hu. Chalen wapis topic par aate hain!"
5. LANGUAGE & TONE: Always use respectful, encouraging, clean, and family-friendly Urdish (Roman Urdu + English terms).
6. TARGET AUDIENCE: Write all explanations, analogies, and questions to be completely safe and appropriate for young school children.
"""

# Dynamic subject mapping according to Pakistani curriculum standards
SUBJECT_MAP = {
    "compulsory": ["Maths", "English", "Urdu", "Islamiat"],
    "junior_only": ["Science", "Social Studies"],                 # Class 1 to 8
    "senior_only": ["Biology", "Physics", "Chemistry", "Pak Studies", "Computer Science"] # Class 9 & 10
}

class QuizEngine:
    def __init__(self):
        api_key = get_gemini_api_key()
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-3.8-flash"

    def get_allowed_subjects(self, grade_num: int) -> List[str]:
        """
        Returns list of valid subjects based on student's class grade (1-10).
        """
        allowed = list(SUBJECT_MAP["compulsory"])
        
        if 1 <= grade_num <= 8:
            allowed.extend(SUBJECT_MAP["junior_only"])
        elif grade_num in [9, 10]:
            allowed.extend(SUBJECT_MAP["senior_only"])
            
        return allowed

    def _get_safety_settings(self) -> list[types.SafetySetting]:
        """
        Configures strict API-level content moderation filters.
        """
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
        subject: str,
        topic: str,
        grade: str,
        difficulty: str,
    ) -> QuizSchema:
        """
        Generate exactly 2 MCQs for one adaptive difficulty stage.
        """

        allowed_difficulties = {
            "easy",
            "medium",
            "hard",
        }

        if difficulty not in allowed_difficulties:
            raise ValueError(
                f"Invalid difficulty '{difficulty}'. "
                "Expected easy, medium, or hard."
            )

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
- Exactly 1 correct answer per question.
- correct_answer must exactly match one option.
- Give each question a concise concept_tag.
- Each question's difficulty must be exactly "{difficulty}".
- Questions must be appropriate for the selected grade.
- Questions must stay within the selected subject and topic.
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

            quiz = QuizSchema.model_validate_json(
                response.text
            )

            if len(quiz.questions) != 2:
                raise ValueError(
                    f"Expected exactly 2 questions, got "
                    f"{len(quiz.questions)}."
                )

            for question in quiz.questions:
                if question.difficulty != difficulty:
                    raise ValueError(
                        "Gemini returned a question with "
                        "the wrong difficulty."
                    )

            return quiz

        except Exception as e:
            raise ValueError(
                f"Quiz generation failed: {e}"
            ) from e

    def evaluate_quiz(self, quiz: QuizSchema, user_answers: Dict[int, str]) -> OverallEvaluation:
        """
        Evaluates student responses across all questions, cross-verifies correct answers,
        tracks easy-level failures, and generates nature-based Urdish analogies for missed questions.
        """
        evaluations: List[EvaluationResult] = []
        score = 0
        total = len(quiz.questions)
        
        easy_failed = False
        failed_easy_concept = ""

        for q in quiz.questions:
            user_ans = user_answers.get(q.id, "").strip()
            is_correct = (user_ans.lower() == q.correct_answer.strip().lower())

            remediation = ""
            if is_correct:
                score += 1
            else:
                if q.difficulty == 'easy':
                    easy_failed = True
                    if not failed_easy_concept:
                        failed_easy_concept = q.concept_tag

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
        
        if score == total:
            understanding_level = "Advanced (Fully Mastered)"
        elif not easy_failed:
            understanding_level = "Intermediate"
        else:
            understanding_level = "Needs Re-explanation"

        return OverallEvaluation(
            score=score,
            total=total,
            passed=passed,
            evaluations=evaluations,
            perceived_understanding_level=understanding_level
        )

    def reexplain_with_new_analogy(self, subject: str, topic: str, grade: str, missed_concept: str = "") -> str:
        """
        Triggered when student fails Easy questions.
        Generates a fresh, alternative nature/animal analogy to re-explain the concept from scratch.
        """
        prompt = f"""
        A {grade} student failed the basic/easy questions in Subject '{subject}', Topic '{topic}'.
        Specific area of confusion: {missed_concept if missed_concept else topic}.

        Tasks:
     1. DOMAIN BOUNDARY: You MUST strictly stick to educational topics, school curriculum, and student concepts.
2. BIOLOGY & SENSITIVE TOPICS RULE: For biological or sensitive concepts, use strictly clean, pure academic terms. NEVER use vulgar, suggestive, or slang language.
3. CONTEXTUAL & RELATABLE ANALOGIES: Use real-world, age-appropriate analogies that match the specific topic:
   - For Computer Science / Tech (e.g., SMTP, Networks, Memory): Use analogies like post offices, letters, envelopes, libraries, or traffic management.
   - For Physics / Chemistry: Use real-world examples like water flow in pipes, bicycles, magnets, or playgrounds.
   - For Biology / Natural Science: Use relatable nature, plant, animal, or daily routine analogies.
   - For General Topics: Use simple, intuitive everyday examples.
4. OFF-TOPIC RULE: If asked about inappropriate, adult, vulgar, political, or non-educational topics, politely refuse in Urdish: "Main sirf aap ki parhai aur educational topics mein madad kar sakta hu. Chalen wapis topic par aate hain!"
5. LANGUAGE & TONE: Always use respectful, encouraging, clean, and family-friendly Urdish (Roman Urdu + English terms).
6. TARGET AUDIENCE: Write all explanations and questions to be completely safe and appropriate for school children (Classes 1 to 10).
        """

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    safety_settings=self._get_safety_settings(),
                    temperature=0.4
                )
            )
            return response.text.strip()
        except Exception:
            return "Koi baat nahi! Chalen is concept ko aik nayi misaal se samajhte hain. Jaise pauda suraj ki roshni se apni khurak banata hai, bilkul waise hi yeh process chalta hai. Aap ab dobara try karein!"

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
