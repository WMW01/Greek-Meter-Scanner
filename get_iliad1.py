from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import unicodedata

url = "https://hypotactic.com/latin/index.html?Use_Id=iliad1"

print("Fetching Iliad 1...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # Load the page and wait for general DOM rendering
    page.goto(url, wait_until="networkidle")
    
    # Give client JavaScript 3 seconds to construct elements
    page.wait_for_timeout(3000)
    
    html_content = page.content()
    browser.close()


# Inspect retrieved HTML using BeautifulSoup
soup = BeautifulSoup(html_content, "html.parser")

with open("iliad1.html", "w", encoding="utf-8") as f:
    f.write(soup.prettify())

# Target meter tags, verse lines, or row containers
verses = soup.find_all(class_="verse") or soup.find_all("tr")

print(f"Saved iliad1.html successfully! Found {len(verses)} rows/lines.")
if verses:
    print("\nFirst row preview:")
    print(verses[0].get_text(separator=" ", strip=True))

LENGH_MARKS = {
    "\u0304", #combining macron 
    "\u0306", # combining breve 
}

def strip_length_marks(text: str) -> str:
    # Decompose so macron/breve become separate combining characters,
    # remove them, then recompose the rest(accents, breathing, etc.)
    decomposed = unicodedata.normalize("NFD", text)
    cleaned = "".join(ch for ch in decomposed if ch not in LENGH_MARKS)
    return unicodedata.normalize("NFC", cleaned)