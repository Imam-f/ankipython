import os
import json
from pathlib import Path
import re
from google import genai
from google.genai.types import (
    GenerateContentConfig,
    GoogleSearch,
    HttpOptions,
    Tool,
)

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("Error: Please set GEMINI_API_KEY environment variable.")
    exit(1)

# Configure Gemini client
client = genai.Client(http_options=HttpOptions(api_version="v1alpha"))


def clean_json_response(text: str) -> str:
    """Remove ```json fences and return clean JSON string."""
    cleaned = re.sub(
        r"^```json\s*|\s*```$", "", text.strip(), flags=re.DOTALL | re.MULTILINE
    )
    return cleaned.strip()


def regenerate_json(word: str, raw_text: str = None):
    """Ask Gemini to regenerate a clean JSON for the word."""
    if raw_text:
        prompt = f"""
        The following is a messy or unstructured dictionary entry for the word "{word}":
        {raw_text}

        Please regenerate it into valid JSON with the following keys:
        "word", "recent_usage", "definition", "etymology", "synonyms", "antonyms".
        """
    else:
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
        model="gemini-2.5-flash-lite",
        contents=prompt,
        config=GenerateContentConfig(
            tools=[Tool(google_search=GoogleSearch())]  # ✅ Ground with Google Search
        ),
    )

    return clean_json_response(response.text)


def repair_json_folder(folder="output"):
    folder = Path(folder)
    for json_file in folder.glob("*.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"⚠️ Skipping invalid JSON file: {json_file}")
                continue

        # Check if it's raw / broken
        if "raw" in data or not any(
            k in data for k in ["definition", "recent_usage", "synonyms", "antonyms"]
        ):
            word = data.get("word") or json_file.stem
            raw_text = data.get("raw", "")
            print(f"🔄 Regenerating JSON for: {word}")

            try:
                result = regenerate_json(word, raw_text)
                try:
                    parsed = json.loads(result)
                except json.JSONDecodeError:
                    print(f"❌ Still invalid JSON for {word}, saving fallback.")
                    parsed = {"word": word, "raw": result}

                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(parsed, f, ensure_ascii=False, indent=2)

                print(f"✅ Fixed {word} → {json_file}")
            except Exception as e:
                print(f"❌ Error regenerating {word}: {e}")


if __name__ == "__main__":
    import sys

    folder = sys.argv[1] if len(sys.argv) > 1 else "output"
    repair_json_folder(folder)