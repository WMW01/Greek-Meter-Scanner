import glob
import json
from collections import Counter, defaultdict

def count_metres(paths:list[str])->tuple[Counter, dict]:
    metre_counts = Counter()
    metre_texts = defaultdict(set)
    for path in paths:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

            use_id = data.get("use_id", None)
            for line in data.get("lines", []):
                line_metre = line["metre"]
                if line_metre == "hexameter incomplete":
                    print(use_id, line["line_num"])
                metre_counts[line_metre] += 1
                metre_texts[line_metre].add(use_id)

    return metre_counts, metre_texts 

if __name__ == "__main__":
    pattern = "scraped_texts/*.json"
    paths = glob.glob(pattern)
    metre_counts, metre_texts = count_metres(paths)
    ranked_metre_counts = metre_counts.most_common()

    with open("metre_counts.json", "w", encoding="utf-8") as f:
        json.dump(ranked_metre_counts, f, ensure_ascii=False, indent=2)

    


