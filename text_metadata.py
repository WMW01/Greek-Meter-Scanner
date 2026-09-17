import re

USE_ID_NUMBERED_PATTERNS = [
    #(regex, author, work)
    (r"^iliad(\d+)$", "Homer", "Iliad"),
    (r"^odyssey(\d+)$", "Homer", "Odyssey"),
    (r"^apollonius(\d+)$", "Apollonius Rhodius", "Argonautica"),
    (r"^dionysiaca(\d+)$", "Nonnus", "Dionysiaca"),
    (r"^qsmyrnaeus(\d+)$", "Quintus Smyrnaeus", "Posthomerica"),
]

USE_ID_HH_PATTERN = r"^HH(\w+)$" # e.g. "HHDemeter" -> Homeric Hymn to Demeter

USE_ID_AUTHOR_WORK = {
    # Aeschylus
    "persians": ("Aeschylus", "Persians"),
    "prometheus": ("Aeschylus", "Prometheus Bound"),
    "seven": ("Aeschylus", "Seven Against Thebes"),
    # Callimachus
    "callimachusHymns": ("Callimachus", "Hymns"),
    "callimachusEp": ("Callimachus", "Epigrams"),
    # Hesiod
    "theogony": ("Hesiod", "Theogony"),
    "worksanddays": ("Hesiod", "Works and Days"),
    "scutum": ("Hesiod", "Shield of Heracles"),
    # Pindar
    "olympians": ("Pindar", "Olympian Odes"),
    "pythians": ("Pindar", "Pythian Odes"),
    "nemeans": ("Pindar", "Nemean Odes"),
    "isthmians": ("Pindar", "Isthmian Odes"),
    # Theocritus
    "theocIdylls": ("Theocritus", "Idylls"),
    "theocEpigrams": ("Theocitus", "Epigrams"),
    # Single/fragmentary-work authors 
    "aratus": ("Aratus", None),
    "bion": ("Bion", None),
    "cleanthes": ("Cleanthes", None),
    "colluthus": ("Colluthus", "Rape of Helen"),
    "lycophron": ("Lycophron", "Alexandra"),
    "moschus": ("Moschus", None),
    "nicander": ("Nicander", None),
    "opcyn": ("Oppian", "Cynegetica"),   
    "ophal": ("Oppian", "Halieutica"),  
    "semonides": ("Semonides", None),
    "solon": ("Solon", None),
    "theognis": ("Theognis", "Elegies"),
    "tryph": ("Tryphiodorus", "Sack of Troy"),
    "tyrtaeus": ("Tyrtaeus", None),
    "batumumach": (None, None), 
}

def use_id_to_metadata(use_id: str) -> dict:
    for pattern, author, work in USE_ID_NUMBERED_PATTERNS:
        match = re.match(pattern, use_id)
        if match:
            return {"author": author, "work": work, "book": int(match.group(1))}
        
    
    match = re.match(USE_ID_HH_PATTERN, use_id)
    if match:
        return {"author": None, "work": f"Homeric Hymn to {match.group(1)}", "book": None}

    if use_id in USE_ID_AUTHOR_WORK:
        author, work = USE_ID_AUTHOR_WORK[use_id]
        return {"author": author, "work": work, "book": None}

    return {"author": None, "work": None, "book": None} # unrecognized pattern

def lower_underscore(s: str) -> str:
    """lower the letter cases and replace whitespaces with underscores for filenames"""
    s = s.strip().lower()
    s = re.sub(r"\s+", "_", s)
    return s

def metatdata_to_filename(data: dict):
    parts = []
    if data.get("author"):
        parts.append(lower_underscore(data["author"]))
    if data.get("work"):
        parts.append(lower_underscore(data["work"]))
    if data.get("book") is not None:
        parts.append(str(data["book"]).zfill(2))

    return "_".join(parts)








