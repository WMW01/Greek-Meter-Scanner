"""
Central list of hypotactic.com Use_Ids. Edit this file to add/remove texts
so that check_coverage.py, hypotactic_scraper.py etc can just import TEXTS from
here instead of retyping the list
""" 
TEXTS = [
    *["persians", "prometheus", "seven"], # Aeschylus
    *["apollonius1", "apollonius2", "apollonius3", "apollonius4"], # Apollonius of Rhodes Argonautica 1
    "aratus",
    "bion",
    *["callimachusHymns", "callimachusEp"], # Callimachus Hymns, Epigrams
    "cleanthes",
    "colluthus", 
    *["theogony", "worksanddays", "scutum"], #Hesiod
    *[f"iliad{n}" for n in range(1, 25)],
    *[f"odyssey{n}" for n in range(1, 25)],
    *[F"HH{title}" for title in ["Demeter", "Aphrodite", "Apollo", "Hermes"]], # The Homeric Hymns
    "lychophron",
    "moschus",
    "nicander",
    *[f"dionysiaca{n}" for n in range(1, 49)], #Nonnus
    *["opcyn", "ophal"] ,
    *["olympians", "pythians", "nemeans", "isthmians"], #Pindar
    *[f"qsmyrnaeus{n}" for n in range(1, 15)], #Quintus Smyrnaeus
    "semonides",
    "solon",
    *[f"theoc{n}" for n in range(1, 5)], #Theocritus
    "theognis",
    "tryph", #Tryphiodorus
    "tyrtaeus", 
]


