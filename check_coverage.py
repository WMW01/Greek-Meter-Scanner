"""
Simple check: does this text have Chamberlain's richer annotation set
(lbn/lbp/bil/hiatus/synizesis/correption/etc. + macrons), or just the
basic long/short/resolved/elided?

Usage:
    python check_coverage.py iliad1 odyssey1 pindar_something
"""

import sys

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE_URL = "https://hypotactic.com/latin/index.html?Use_Id={use_id}"

RICH_MARKERS = {
    "lbn", "lbp", "bil", "hiatus", "synizesis",
    "correption", "mcl", "diastole", "preliquid", "pre-dw",
}


def check(use_id: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL.format(use_id=use_id), wait_until="networkidle")
        page.wait_for_timeout(3000)
        html_content = page.content()
        browser.close()

    soup = BeautifulSoup(html_content, "html.parser")
    sylls = soup.select("span.syll")

    all_classes = set()
    for syll in sylls:
        all_classes.update(syll.get("class", []))

    present_rich = sorted(RICH_MARKERS & all_classes)
    has_macrons = any(s.get("data-mac") for s in sylls)

    print(f"{use_id}: {len(sylls)} syllables")
    print(f"  Rich markers present: {present_rich or 'NONE'}")
    print(f"  Has macrons: {has_macrons}")


if __name__ == "__main__":
    use_ids = sys.argv[1:] or ["iliad1"]
    for use_id in use_ids:
        check(use_id)









