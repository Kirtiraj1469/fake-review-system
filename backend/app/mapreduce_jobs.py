"""Hadoop Streaming compatible review aggregation with an identical local runner."""
import json
import sys
from collections import Counter

def mapper(source, destination):
    for line in source:
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        label = str(row.get("predicted_label", "unlabeled"))
        destination.write(f"label:{label}\t1\n")
        words = str(row.get("Review", row.get("text_", row.get("review", "")))).lower().split()
        for word in words:
            word = "".join(char for char in word if char.isalnum())
            if len(word) > 2:
                destination.write(f"word:{word}\t1\n")

def reducer(source, destination):
    counts = Counter()
    for line in source:
        try:
            key, value = line.rstrip("\n").split("\t", 1)
            counts[key] += int(value)
        except (ValueError, TypeError):
            continue
    for key, count in sorted(counts.items()):
        destination.write(f"{key}\t{count}\n")

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"mapper", "reducer"}:
        raise SystemExit("Usage: python mapreduce_jobs.py mapper|reducer")
    (mapper if sys.argv[1] == "mapper" else reducer)(sys.stdin, sys.stdout)

if __name__ == "__main__":
    main()
