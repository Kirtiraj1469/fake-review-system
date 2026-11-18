#!/usr/bin/env python3
"""Hadoop Streaming reducer that totals the mapper's tab-separated counts."""
import sys


def reduce_lines(lines):
    counts = {}
    for line in lines:
        try:
            key, value = line.rstrip("\n").split("\t", 1)
            counts[key] = counts.get(key, 0) + int(value)
        except (ValueError, TypeError):
            continue
    return counts


def main():
    for key, count in sorted(reduce_lines(sys.stdin).items()):
        sys.stdout.write(f"{key}\t{count}\n")


if __name__ == "__main__":
    main()
