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
3. PREFERRED ANALOGIES: Use dead-simple, nature-inspired analogies wherever possible — such as flowers, plants, garden ecosystems, or familiar animals (e.g., ants working as a team, roots absorbing water like a straw, bees transferring pollen).
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

    def generate_quiz(self, subject: str, topic: str, grade: str) -> QuizSchema:
        """
        Generates a 6-question tiered multiple-choice quiz (2 Easy, 2 Medium, 2 Hard)
        for the specified subject, topic, and grade using Gemini JSON Schema mode.
        """
        try:
            grade_num = int(''.join(filter(str.isdigit, grade)))
        except ValueError:
            grade_num = 5

        allowed_subjects = self.get_allowed_subjects(grade_num)
        if subject.strip().title() not in [s.title() for s in allowed_subjects]:
            raise ValueError(
                f"Subject '{subject}' is not available for {grade}. "
                f"Available subjects for {grade}: {', '.join(allowed_subjects)}"
            )

        prompt = f"""
        Create a 6-question multiple-choice quiz in Urdish (Roman Urdu + English terms) 
        testing core concepts for Subject: '{subject}', Topic: '{topic}', Grade: '{grade}'.

        STRICT DIFFICULTY BREAKDOWN:
        - Questions 1 & 2: 'easy' difficulty (Basic recall and definitions)
        - Questions 3 & 4: 'medium' difficulty (Application of concept)
        - Questions 5 & 6: 'hard' difficulty (Reasoning/conceptual mastery)

        Requirements:
        - Exactly 6 questions total.
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