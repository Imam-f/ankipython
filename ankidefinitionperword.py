import sqlite3
import json
import zipfile
import os
import sys
from pathlib import Path
import re

# Gemini API (grounded)
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
    sys.exit(1)

# Configure Gemini client
client = genai.Client(http_options=HttpOptions(api_version="v1alpha"))


def extract_sort_field_words(apkg_path):
    """Extract all sort field values (words) from an Anki .apkg deck."""
    with zipfile.ZipFile(apkg_path, "r") as z:
        if "collection.anki2" not in z.namelist():
            raise FileNotFoundError("collection.anki2 not found in the .apkg file")
        z.extract("collection.anki2", path=".")

    conn = sqlite3.connect("collection.anki2")
    cursor = conn.cursor()

    # Load models
    cursor.execute("SELECT models FROM col")
    row = cursor.fetchone()
    if not row:
        raise ValueError("No models found in collection.anki2")
    models = json.loads(row[0])

    # Map model_id -> sort field index
    model_info = {}
    for model_id, model in models.items():
        sort_field_index = model.get("sortf", 0)
        model_info[int(model_id)] = sort_field_index

    # Extract notes
    cursor.execute("SELECT mid, flds FROM notes")
    notes = cursor.fetchall()

    words = []
    for mid, flds in notes:
        if mid not in model_info:
            continue
        sort_field_index = model_info[mid]
        field_values = flds.split("\x1f")
        if 0 <= sort_field_index < len(field_values):
            word = field_values[sort_field_index].strip()
            if word:
                words.append(word)

    conn.close()
    os.remove("collection.anki2")
    return words


def clean_json_response(text: str) -> str:
    """Remove ```json fences and return clean JSON string."""
    # Remove markdown fences like ```json ... ```
    cleaned = re.sub(r"^```json\s*|\s*```$", "", text.strip(), flags=re.DOTALL | re.MULTILINE)
    return cleaned.strip()


def fetch_word_info(word: str):
    """Fetch definition, usage, synonyms, antonyms, etc. from Gemini (grounded)."""
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


def main(apkg_path, output_folder="output"):
    Path(output_folder).mkdir(parents=True, exist_ok=True)

    words = extract_sort_field_words(apkg_path)
    print(f"Found {len(words)} words in deck.")

    for word in words:
        safe_word = word.replace(" ", "_").replace("/", "_")
        out_path = Path(output_folder) / f"{safe_word}.json"

        if out_path.exists():
            print(f"✅ Skipping {word} (already exists)")
            continue

        print(f"🔎 Fetching info for: {word}")
        try:
            result = fetch_word_info(word)

            # Validate JSON before saving
            try:
                parsed = json.loads(result)
            except json.JSONDecodeError:
                print(f"⚠️ Warning: Gemini returned invalid JSON for {word}, saving raw text.")
                parsed = {"word": word, "raw": result}

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2)

            print(f"💾 Saved {word} → {out_path}")
        except Exception as e:
            print(f"❌ Error fetching {word}: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python anki_definitions.py deck.apkg [output_folder]")
        sys.exit(1)

    apkg_path = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else "output"
    main(apkg_path, output_folder)