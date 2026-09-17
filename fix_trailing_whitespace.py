import glob
import json
import unicodedata
from pathlib import Path
import sys
import re

LENGTH_MARK_CHARS = {
    "\u0304", # combining macron (long)
    "\u0306", # combining breve
}

ELISION_MARKS_CHARS = {
    "\u2019", # right single quotation mark
    "\u1FBD", # greek koronis proper
    "\u0027", # plain ASCII apostrophe
}

def is_essential_char(char: str) -> bool:
    if char in LENGTH_MARK_CHARS:
        return False
    if char in ELISION_MARKS_CHARS:
        return True
    if char.isspace():
        return True
    category = unicodedata.category(char)
    return category.startswith("L") or category == "Mn"

def clean_syllable_text(text: str) -> str:
    pattern = r'\s{2,}'
    decomposed = unicodedata.normalize("NFD", text)
    cleaned = "".join(char for char in decomposed if is_essential_char(char))
    cleaned = re.sub(pattern, " ", cleaned).strip()
    return unicodedata.normalize("NFC", cleaned)

def build_line_text_and_labels(syllables: list[dict]):  
    chars = []
    labels = []
    for i, syll in enumerate(syllables):
        if i > 0 and syll["word_start"]:
            chars.append(" ")
            labels.append("O")
        text = syll["text_clean"]
        for j, char in enumerate(text):
            chars.append(char)
            labels.append("B" if j == 0 else "I")

    return {"line": "".join(chars), "labels": labels}

def fix_file(path: str, outdir: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    
    syllables_changed = 0
    lines_changed = 0

    for line in data.get("lines", []):
        syllables = line.get("annotated_syllables", [])
        line_changed = False
        changed_syllables_count = 0

        for syll in syllables:
            old_clean = syll.get("text_clean", "")
            new_clean = clean_syllable_text(syll.get("text", ""))
            if old_clean != new_clean:
                changed_syllables_count += 1
                syll["text_clean"] = new_clean
                syllables_changed += 1
                line_changed = True
                if changed_syllables_count < 100:
                    print(f"the old text is: {old_clean} ----- the new text is: {new_clean}")
                    
        
        if line_changed:
            line["line_text_and_labels"] = build_line_text_and_labels(syllables) 
            lines_changed += 1

    outdir.mkdir(parents=True, exist_ok=True)
    out_path = outdir / Path(path).name
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"syllables_changed": syllables_changed, 
            "lines_changed": lines_changed,
            "out_path": str(out_path)}

if __name__ == "__main__":

    pattern = sys.argv[1] if len(sys.argv) > 1 else "scraped_texts/*.json"
    outdir = Path(sys.argv[2] if len(sys.argv) > 2 else "scraped_texts_fixed")

    total_syllables = 0
    total_lines = 0
    files_touched = 0

    for path in glob.glob(pattern):
        result = fix_file(path, outdir)
        if result["syllables_changed"] > 0:
            files_touched += 1
            total_syllables += result["syllables_changed"]
            total_lines += result["lines_changed"]
            print(f"{path}: fixed {result["syllables_changed"]} syllable(s) across {result["lines_changed"]} line(s)")
    
    print({total_lines})