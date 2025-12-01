from flask import Flask, render_template, jsonify, send_file
import sqlite3
import json
import os
from gtts import gTTS
from io import BytesIO

DB_FILE = "words.db"
WORDS_DIR = "../output_jsons"

app = Flask(__name__)

# ---------- Database ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS words (
            word TEXT PRIMARY KEY,
            definition TEXT,
            frequency INTEGER,
            read_count INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()


def load_words_from_folder():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    for fn in os.listdir(WORDS_DIR):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(WORDS_DIR, fn)
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                word = data.get("word")
                definition = data.get("definition", "")
                freq = data.get("frequency", 0)
                cur.execute(
                    "INSERT OR IGNORE INTO words (word, definition, frequency) VALUES (?, ?, ?)",
                    (word, definition, freq),
                )
            except Exception as e:
                print(f"Failed to load {fn}: {e}")
    conn.commit()
    conn.close()


# ---------- Logic ----------
def get_next_word():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT word, definition, frequency, read_count
        FROM words
        ORDER BY read_count ASC, frequency DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "word": row[0],
            "definition": row[1],
            "frequency": row[2],
            "count": row[3],
        }
    return None


def increment_count(word):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE words SET read_count = read_count + 1 WHERE word = ?", (word,))
    conn.commit()
    conn.close()


# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/next")
def next_word():
    word_data = get_next_word()
    if not word_data:
        return jsonify({"error": "No words available."})
    increment_count(word_data["word"])
    return jsonify(word_data)


@app.route("/audio/<word>")
def audio(word):
    """Generate and stream TTS audio."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT definition FROM words WHERE word = ?", (word,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Word not found"}), 404

    text = f"{word}. Definition: {row[0]}"
    tts = gTTS(text=text, lang="en")
    audio_fp = BytesIO()
    tts.write_to_fp(audio_fp)
    audio_fp.seek(0)

    return send_file(
        audio_fp,
        mimetype="audio/mpeg",
        as_attachment=False,
        download_name=f"{word}.mp3",
    )


if __name__ == "__main__":
    init_db()
    load_words_from_folder()
    app.run(debug=True)