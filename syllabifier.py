import unicodedata

from greek_accentuation.syllabify import*

def prepare_syllabify(line):
    all_words = []
    curr_word = []
    for i, char in enumerate(line):
        if not char.isspace():
            
