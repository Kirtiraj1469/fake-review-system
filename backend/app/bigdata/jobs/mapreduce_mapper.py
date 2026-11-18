#!/usr/bin/env python3
"""Hadoop Streaming mapper. Input records are JSON Lines from prepare_reviews.py."""
import json
import sys


def map_record(line):
    try:
        review = json.loads(line)
    except json.JSONDecodeError:
        return []
    category = str(review.get("category") or "(missing)").strip() or "(missing)"
    rating = str(review.get("rating") or "(missing)").strip() or "(missing)"
    label = str(review.get("label") or "(missing)").strip().upper() or "(missing)"
    return [f"category:{category}\t1\n", f"rating:{rating}\t1\n", f"label:{label}\t1\n"]


def main():
    for line in sys.stdin:
        sys.stdout.writelines(map_record(line))


if __name__ == "__main__":
    main()
