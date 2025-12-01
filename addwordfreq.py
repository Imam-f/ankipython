import os
import json
import requests

# --- Configuration ---
SOURCE_DIR = "vocab_json"        # Folder containing your existing JSON files
OUTPUT_DIR = "vocab_output_jsons"       # Folder to save updated JSON files
API_URL = "https://api.datamuse.com/words?sp={word}"  # Example endpoint

# --- Function to fetch frequency data ---
def fetch_word_frequency(word):
    try:
        # Example using Datamuse API; replace with your real endpoint as needed
        response = requests.get(API_URL.format(word=word))
        response.raise_for_status()
        data = response.json()
        # Example: Datamuse returns a list of word objects that may contain 'score' or 'tags'
        # Adjust logic below depending on your API response structure
        if data:
            # Here we fake a 'frequency' value from 'score' or any numeric data available
            return data[0].get("score", 0)
        return None
    except requests.RequestException:
        return None

# --- Ensure output directory exists ---
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Process JSON files ---
for filename in os.listdir(SOURCE_DIR):
    if filename.endswith(".json"):
        source_path = os.path.join(SOURCE_DIR, filename)
        output_path = os.path.join(OUTPUT_DIR, filename)

        with open(source_path, "r", encoding="utf-8") as f:
            word_data = json.load(f)

        word = word_data.get("word")
        if word:
            frequency = fetch_word_frequency(word)
            word_data["frequency"] = frequency

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(word_data, f, indent=2, ensure_ascii=False)

        print(f"Processed: {filename} → frequency={frequency}")