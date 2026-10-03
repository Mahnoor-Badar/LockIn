import io
from gtts import gTTS
from google import genai
from config import get_gemini_api_key

class VoiceService:
    def __init__(self):
        api_key = get_gemini_api_key()
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def text_to_speech(self, text: str) -> io.BytesIO:
        """
        Converts Urdish text/analogies into spoken audio bytes.
        """
        # gTTS supports 'ur' for Urdu phonetics, which works smoothly for Roman Urdu/Urdish
        tts = gTTS(text=text, lang='ur', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp

    def transcribe_audio(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
        """
        Uses Gemini 2.5 Flash native multimodal capabilities to transcribe spoken student audio.
        """
        prompt = "Transcribe the following student spoken audio accurately. If it is in Urdish or Urdu, convert it to Roman Urdu/English text."
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                    prompt
                ]
            )
            return response.text.strip()
        except Exception as e:
            return f"Audio transcription failed: {e}"