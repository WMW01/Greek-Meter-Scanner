from bs4 import BeautifulSoup

with open("iliad1.html", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

candidates = ["\u1FBD", "\u2019", "'"]  # koronis, right single quote, plain apostrophe

for syll in soup.select("span.syll"):
    text = syll.get_text()
    if any(c in text for c in candidates):
        print(repr(text), syll.get("class"))