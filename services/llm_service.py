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

    def explain_topic(self, topic: str, grade: str, board: str = "General") -> str:
        """
        Generates an Urdish explanation for a given topic with safety guardrails.
        """
        prompt = f"""
        Explain the topic '{topic}' for Grade '{grade}' ({board} Board).
        - Speak naturally in Urdish (Roman Urdu + English technical terms).
        - Use simple, everyday Pakistani analogies.
        - Keep it concise and end by asking if they understood ("Smjh aa gya?").
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
        except Exception as e:
            return "Yeh topic safe parhai ke dairey mein nahi aata ya API response error aya hai. Please apna topic check karein!"

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