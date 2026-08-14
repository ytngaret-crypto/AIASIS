
import asyncio
from google import genai
from google.genai import types
from config import GEMINI_API_KEY,GEMINI_MODEL,SYSTEM_PROMPT,MAX_OUTPUT_CHARS

client=genai.Client(api_key=GEMINI_API_KEY)

def _call(history,prompt):
    contents=[]
    for role,text in history:
        contents.append(types.Content(role="user" if role=="user" else "model",
                                      parts=[types.Part.from_text(text=text)]))
    contents.append(types.Content(role="user",parts=[types.Part.from_text(text=prompt)]))
    r=client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=1000,
        ),
    )
    out=(r.text or "").strip()
    if not out: raise RuntimeError("Gemini returned empty text")
    return out[:MAX_OUTPUT_CHARS]

async def ask(history,prompt):
    return await asyncio.to_thread(_call,history,prompt)
