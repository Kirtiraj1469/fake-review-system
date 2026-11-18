import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from backend.app.bigdata.jobs.prepare_reviews import main as prepare_csv
from backend.app.bigdata.jobs.mapreduce_mapper import map_record
from backend.app.bigdata.jobs.mapreduce_reducer import reduce_lines

class BigDataJobTests(unittest.TestCase):
    def test_csv_quotes_commas_and_embedded_newline_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "reviews.csv"
            target = root / "reviews.jsonl"
            source.write_text('category,rating,label,text_\n"Phones, premium",5,OR,"Works well, fast\nsecond line"\n', encoding="utf-8")
            prepare_csv(str(source), str(target))
            row = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(row["category"], "Phones, premium")
            self.assertEqual(row["text_"], "Works well, fast\nsecond line")

    def test_blank_rows_are_skipped_and_missing_optional_columns_are_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / "reviews.csv", Path(directory) / "reviews.jsonl"
            source.write_text('text_,label\n"",CG\nA real review,OR\n', encoding="utf-8")
            prepare_csv(str(source), str(target))
            row = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(row["text_"], "A real review")
            self.assertEqual(row["category"], "")

    def test_mapper_reducer_count_category_rating_and_source_labels(self):
        rows = [
            {"category": "Books", "rating": "5", "label": "OR", "text_": "good"},
            {"category": "Books", "rating": "5", "label": "CG", "text_": "fake"},
            {"category": "", "rating": "", "label": "OR", "text_": "review"},
        ]
        mapped = []
        for row in rows:
            mapped.extend(map_record(json.dumps(row)))
        reduced = reduce_lines(sorted(mapped))
        self.assertEqual(reduced["category:Books"], 2)
        self.assertEqual(reduced["rating:5"], 2)
        self.assertEqual(reduced["label:OR"], 2)
        self.assertEqual(reduced["label:CG"], 1)
        self.assertEqual(reduced["category:(missing)"], 1)

if __name__ == "__main__":
    unittest.main()
