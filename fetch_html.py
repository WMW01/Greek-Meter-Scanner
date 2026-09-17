from playwright.sync_api import sync_playwright
from scraper import HypotacticScraper

def fetch_an_html(use_id:str, out_filename:str):
    
    scraper = HypotacticScraper()
    with sync_playwright() as p:
        browser = p. chromium.launch(headless = True)
        page = browser.new_page()
        html_content = scraper.fetch_html(page, use_id)
        browser.close()
    
    with open(out_filename, "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    fetch_an_html("dionysiaca1", "dionysiaca1_html")
