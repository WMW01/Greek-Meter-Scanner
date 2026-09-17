"""
Debug helper: find real examples of elided syllables on hypotactic.com
and print the raw HTML around them, so we can see exactly how elision
is rendered (full vowel? apostrophe? something else?) instead of guessing.

Usage:
    python inspect_elision.py iliad1 iliad2 iliad3 iliad4 iliad5
"""

import sys

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE_URL = "https://hypotactic.com/latin/index.html?Use_Id={use_id}"


def inspect(use_id: str, max_examples: int = 5):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL.format(use_id=use_id), wait_until="networkidle")
        page.wait_for_timeout(3000)
        html_content = page.content()
        browser.close()

    soup = BeautifulSoup(html_content, "html.parser")
    elided_sylls = soup.select("span.syll.elided")

    print(f"\n=== {use_id}: {len(elided_sylls)} elided syllable(s) found ===")

    for i, syll in enumerate(elided_sylls[:max_examples]):
        word_span = syll.find_parent("span", class_="word")
        line_div = syll.find_parent("div", class_="line")

        print(f"\n--- example {i+1} ---")
        print("syll text:      ", repr(syll.get_text()))
        print("syll classes:   ", syll.get("class"))
        print("syll raw HTML:  ", str(syll))
        if word_span:
            print("word raw HTML:  ", str(word_span))
        if line_div:
            print("line plain text:", line_div.get_text(separator="", strip=True))

    return len(elided_sylls)


if __name__ == "__main__":
    use_ids = sys.argv[1:] or [f"odyssey{n}" for n in range(1, 25)]  # all 24 books by default

    total = 0
    for use_id in use_ids:
        total += inspect(use_id)
        if total >= 5:
            break

    if total == 0:
        print("\nNo elided syllables found in any of the works checked. "
              "Try more/different Use_Ids (elision is common in Latin hexameter, "
              "e.g. 'aeneid1').")
