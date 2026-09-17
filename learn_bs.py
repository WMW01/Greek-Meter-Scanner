from bs4 import BeautifulSoup
import unicodedata

LENGTH_MARK_CHARS = {
    "\u0304",    # combining macron(long)
    "\u0306",    # combining breve(short)
}

SYLL_CLASSES = {
    "elided", "hiatus", "synizesis", "resolved", "unres", "exception",
    "anceps", "link"
}

# See hypotactic.com for Chamberlain's exact definition of these syllable classes
LONG_REASON_CLASSES = ("lbn", "lbp", "bil", "disastole", "preliquid", "pre-dw")
SHORT_REASON_CLASSES = ("correption", "mcl")

# Some texts are hypitatic yet contain these annotations. As Chamberlain 
# continue working on complete annotations on all the texts, I try to
# distinguish between texts that are fully annotated from texts that are not
# in order to have a better sense of how to scrape the texts. 
RICH_MARKERS = {
    "lbn", "lbp", "bil", "hiatus", "synizesis",
    "correption", "mcl", "disastole", "preliquid", "pre-dw",
}

def strip_length_marks(text: str) -> str:
    """
    Romove scansion-only macron/breve marks
    """
    decomposed = unicodedata.normalize("NFD", text)
    cleaned = [char for char in decomposed if char not in LENGTH_MARK_CHARS]
    return unicodedata.normalize("NFC", "".join(cleaned))


def metre(line_div):
        metre = line_div.get("data-metre")
        if metre:
            return metre
        
        poem = line_div.find_parent(class_ = "poem")
        return poem.get("data-metre") if poem else None
    
def parse_syllable(syll):
    raw_text = syll.get_text(strip=True)
    classes = syll.get("class", [])
    classes_set = set(classes)

    quantity = "long" if "long" in classes_set else "short"
    reason_pool = LONG_REASON_CLASSES if quantity == "long" else SHORT_REASON_CLASSES
    quantity_reason = None
    for c in reason_pool:
        if c in classes_set:
            quantity_reason = c
            break
        
        
    return {
        "text" : strip_length_marks(raw_text),
        "data_mac": syll.get("data-mac"),
        "quantity": quantity,
        "quantity_reason": quantity_reason,
        "syll_annotations": sorted(classes_set & SYLL_CLASSES),
        "classes_raw": classes, 
    }
    
def annotation_summary(soup):
    sylls = soup.select("span.syll")
    all_classes = set()
    for syll in sylls:
        all_classes.update(syll.get("class", []))

    present_rich = sorted(RICH_MARKERS & all_classes)
    has_macrons = any(syll.get("data-mac") for syll in sylls)

    return {
        "rich_marker_present": present_rich,
        "has_macrons": has_macrons
    }

def parse(self, html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    lines = []
    for line_div in soup.select("div.line"):
        syllables = []
        for word_span in line_div.select("span.word"):
            for i, syll in enumerate(word_span.select("span.syll")):
                parsed = self.parse_syllable(syll)
                parsed["word_start"] = (i==0)
                syllables.append(parsed)
            
        lines.append({
            "metre": self.metre(line_div),
            "syllables": syllables, 
        })

# collecting data for training the CRF syllabifier

def build_line_text_and_labels(syllables: list[dict]) -> dict:

    chars, labels = [], []
    for i, syll in enumerate(syllables):
        if i > 0 and syll["word_start"]:
            chars.append(" ")
            labels.append("O")
        text = syll["text"]
        for j, char in enumerate(text):
            chars.append(char)
            labels.append("B" if j == 0 else "I")
        
    return {"line_text": "".join(chars), "char_labels": labels}

if __name__ == "__main__":

    with open("iliad1.html", "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    test_line = soup.find("div", class_="line")
    #print(test_line)
    #print(f"the metre of the first line in the iliad is: {metre(test_line)}")
    #print(annotation_summary(soup))
    sylls = test_line.select("span.syll")
    syllables = []
    for syll in sylls:
        parsed_syllable = parse_syllable(syll)
        syllables.append(parsed_syllable)
    build_line_text_and_labels(syllables)


    


