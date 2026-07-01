
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def get_ai_client():
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return None

    return OpenAI(api_key=api_key)


def ask_ai(prompt, model="gpt-4.1-mini"):
    client = get_ai_client()

    if client is None:
        raise RuntimeError("OPENAI_API_KEY not found.")

    response = client.responses.create(
        model=model,
        input=prompt,
    )

    return response.output_text


def ask_ai_json(prompt, model="gpt-4.1-mini"):
    """
    Sends a prompt to OpenAI and expects ONLY valid JSON.
    Returns a Python dictionary.
    """

    text = ask_ai(prompt, model=model)

    # Remove Markdown code fences if the model returns them
    text = text.strip()

    if text.startswith("```json"):
        text = text[7:]

    if text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    return json.loads(text)

