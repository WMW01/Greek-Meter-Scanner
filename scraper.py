import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from text_metadata import use_id_to_metadata, lower_underscore, metatdata_to_filename

LENGTH_MARK_CHARS = {
    "\u0304",    # combining macron(long)
    "\u0306",    # combining breve(short)
}

ELISION_MARK_CHARS = {
    "\u2019", # right single quotation mark
    "\u1FBD", # greek koronis proper
    "\u0027", # plain ASCII apostrophe
}

SYLL_CLASSES = {
    "elided", "hiatus", "synizesis", "resolved", "unres", "exception",
    "anceps", "link", 
    "deleted", # texts enclosed in square brackets [], spurious, might be deleted 
    "added", # texts enclosed in angle brackets <>, indicating editorial addition
}

# See hypotactic.com for Chamberlain's exact definition of these syllable classes
LONG_REASON_CLASSES = ("lbn", "lbp", "bil", "diastole", "preliquid", "pre-dw")
SHORT_REASON_CLASSES = ("correption", "mcl")

# Some texts in hypotatic yet contain these annotations. While Chamberlain 
# continues working on complete annotations on all the texts, I try to
# distinguish between texts that are fully annotated from texts that are not
# in order to have a better sense of how to use the scraped data. 
RICH_MARKERS = {
    "lbn", "lbp", "bil", "hiatus", "synizesis",
    "correption", "mcl", "diastole", "preliquid", "pre-dw",
}

def is_essential_char(char:str) -> bool:
    """
    True for Greek letters, real combining marks (accent/breathing/iota subscription),
    whitespace(needed inside elision-merged syllables like "δ' ιφ"), and the elision mark.
    Flase for everything else, including macron/brev and any punctutaion. 
    """
    if char in LENGTH_MARK_CHARS:
        return False
    if char in ELISION_MARK_CHARS:
        return True
    if char.isspace():
        return True
    category = unicodedata.category(char)
    return category.startswith("L") or category == "Mn"

def clean_syllable_text(text:str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    cleaned = "".join(char for char in decomposed if is_essential_char(char))
    return unicodedata.normalize("NFC", cleaned)


class HypotacticScraper: 
    BASE_URL = "https://hypotactic.com/latin/index.html?Use_Id={use_id}"
    
    def __init__(self, wait_ms: int = 300, headless: bool = True, delay_between: float = 1.0):

        self.wait_ms = wait_ms
        self.headless = headless
        self.delay_between = delay_between

    def fetch_html(self, page, use_id: str) -> str:
        url = self.BASE_URL.format(use_id=use_id)
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(self.wait_ms)
        return page.content()
    
    def metre(self, line_div):
        metre = line_div.get("data-metre")
        if metre:
            return metre
        
        poem = line_div.find_parent(class_ = "poem")
        return poem.get("data-metre") if poem else None

    def is_incomplete(self, line_div) -> bool:
        classes = line_div.get("class", [])
        has_class = "incomplete" in classes
        has_lacuna_span = line_div.select_one("span.lacuna") is not None
        return has_class or has_lacuna_span
    
    def speaker(self, line_div):
        return line_div.get("data-speaker")

    def poem_info(self, line_div):
        """
        Anthology-style texts (e.g. Bion) wrap each poem in its own .poem div
        with its own number/title. Continuous work has no .poem div wrapper,
        and thus None for number/title
        """
        poem = line_div.find_parent(class_="poem")
        if not poem:
            return {"poem_number": None, "poem_title": None}
        
        number_div = poem.select_one(".poem_number")
        title_div = poem.select_one(".poem_title")

        poem_number_text = number_div.get_text(strip=True) if number_div else None
        poem_number = int(poem_number_text) if poem_number_text and poem_number_text.isdigit() else None
        poem_title = title_div.get_text(strip=True) if title_div else None

        return {"poem_number": poem_number, "poem_title": poem_title}
    
    def line_number(self, line_div):
        # The majority of the line numebrs are represented by an individual numbers
        # but some line number has a suffix in letter, indicating interpolated/disputed lines.
        n = line_div.get("data-number")
        match = re.match(r"^(\d+)([a-z]*)$", n)
        if not match:
            print(f"The unrecognized line number format: {n!r} --- line text: {line_div.get_text(strip=True)[:60]!r}")
            return {"line_number": None, "line_number_suffix": None}
        number_part, suffix_part = match.groups()
        return{
            "line_number": int(number_part),
            "line_number_suffix": suffix_part or None
        }
    
    def parse_syllable(self, syll, bracket_state: dict):
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
        
        flags = set(classes_set & SYLL_CLASSES)

        # texts in brackets can span across words, even lines. In some richly annotated 
        # texts, all the syllables in brackets has the class flags "added" or "deleted",
        # but in some texts, the class flags are missing

        # find a left bracket in a syllable, therefore all the subsequent syllables 
        # should be flagged by either deleted or added until we encounter a syllable
        # with a right bracket 
        if "[" in raw_text:
            bracket_state["in_deleted"] = True
        if "<" in raw_text:
            bracket_state["in_added"] = True
        
        if bracket_state["in_deleted"]:
            flags.add("deleted")
        if bracket_state["in_added"]:
            flags.add("added")
        
        if "]" in raw_text:
            bracket_state["in_deleted"] = False
        if ">" in raw_text:
            bracket_state["in_added"] = False
        
        return {
            "text": raw_text,
            "text_clean" : clean_syllable_text(raw_text),
            "data_mac": syll.get("data-mac"),
            "quantity": quantity,
            "quantity_reason": quantity_reason,
            "syll_annotations": sorted(flags),
            "classes_raw": classes, 
        }
    
    def annotation_summary(self, soup):
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

    # collecting data for training the CRF syllabifier
    def build_line_text_and_labels(self, syllables: list[dict]) -> dict:
        """
        Label scheme:
            "B" = first character of a syllable
            "I" = continues the current syllable (includes any sapce emebdded
            insided an elision-merged syllable, , e.g. "δ' ιφ" as ONE unit)
            "O" = a single inserted space between two different words 
        """
        chars, labels = [], []
        for i, syll in enumerate(syllables):
            if i > 0 and syll["word_start"]:
                chars.append(" ")
                labels.append("O")
            text = syll["text_clean"]
            for j, char in enumerate(text):
                chars.append(char)
                labels.append("B" if j == 0 else "I")
        
        return {"line_text": "".join(chars), "char_labels": labels}

    def parse(self, html_content, use_id):
        soup = BeautifulSoup(html_content, "html.parser")
        meta = use_id_to_metadata(use_id)
        bracket_state = {"in_deleted": False, "in_added": False}

        lines = []
        for line_div in soup.select("div.line"):
            syllables = []
            for word_span in line_div.select("span.word"):
                for i, syll in enumerate(word_span.select("span.syll")):
                    parsed = self.parse_syllable(syll, bracket_state)
                    parsed["word_start"] = (i==0)
                    syllables.append(parsed)
                    
            lines.append({
                **self.poem_info(line_div),
                "line_num": self.line_number(line_div),
                "is_incomplete": self.is_incomplete(line_div), 
                "metre": self.metre(line_div),
                "speaker": self.speaker(line_div), 
                "annotated_syllables": syllables, 
                "line_text_and_labels": self.build_line_text_and_labels(syllables)
            })
        
        return{
            "use_id": use_id,
            **meta,
            "line_count": len(lines),
            "annotation_summary": self.annotation_summary(soup),
            "lines": lines
        }
    
    def scrape(self, use_id: str, outdir: str = "scraped_texts", save:bool = True) -> dict:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            try:
                print(f"Fetching {use_id}...")
                html_content = self.fetch_html(page, use_id)
            finally:
                browser.close()
            
        data = self.parse(html_content, use_id)
        print(f" ->{data["line_count"]} lines")
        if save:
            filename = metatdata_to_filename(data)
            out_path = Path(outdir) / f"{filename}.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f" -> saved to {out_path}")

        return data
    
    def scrape_many(self, use_ids: list[str], outdir: str = "scraped_texts"):
        out_path = Path(outdir)
        out_path.mkdir(parents=True, exist_ok=True)

        results = {}
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            try:
                for i, use_id in enumerate(use_ids):
                    print(f"Fetching {use_id}...")
                    html_content = self.fetch_html(page, use_id)
                    data = self.parse(html_content, use_id)
                    print(f" ->{data['line_count']} lines")

                    filename = metatdata_to_filename(data)

                    with open(out_path / f"{filename}.json", "w", encoding = "utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    results[use_id] = data
                    if i < len(use_ids) - 1:
                        time.sleep(self.delay_between)
            finally:
                browser.close()
        print(f"Done. Saved {len(results)} works to {outdir}")

        return results

    def scrape_range(self, prefix: str, start: int, end: int, outdir: str = "scraped_texts"):
        use_ids = use_ids = [f"{prefix}{n}" for n in range(start, end + 1)]
        return self.scrape_many(use_ids)



if __name__ == "__main__":
    scraper = HypotacticScraper()
    
    from texts import TEXTS
    scraper.scrape("HHermes")
    
    

    



    
            

            


    







