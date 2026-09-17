from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from texts import TEXTS
BASE_URL = "https://hypotactic.com/latin/index.html?Use_Id={use_id}"

def validate_one(use_id: str) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL.format(use_id=use_id), wait_until="networkidle")
        page.wait_for_timeout(3000)
        html_content = page.content()
        browser.close()
    
    soup = BeautifulSoup(html_content, "html.parser")
    line_count = len(soup.select("div.line"))
    syll_count = len(soup.select("div.syll"))

    return {
        "use_id": use_id,
        "line_count": line_count,
        "syll_count": syll_count,
        "ok": line_count > 0 and syll_count > 0, 
    }

if __name__ == "__main__":
    print(f"Checking {len(TEXTS)} Use_Ids from texts.py..\n")

    results = [validate_one(uid) for uid in TEXTS]

    bad = [r for r in results if not r["ok"]]
    good = [r for r in results if r["ok"]]

    for r in bad:
        print("Likely typos:", [r["use_id"] for r in bad])

    