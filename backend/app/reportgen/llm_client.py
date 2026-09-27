"""LLM report writer client.

Model choice (gemini-3.6-flash) is taken verbatim from the design doc's
answered open question -- OPEN ITEM: verify the exact model id in your
Google AI Studio / Vertex account, it is not independently confirmed here.
"""

from google import genai

from app.config import Settings


def generate_report_md(prompt: str, settings: Settings) -> str:
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
    )
    return response.text
