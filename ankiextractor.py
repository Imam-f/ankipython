import sqlite3
import json
import zipfile
import sys
import os


def extract_sort_field_content(apkg_path, output_file):
    # Step 1: Extract collection.anki2 from the apkg (it's a zip file)
    with zipfile.ZipFile(apkg_path, "r") as z:
        if "collection.anki2" not in z.namelist():
            raise FileNotFoundError("collection.anki2 not found in the .apkg file")
        z.extract("collection.anki2", path=".")

    # Step 2: Connect to the SQLite database
    conn = sqlite3.connect("collection.anki2")
    cursor = conn.cursor()

    # Step 3: Get the models JSON from the col table
    cursor.execute("SELECT models FROM col")
    row = cursor.fetchone()
    if not row:
        raise ValueError("No models found in collection.anki2")

    models = json.loads(row[0])

    # Step 4: Get all notes
    cursor.execute("SELECT id, mid, flds FROM notes")
    notes = cursor.fetchall()

    # Step 5: Map model_id -> (model_name, sort_field_index, field_names)
    model_info = {}
    for model_id, model in models.items():
        model_name = model.get("name", f"Model_{model_id}")
        sort_field_index = model.get("sortf", 0)
        fields = [fld.get("name", "Unknown") for fld in model.get("flds", [])]
        model_info[int(model_id)] = (model_name, sort_field_index, fields)

    # Step 6: Extract sort field content
    results = {}
    for note_id, mid, flds in notes:
        if mid not in model_info:
            continue
        model_name, sort_field_index, fields = model_info[mid]
        field_values = flds.split("\x1f")  # fields are separated by 0x1F
        if 0 <= sort_field_index < len(field_values):
            sort_value = field_values[sort_field_index]
        else:
            sort_value = ""
        results.setdefault(model_name, []).append(sort_value)

    conn.close()

    # Step 7: Save results to file
    with open(output_file, "w", encoding="utf-8") as f:
        for model_name, values in results.items():
            f.write(f"Note Type: {model_name}\n")
            f.write("Sort Field Values:\n")
            for v in values:
                f.write(f"  - {v}\n")
            f.write("\n")

    # Clean up extracted DB
    os.remove("collection.anki2")

    print(f"Sort field contents saved to {output_file}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python extract_sort_field_content.py deck.apkg output.txt")
        sys.exit(1)

    apkg_path = sys.argv[1]
    output_file = sys.argv[2]
    extract_sort_field_content(apkg_path, output_file)