#!/usr/bin/env python3
"""Convert a quoted CSV into one JSON object per record for Hadoop and Spark."""
import csv
import json
import sys
from pathlib import Path

ALIASES = {
    "category": ("category", "product_category"),
    "rating": ("rating", "rate", "stars"),
    "label": ("label", "class", "target"),
    "text_": ("text_", "review", "review_text", "text"),
}

def main(source, destination):
    input_path, output_path = Path(source), Path(destination)
    count = 0
    with input_path.open("r", encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file)
        if not reader.fieldnames:
            raise ValueError("The CSV is empty or has no header row.")
        normalized = {name.strip().lower(): name for name in reader.fieldnames}
        columns = {key: next((normalized[a] for a in aliases if a in normalized), None)
                   for key, aliases in ALIASES.items()}
        missing = [key for key in ("label", "text_") if columns[key] is None]
        if missing:
            raise ValueError("Missing required column(s): " + ", ".join(missing) +
                             ". Expected label and text_ (or review/text).")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8", newline="") as output_file:
            for row in reader:
                text = (row.get(columns["text_"]) or "").strip()
                label = (row.get(columns["label"]) or "").strip()
                if not text or not label:
                    continue
                record = {"text_": text, "label": label}
                for key in ("category", "rating"):
                    record[key] = (row.get(columns[key]) or "").strip() if columns[key] else ""
                output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
    if count == 0:
        raise ValueError("No rows with both review text and label were found.")
    print(f"Prepared {count} valid review records as JSON Lines.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: prepare_reviews.py INPUT.csv OUTPUT.jsonl")
    main(sys.argv[1], sys.argv[2])
