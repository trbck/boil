import argparse
import sys


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="wordfreq", description="Print the most frequent words in a text file.")
    ap.add_argument("file")
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args(argv)
    return 0
