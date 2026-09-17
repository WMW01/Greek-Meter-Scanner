"""
Scans every scraped JSON file for syllables whose text_clean has
leading/trailing whitespace -- the exact signature of the "space
attached to punctuation that then gets stripped" bug confirmed this
session (e.g. raw "δείλ' ," -> text_clean "δείλ' ", trailing space
left over once the comma is removed).

A genuine, correctly-formed embedded elision space (e.g. "δ' ιφ") is
NEVER leading or trailing within one syllable's own text -- it's
always sandwiched between real letters on both sides -- so this check
has no false positives from real elision-merge syllables.

Usage:
    python find_trailing_whitespace_bug.py "scraped_texts/*.json"
"""

import glob
import json
import sys


def find_affected_syllables(paths):
    affected = []
    for path in glob.glob(paths):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        use_id = data.get("use_id", path)
        for line in data.get("lines", []):
            line_num_field = line.get("line_num")
            # Handle either shape: a plain int (older scrapes) or the
            # {"line_number": ..., "line_number_suffix": ...} dict
            # (current scraper.py's line_number()) -- don't assume one,
            # since this session has already found local files diverge
            # from whatever the current script looks like.
            if isinstance(line_num_field, dict):
                line_num = line_num_field.get("line_number")
            else:
                line_num = line_num_field
            for syll in line.get("annotated_syllables", []):
                clean = syll.get("text_clean", "")
                if clean != clean.strip():
                    affected.append({
                        "use_id": use_id,
                        "line_number": line_num,
                        "raw_text": syll.get("text"),
                        "text_clean": clean,
                        "text_clean_repr": repr(clean),  # makes the whitespace visible
                    })
    return affected


if __name__ == "__main__":
    pattern = sys.argv[1] if len(sys.argv) > 1 else "scraped_texts/*.json"
    affected = find_affected_syllables(pattern)

    print(f"Found {len(affected)} affected syllable(s) across the corpus.\n")

    # Group by use_id for a readable summary
    by_work = {}
    for a in affected:
        by_work.setdefault(a["use_id"], []).append(a)

    for use_id, items in sorted(by_work.items()):
        print(f"{use_id}: {len(items)} occurrence(s)")
        for item in items[:5]:  # cap per-work printout so this stays readable
            print(f"    line {item['line_number']}: raw={item['raw_text']!r} -> clean={item['text_clean_repr']}")
        if len(items) > 5:
            print(f"    ... and {len(items) - 5} more")
        print()

    # Also dump the full list to a file, useful for actually reporting this upstream
    with open("trailing_whitespace_bug_report.json", "w", encoding="utf-8") as f:
        json.dump(affected, f, ensure_ascii=False, indent=2)
    print(f"Full report ({len(affected)} entries) written to trailing_whitespace_bug_report.json")