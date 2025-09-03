const express = require("express");
const bodyParser = require("body-parser");
const path = require("path");
const fs = require("fs");
const sqlite3 = require("sqlite3").verbose();

const app = express();
const PORT = 3030;

// 🔧 Configurable session length
const SESSION_LENGTH = 20;

app.use(bodyParser.json());
app.use(express.static("public"));
app.set("view engine", "ejs");

const db = new sqlite3.Database("flashcards.db");

// Create table if not exists
db.serialize(() => {
  db.run(`
    CREATE TABLE IF NOT EXISTS overall_queue (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      word TEXT,
      recent_usage TEXT,
      definition TEXT,
      etymology TEXT,
      synonyms TEXT,
      antonyms TEXT
    )
  `);
});

// Load JSON files into DB if empty
function loadDataFromFiles() {
  db.get("SELECT COUNT(*) as count FROM overall_queue", (err, row) => {
    if (err) throw err;
    if (row.count === 0) {
      const folder = path.join(__dirname, "../output");
      const files = fs.readdirSync(folder);

      files.forEach((file) => {
        if (file.endsWith(".json")) {
          const data = JSON.parse(
            fs.readFileSync(path.join(folder, file), "utf-8")
          );
          db.run(
            `INSERT INTO overall_queue 
              (word, recent_usage, definition, etymology, synonyms, antonyms) 
              VALUES (?, ?, ?, ?, ?, ?)`,
            [
              data.word,
              data.recent_usage,
              data.definition,
              data.etymology,
              JSON.stringify(data.synonyms),
              JSON.stringify(data.antonyms),
            ]
          );
        }
      });
      console.log("Data loaded into DB from JSON files.");
    }
  });
}

loadDataFromFiles();

// Session queue
let sessionQueue = [];
let currentIndex = 0;

// Reset session queue: pull N cards from DB
function resetSessionQueue(n = SESSION_LENGTH, callback) {
  db.all("SELECT * FROM overall_queue LIMIT ?", [n], (err, rows) => {
    if (err) throw err;
    sessionQueue = rows;
    currentIndex = 0;
    if (callback) callback();
  });
}

// Initial session load
resetSessionQueue();

// Routes
app.get("/", (req, res) => {
  const currentCard = sessionQueue[currentIndex] || null;
  res.render("index", {
    card: currentCard,
    index: currentIndex,
    total: sessionQueue.length,
  });
});

// Navigation
app.post("/navigate", (req, res) => {
  const { direction } = req.body;
  if (direction === "right" && currentIndex < sessionQueue.length - 1) {
    currentIndex++;
  } else if (direction === "left" && currentIndex > 0) {
    currentIndex--;
  }
  res.json({
    card: sessionQueue[currentIndex] || null,
    index: currentIndex,
    total: sessionQueue.length,
  });
});

// Actions (Easy/Medium/Hard)
app.post("/action", (req, res) => {
  const { action } = req.body;
  const card = sessionQueue[currentIndex];

  if (!card) return res.json({ message: "No card available" });

  if (action === "easy") {
    db.run(
      `INSERT INTO overall_queue 
        (word, recent_usage, definition, etymology, synonyms, antonyms) 
        VALUES (?, ?, ?, ?, ?, ?)`,
      [
        card.word,
        card.recent_usage,
        card.definition,
        card.etymology,
        card.synonyms,
        card.antonyms,
      ]
    );
  } else if (action === "medium") {
    db.serialize(() => {
      db.run("DELETE FROM overall_queue WHERE id = ?", [card.id], () => {
        db.run(
          `INSERT INTO overall_queue 
            (id, word, recent_usage, definition, etymology, synonyms, antonyms) 
            VALUES (?, ?, ?, ?, ?, ?, ?)`,
          [
            card.id,
            card.word,
            card.recent_usage,
            card.definition,
            card.etymology,
            card.synonyms,
            card.antonyms,
          ]
        );
      });
    });
  } else if (action === "hard") {
    sessionQueue.push(card);
  }

  // After action, move to next card if possible
  if (currentIndex < sessionQueue.length - 1) {
    currentIndex++;
  }

  res.json({
    card: sessionQueue[currentIndex] || null,
    index: currentIndex,
    total: sessionQueue.length,
  });
});

// Reset session
app.post("/reset", (req, res) => {
  resetSessionQueue(SESSION_LENGTH, () => {
    res.json({
      card: sessionQueue[currentIndex] || null,
      index: currentIndex,
      total: sessionQueue.length,
    });
  });
});

app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});