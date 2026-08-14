from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL, PERSONALITY, MAX_OUTPUT_CHARS

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_reply(history, user_text: str) -> str:
    contents = []
    for item in history:
        role = item.get("role")
        text = item.get("text", "")
        if text:
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text)]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_text)]))

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=PERSONALITY,
            temperature=0.7,
            max_output_tokens=700,
        ),
    )
    text = (response.text or "").strip()
    if not text:
        return "Maaf, aku belum bisa menjawab sekarang."
    return text[:MAX_OUTPUT_CHARS]
