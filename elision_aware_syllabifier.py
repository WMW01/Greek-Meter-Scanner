import re
import unicodedata
from greek_accentuation.syllabify import*

LENGTH_MARK_CHARS = "\u0304\u0306"
ELISION_MARK_CHARS = "\u2019\u1FBD\u0027"
ELISION_PATTERN = re.compile(f"([{ELISION_MARK_CHARS}]) ") #possible elision mark immediately followed by a whitespace
BASE_GREEK_VOWELS = set("αεηιουωΑΣΗΙΟΥΩ")

def base_letter(char):
    return unicodedata.normalize("NFD", char)[0] if char else ""

def is_vowel(char):
    return bool(char) and base_letter(char) in BASE_GREEK_VOWELS

def word_has_vowel(word:list[str]) -> bool:
    return any(is_vowel(char) for char in word)

def strippable_punctuation(char:str) -> bool:
    if char in LENGTH_MARK_CHARS:
        return True
    if char in ELISION_MARK_CHARS:
        return False
    category = unicodedata.category(char)
    return category.startswith("P")

def strip_non_elision_punctuations(line:str):
    decomposed = unicodedata.normalize("NFD", line)
    decomposed = "".join(char for char in decomposed if not strippable_punctuation(char))
    return unicodedata.normalize("NFC", decomposed)

def merge_elisions(line:str) -> tuple[str, list[str]]:
    """
    Remove all the "<elision><whitespace>" occurences in a line WHERE the only vowel(s) 
    of a word is elided, making it necessary for the bare, vowel-less remainder like δ᾽to
    fuse foward. Words like ἀλλ’ are left untouched. 
    Return a string where the "<elision><whitespace>" occurences are 
    removed as necessary (e.g., δ’ ἐτελείετο becomes δἐτελείετο), as well a list indicating the 
    indices of the elision marks against the merged string
    """
    merged_chars = []
    mark_positions = []
    curr_word_chars = [] # chars accumulated since the last real word-seperator space
    
    i = 0
    while i < len(line):
        match = ELISION_PATTERN.match(line, i)
        if match:
            # if there is a match but the current word itself has a vowel
            if word_has_vowel(curr_word_chars):
                # add the elision mark onto the curr_word_chars-list
                mark_char = match.group(1)
                merged_chars.append(mark_char)
                curr_word_chars.append(mark_char)
                # move the index to that of the whitespace in the pattern, so that
                # in the next loop, the whitespace get added to merged_chars, and 
                # curr_word_chars gets gets reset to empty
                i = match.end(1)
                continue
            else:
                print({f"the current i is: {i}"})
                print(f"the number of matches we found so far is: {len(match.groups())}")
                # if the current word does not have a vowel(the bare, vowel-less remainder senario)
                # mark the index of the elision-mark against the merged_chars-list
                mark_positions.append(len(merged_chars))
                # fuse the vowel-less remainder with the next word coming up
                curr_word_chars = []
                i = match.end()
                print(f"the position of the first letter after a <elision><space> is: {i}")
                continue

        char = line[i]
        if char == " ":
            curr_word_chars = []
        else:
            curr_word_chars.append(char)

        merged_chars.append(char)
        i += 1
    print(f"the merged_chars for the special sentence is: {"".join(merged_chars)}")
    print(f"the mark_positions are: {mark_positions}")
    return "".join(merged_chars), mark_positions

def reinsert_elision_marks(syllables:list[list[str]], word_starts: list[int], mark_positions:list[int]) -> list[str]:

    # make a new copy of the syllables list, so that the original list remains unchanged and informs of mark postions,
    # while the new list get muted with elision mark reinserted
    result = [list(sylls) for sylls in syllables]
    for pos in mark_positions:
        # find the word where the position falls in, and calculate the offset betwee
        # the start of the word and the original elision mark
        for w_idx, w_start in enumerate(word_starts):
            word_length = sum(len(syll) for syll in syllables[w_idx])
            end = w_start + word_length
            if w_start <= pos < end:
                offset = pos - w_start
                # find the syllable where the position falls 
                running = 0
                for s_idx, syll in enumerate(result[w_idx]):
                    if running <= offset < running + len(syll):
                        elision_pos = offset - running
                        result[w_idx][s_idx] = syll[:elision_pos] + "\u2019" + syll[elision_pos:]
                        break
                    running += len(syll)
                break
    return result
        
def elision_aware_syllabify_line(line: str):
    line = strip_non_elision_punctuations(line)
    print(line)
    print(len(line))
    merged_chars, mark_positions = merge_elisions(line)

    words = merged_chars.split()
    word_starts = []
    pos = 0
    for word in words:
        word_starts.append(pos)
        pos += len(word) + 1 #matching with merged string where a new words starts after a whitespace

    syllables = [syllabify(word) for word in words]
    syllables = reinsert_elision_marks(syllables, word_starts, mark_positions)
    return syllables

def build_labels(syllables:list[list[str]]):
    labels=[]
    for w_idx, word in enumerate(syllables):
        for s_idx, syll in enumerate(word):
            for c_idx in range(len(syll)):
                if c_idx == 0:
                    labels.append("B")
                else: 
                    labels.append("I")
            if s_idx == len(word) - 1 and w_idx < len(syllables) - 1:
                labels.append("0")
    return labels

if __name__ == "__main__":
    line = "παῖδα δ’ ἐμοὶ λῡ́σαιτε φίλην, τὰ δ’ ἄποινα δέχεσθαι, "
    result = elision_aware_syllabify_line(line)
    #labels = build_labels(result)
    print(result)
    #print(labels)
    #print(len(labels))
    line1 = "ἔκλαγξαν δ’ ἄρ’ ὀϊστοὶ ἐπ’ ὤμων χωομένοιο,"
    result1 = elision_aware_syllabify_line(line1)
    #labels = build_labels(result1)
    print(result1)
    #print(syllabify("αἰείτοιτὰκάκἐστὶφίλαφρεσὶμαντεύεσθαι"))

    
