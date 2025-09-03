from google import genai
from google.genai.types import (
    GenerateContentConfig,
    GoogleSearch,
    HttpOptions,
    Tool,
)
import os
import sys

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("Error: Please set GEMINI_API_KEY environment variable.")
    sys.exit(1)

def get_word_info(word: str):
    # ✅ Use v1alpha for grounding support
    client = genai.Client(http_options=HttpOptions(api_version="v1alpha"))

    prompt = f"""
    You are a dictionary assistant. For the word "{word}", provide the following:
    - Recent usage: a natural example sentence
    - Definition: clear and concise
    - Etymology: origin of the word
    - Synonyms: list of synonyms
    - Antonyms: list of antonyms

    Format the response in JSON with keys:
    "word", "recent_usage", "definition", "etymology", "synonyms", "antonyms".
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=GenerateContentConfig(
            tools=[
                Tool(google_search=GoogleSearch())  # ✅ Ground with Google Search
            ]
        ),
    )

    return response.text


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python word_info_grounded.py <word>")
        sys.exit(1)

    word = sys.argv[1]
    result = get_word_info(word)
    print(result)