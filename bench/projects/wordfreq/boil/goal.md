# Goal

**One-line:** `wordfreq FILE` prints the most frequent words with --top and clean errors

## Success checklist
- [ ] `python -m wordfreq --help` exits 0 and mentions --top
- [ ] `python -m wordfreq FILE` prints `word count` lines, most frequent first, ties alphabetical, case-insensitive
- [ ] `--top N` limits the output to N lines
- [ ] a missing file exits 2 with `error:` on stderr; an empty file prints nothing and exits 0

## Requirements understanding
| Requirement | Interpretation | Acceptance signal | Confidence | Open uncertainty |
|---|---|---|---|---|
| a | b | c | 95 | none |

## How the user will see this works
printf 'b a b c a b' > f.txt && python -m wordfreq f.txt --top 2
