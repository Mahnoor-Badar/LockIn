from google import genai
from google.genai import types
from config import get_gemini_api_key
from schemas.quiz_schema import QuizSchema, OverallEvaluation

# System instruction to enforce educational domain boundaries and polite Urdish tone
SYSTEM_INSTRUCTION = """
You are "LockIn AI", a dedicated, friendly, and age-appropriate virtual tutor for Pakistani school students (Grades 1 to 12).

STRICT RULES:
1. DOMAIN BOUNDARY: You MUST strictly stick to educational topics, school curriculum, and student concepts.
2. BIOLOGY & SENSITIVE TOPICS RULE: For biological concepts (e.g., cell reproduction, digestive system, plant fertilization, organ systems), use strictly clean, pure academic terms. NEVER use vulgar, suggestive, or slang language.
3. PREFERRED ANALOGIES: Use dead-simple, nature-inspired analogies wherever possible — such as flowers, plants, garden ecosystems, or familiar animals (e.g., ants working as a team, roots absorbing water like a straw, bees transferring pollen).
4. OFF-TOPIC RULE: If asked about inappropriate, adult, vulgar, political, or non-educational topics, politely refuse in Urdish: "Main sirf aap ki parhai aur educational topics mein madad kar sakta hu. Chalen wapis topic par aate hain!"
5. LANGUAGE & TONE: Always use respectful, encouraging, clean, and family-friendly Urdish (Roman Urdu + English terms).
"""

class LLMService:
    def __init__(self):
        api_key = get_gemini_api_key()
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-3.8-flash"

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

    def explain_topic(
        self,
        topic: str,
        grade: str,
        board: str = "General",
        subject: str = "General",
        student_question: str = "",
    ) -> str:
        """
        Generates an age-appropriate Urdish explanation
        based on the selected subject/topic and the student's question.
        """

        if student_question.strip():
            question_text = student_question.strip()
        else:
            question_text = (
                f"Please explain the topic '{topic}' "
                "in a simple way."
            )

        prompt = f"""
        Student profile:
        - Grade: {grade}
        - Board: {board}
        - Subject: {subject}
        - Topic: {topic}

        Student question:
        {question_text}

        Answer the student's question directly.

        Rules:
        - Stay strictly within the selected educational subject and topic.
        - Speak naturally in Urdish
          (Roman Urdu + English technical terms).
        - Match the explanation to the student's grade.
        - Use simple everyday Pakistani examples when helpful.
        - Do not unnecessarily repeat the whole topic.
        - Keep the answer clear and concise.
        - End with "Samajh aa gaya?" only when it feels natural.
        """

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    safety_settings=self._get_safety_settings(),
                    temperature=0.3,
                )
            )

            return response.text

        except Exception:
            return (
                "Mujhe is waqt jawab generate karne mein "
                "problem aa rahi hai. Please apna sawal dobara try karein."
            )

    def generate_quiz(self, topic: str, grade: str) -> QuizSchema:
        """
        Generates a 3-question multiple-choice quiz adhering to QuizSchema and safety rules.
        """
        prompt = f"Generate a 3-question multiple-choice quiz in Urdish for '{topic}', Grade '{grade}'."
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
                )
            )
            return QuizSchema.model_validate_json(response.text)
        except Exception as e:
            raise ValueError(f"Quiz generation failed due to safety limits or parsing error: {e}")