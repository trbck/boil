import argparse
import re
import sys
from collections import Counter

WORD = re.compile(r"\w+")


def count_words(text):
    counts = Counter(w.lower() for w in WORD.findall(text))
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="wordfreq", description="Print the most frequent words in a text file.")
    ap.add_argument("file")
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args(argv)
    with open(args.file, encoding="utf-8") as fh:
        text = fh.read()
    for word, n in count_words(text)[: args.top]:
        sys.stdout.write(f"{word} {n}\n")
    return 0
