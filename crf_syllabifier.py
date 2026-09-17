import glob
import json
import unicodedata
import re
import random
from collections import Counter
from greek_accentuation.syllabify import syllabify
import sklearn_crfsuite
from sklearn_crfsuite import metrics as crf_metrics
from sklearn_crfsuite.trainer import LinePerIterationTrainer


BASE_GREEK_VOWELS = set("αεηιουωΑΣΗΙΟΥΩ")
BASE_GREEK_CONSONANTS = set("βγδζθκλμνξπρσςτφχψΒΓΔΖΘΚΛΜΝΞΠΡΣΤΦΧΨ")
DIPTHONGS = {'αι', 'ει', 'οι', 'υι', 'αυ', 'ευ', 'ου', 'ηυ'}
TREMA_MARK = "\u0308"
ELISION_MARK_CHARS = ELISION_MARK_CHARS = "\u2019\u1FBD\u0027"
ELISION_PATTERN = re.compile(f"([{ELISION_MARK_CHARS}]) ")
# per West,M.L GREEK METER (p.12 "Two or more vowels are slurred together to make one long syllable,
# within the word this is common wehre the first vowel is ε)
epsilon_pairs = {"ε" + vowel for vowel in  "αεηοω"}
alpha_pairs = {"α" + vowel for vowel in "αεωο"}
iota_pairs = {"ι" + vowel for vowel in "οα"} 
omega_pairs = {"ωα"}
omicron_pairs = {"ο" + vowel for vowel in "αεοω"}
eta_pairs = {"η" + vowel for vowel in "αε"}
upsilon_pairs = {"υ" + "οω"}
KNOWN_SYNIZESIS_PAIRS = epsilon_pairs | alpha_pairs | iota_pairs | omega_pairs | omicron_pairs | eta_pairs | upsilon_pairs
KNOWN_SYNECPHONESIS_TRIGGER_WORDS = {"δη", "η", "επει", "μη", "και", "ω", "εγω", "ο", "α", "το", "τα"}
MUTE_LIQUID = {
    "θλ", "θρ", "θμ", "θν",
    "κλ", "κρ", "κμ", "κν",
    "πλ", "πρ", "πν", "πμ",
    "τλ", "τρ", "τν", "τμ",
    "φλ", "φρ", "φν", "φμ",
    "χλ", "χρ", "χν", "χμ",
    "βρ", "γρ", "δρ"
}


def base_letter(char: str) -> str:
    return unicodedata.normalize("NFD", char)[0] if char else ""

def is_vowel(char: str) -> bool: 
    return bool(char) and base_letter(char) in BASE_GREEK_VOWELS

def is_consonant(char: str) -> bool:
    return bool(char) and base_letter(char) in BASE_GREEK_CONSONANTS

def is_elision_mark(char: str) -> bool:
    return char in ELISION_MARK_CHARS

def has_trema(char: str) -> bool:
    decomposed = unicodedata.normalize("NFD", char)
    return TREMA_MARK in decomposed[1:]

def token_has_vowel(token) -> bool:
    return any(is_vowel(char) for char in token)

def is_mute_cum_liquid(first_char: str, second_char: str) -> bool:
    return base_letter(first_char) + base_letter(second_char) in MUTE_LIQUID

def rule_based_labels(line: str) -> list[str]:
    """
    The "syllabify" function in greek_accentuation is designed to syllabify a single
    word accurately, but it cannot correctly deal with elisions of an entire line.
    This function wraps the "syllabify" function, so that it can syllabify an 
    entire sentence with elision-awareness
    """
    # create a list of labels with the same length of the input line
    labels = ["I"] * len(line)
    
    i = 0
    while i < len(line):
        # de-spaced token text
        curr_token_chars = []
        # a list containing the current token's chars' corresponding indices in the original line
        token_orig_idx = [] 
        while i < len(line):
            char = line[i]
            # check whether the current char and its subsequent char is of "<elision mark><whitespace pattern>""
            match = ELISION_PATTERN.match(line, i)
            if match:
                mark_char = match.group(1)
                # if the elision happens within a token that has a vowel(e.g., ἀλλ' ),
                # no forward fusion is needed, add the elision mark to the curr_token_chars
                # advance the index to the subsequent whitespace, so that in the next loop
                # the whitespace can be handled as a regular char
                if token_has_vowel(curr_token_chars):
                    curr_token_chars.append(mark_char)
                    token_orig_idx.append(i)
                    i = match.end(1)
                    continue
                # if due to the elision, the current token becomes a vowel-less
                # remainder, advance the index to the char immediately behind the
                # whitespace, so that the vowels-less consonant and the subsequent 
                # vowel-starting word becomes a single token (stored in curr_token_chars)
                # together.
                else:
                    i = match.end()
                    continue
            
            if char == " ":
                labels[i] = "O"
                i += 1
                break
            curr_token_chars.append(char)
            token_orig_idx.append(i)
            i += 1

        # syllabify the current token
        syllables = syllabify("".join(curr_token_chars))
        syll_b_idx = 0
        for syll in syllables:
            # find the original indices of the beginnings of each syllable in the current token,
            # flip the "I" in the lables-list to "B"
            labels[token_orig_idx[syll_b_idx]] = "B"
            syll_b_idx += len(syll)
    
    return labels

def rule_based_boundary_flags(line: str) -> list[bool]:

    return [label == "B" for label in rule_based_labels(line)]

def distance_to_nearest(line: str, i: int, target:str, direction:int, max_distance: int=6) -> int:
    d = 0
    j = i
    while 0 <= j < len(line) and d < max_distance:
        if line[j] == target:
            return d
        j += direction
        d += 1
    return max_distance

def base_vowel_or_none(char: str) -> str | None:
    """
    Bare (unaccented) vowel letter this character is built on, lowercased or none
    if it is not a vowel at all.
    """
    if not char:
        return None
    base = base_letter(char)
    return base.lower() if base in BASE_GREEK_VOWELS else None

def strip_diacritics(chars: str) -> str:
    decomposed = unicodedata.normalize("NFD", chars.lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != 'Mn')

def synecphonesis_trigger_flags(line: str) -> list[bool]:
    flags = [False] * len(line)
    for i, char in enumerate(line):
        if char != " ":
            continue
        word_start = line.rfind(" ", 0, i) + 1 
        word_before = line[word_start:i] 
        next_char = char_at(line, i + 1)
 
        if strip_diacritics(word_before) in KNOWN_SYNECPHONESIS_TRIGGER_WORDS and is_vowel(next_char):
            flags[i + 1] = True
            continue
        
        next_word_end = line.find(" ", i + 1)
        if next_word_end == -1:
            next_word_end = len(line)
        next_word = strip_diacritics(line[i + 1:next_word_end])

        base_last = base_vowel_or_none(word_before[-1]) if word_before else None
        if len(word_before) >= 2:
            penultimate_base = base_vowel_or_none(word_before[-2])
            ending_pair = (penultimate_base or "") + (base_last or "")
        else: 
            ending_pair = ""

        ends_in_dipthong = ending_pair in DIPTHONGS 
        ends_in_unambiguous_long = base_last in {"η", "ω"}

        if next_word == "εστι" and (ends_in_dipthong or ends_in_unambiguous_long):
            flags[i + 1] = True
        
    return flags 


def is_line_with_deleted_flag(line: dict) -> bool:
    syllables = line.get("annotated_syllables")
    for syllable in syllables:
        syllable_annotations = syllable.get("syll_annotations")
        if "deleted" in syllable_annotations:
            print(line.get("line_num"))
            return True
    
    return False

def load_lines_from_json(paths) -> list[dict]:
    """
    paths: a list of file paths, or a glob pattern string (e.g. "scraped_texts/*")
    returns a flat list of {"line":..., "char_labels": [...]} dicts
    """
    if isinstance(paths, str):
        paths = glob.glob(paths)

    examples = []
    skipped = 0
    for path in paths:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            for line in data["lines"]:
                line_text_and_labels = line.get("line_text_and_labels")
                line_text = line_text_and_labels.get("line_text")
                # skip lines that are empty, incomplete or spurious(indicated by the class flag "deleted" in the html files)
                if not line_text or line.get("is_incomplete") or is_line_with_deleted_flag(line):
                    skipped += 1
                    continue
                examples.append({
                    "line": line_text_and_labels["line_text"],
                    "labels": line_text_and_labels["char_labels"]
                })

    print(f"loaded {len(examples)} examples and skipped {skipped} lines")
    return examples 

def char_at(line: str, i:int) -> str:
    return line[i] if 0 <= i < len(line) else ""


def char_features(
    line: str, 
    i:int, 
    rule_boundaries: list[bool] | None = None, 
    synecphonesis_triggers: list[bool] | None = None):

    char = line[i]
    prev1, next1 = char_at(line, i-1), char_at(line, i+1)
    prev2, next2 = char_at(line, i-2), char_at(line, i+2)

    base_this = base_vowel_or_none(char)
    base_next = base_vowel_or_none(next1)
    base_prev = base_vowel_or_none(prev1)
    base_next2 = base_vowel_or_none(next2)
    base_prev2 = base_vowel_or_none(prev2)

    vowel_pair_with_next = bool(base_this and base_next)
    vowel_pair_with_prev = bool(base_this and base_prev)

    cross_word_vowel_next = bool(base_this and next1 == " " and base_next2)
    cross_word_vowel_prev = bool(base_this and prev1 == " " and base_prev2)

    is_mute_cum_liquid_prev = is_mute_cum_liquid(prev1, char)
    is_mute_cum_liquid_next = is_mute_cum_liquid(char, next1)
    is_non_liquid_cluster_prev = is_consonant(prev1) and is_consonant(char) and not is_mute_cum_liquid_prev
    is_non_liquid_cluster_next = is_consonant(char) and is_consonant(next1) and not is_mute_cum_liquid_next

    features = {
        "char": char,
        "char.lower": char.lower(),
        "is_vowel": is_vowel(char),
        "is_consonant": is_consonant(char),
        "is_space": char == " ",
        "has_trema": has_trema(char),
        "next1.has_trema": has_trema(next1) if next1 else False,
        "is_elision_mark": is_elision_mark(char),
        "prev1.is_elision_mark": is_elision_mark(prev1) if prev1 else False,
        "next1.is_elision_mark": is_elision_mark(next1) if next1 else False,
        "is_mute_cum_liquid_prev": is_mute_cum_liquid_prev,
        "is_non_liquid_cluster_prev": is_non_liquid_cluster_prev,
        "is_first": i == 0,
        "is_last": i == len(line) - 1,

        "prev1": prev1,
        "next1": next1,
        "prev1.is_vowel": is_vowel(prev1),
        "next1.is_vowel": is_vowel(next1),
        "prev1.is_space": prev1 == " ",
        "next1.is_space": next1 == " ",

        "prev2": prev2,
        "next2": next2,

        "bigram_prev": prev1 + char,
        "bigram_next": char + next1,

        "is_dipthong_with_prev": (prev1 + char).lower() in DIPTHONGS,
        "is_dipthong_with_next": (char + next1).lower() in DIPTHONGS,
        "is_known_synizesis_pair_prev": ((base_prev or "") + (base_this or "")) in KNOWN_SYNIZESIS_PAIRS,
        "is_known_synizesis_pair_next": ((base_this or "") + (base_next or "")) in KNOWN_SYNIZESIS_PAIRS,
    }

    if synecphonesis_triggers is not None:
        features["synecphonesis_trigger"] = synecphonesis_triggers[i]
        # synizesis relevant signals
        # Any vowel-vowel adjacency (not just dipthongs) is a candidate point for 
        # merging/ The specific pair identity lets the CRF learn per-pair 
        # tendencies (e.g. εω is more likely to merge than other non-dipthong pairs)

    features.update({
            "vowel_pair_with_next": vowel_pair_with_next,
            "vowel_pair_with_prev": vowel_pair_with_prev,
            "vowel_pair_bigram_next": (base_this + base_next) if vowel_pair_with_next else "",
            "vowel_pair-bigram_prev": (base_prev + base_this) if vowel_pair_with_prev else "", 

            "cross_word_vowel_next": cross_word_vowel_next,
            "cross_word_vowel_prev": cross_word_vowel_prev, 
            "cross_word_vowel_bigram_next": (base_this + base_next) if vowel_pair_with_next else "",
            "cross_word_vowel_bigram_prev": (base_prev2 + base_this) if cross_word_vowel_prev else "",

            # εω usually indicates genetive forms, thus nearing the end of a word
            "distance_to_next_space": distance_to_nearest(line, i, " ", +1),
    })
    

    if rule_boundaries is not None:
        features["rule_says_boundary"] = rule_boundaries[i]
        features["prev1.rule_syas_boundary"] = rule_boundaries[i-1] if i > 0 else False
        features["next1.rule_says_boundary"] = rule_boundaries[i+1] if i + 1 < len(line) else False

        features["rule_and_mute_prev"] = f"{rule_boundaries[i]}_{is_mute_cum_liquid_prev}"
    
        features["rule_and_synizesis_prev"] = f"{rule_boundaries[i]}_{synecphonesis_triggers[i]}"

    if synecphonesis_triggers is not None:
        features["rule_and_sync"] = f"{rule_boundaries[i]}_{synecphonesis_triggers[i]}"

    return features

def build_vowel_pair_lexicon(examples: list[dict]) -> dict:
    merge_counts = Counter()
    total_counts = Counter()

    for example in examples:
        line, labels = example["line"], example["labels"]
        for i in range(len(line) - 1):
            vowel1 = base_vowel_or_none(line[i])
            vowel2 = base_vowel_or_none(line[i + 1])
            if vowel1 and vowel2:
                pair = vowel1 + vowel2
                total_counts[pair] += 1
                if labels[i + 1] == "I":
                    merge_counts[pair] += 1

    return {pair: merge_counts[pair] / total_counts[pair] for pair in total_counts}

def line_to_features(line: str) -> list[dict]:
    rule_boundaries = rule_based_boundary_flags(line)
    synecphonesis_triggers = synecphonesis_trigger_flags(line)
    return [char_features(line, i, rule_boundaries, synecphonesis_triggers) for i in range(len(line))]

def build_features_and_labels_safe(examples: list[dict], split_name: train):
    X, Y = [], []
    skipped = 0
    for example in examples: 
        try: 
            X.append(line_to_features(example["line"]))
            Y.append(example["labels"])
        except Exception as e:
            skipped += 1
            print(f"Warning: skipping {split_name} line ({type(e).__name__}: {e}) -- {example["line"]}")
    return X, Y
    
def train(
        examples: list[dict],
        test_fraction: float = 0.10,
        val_fraction: float = 0.10,
        seed: int = 42,
        **crf_kwargs,
):
    rng = random.Random(seed)
    shuffled = examples[:]
    rng.shuffle(shuffled)

    n_test = max(1, int(len(shuffled) * test_fraction))
    n_val = max(1, int(len(shuffled) * val_fraction))

    test_set = shuffled[:n_test]
    val_set = shuffled[n_test:n_test + n_val]
    train_set = shuffled[n_test + n_val:]

    X_train, Y_train = build_features_and_labels_safe(train_set, "train")
    X_val, Y_val = build_features_and_labels_safe(val_set, "validation")
    X_test, Y_test = build_features_and_labels_safe(test_set, "test")


    default_kwargs = dict(
        algorithm="lbfgs",
        c1=0.01,
        c2=0.01,
        max_iterations = 100,
        verbose = True,
        trainer_cls = LinePerIterationTrainer, 
        all_possible_transitions = True, 
    )
    default_kwargs.update(crf_kwargs)

    model = sklearn_crfsuite.CRF(**default_kwargs)
    print(f"Training on {len(X_train)} lines, evaluating on {len(X_test)} held-out lines...")
    model.fit(X_train, Y_train, X_dev=X_val, y_dev=Y_val)

    train_line_accuracy = None
    if X_train:
        y_pred_train = model.predict(X_train)
        exact_line_matches_train = sum(1 for yt, yp in zip(Y_train, y_pred_train) if list(yt) == list(yp))
        train_line_accuracy = exact_line_matches_train / len(Y_train)
        print(f"Lines with 1--% correct char labels (TRAINING set): {exact_line_matches_train} / {len(Y_train)}  "
              f"({train_line_accuracy:.1%})")

    if X_test:
        Y_pred = model.predict(X_test)
        labels = ["B", "I", "O"]
        report = crf_metrics.flat_classification_report(Y_test, Y_pred, labels=labels, digits=3)
        print(report)

        exact_line_matches = sum(1 for yt, yp in zip(Y_test, Y_pred) if list(yt) == list(yp))
        print(f"Lines with 100% correct char labels (TEST set): {exact_line_matches}/len{len(Y_test)}  "
              f"({exact_line_matches / len(Y_test):.1%})")
        
    return {"model": model, "test_set": test_set}

def predict_labels(bundle: dict, line:str) -> list[str]:
    features = line_to_features(line)
    return bundle["model"].predict_single(features)

def labels_to_syllables(line: str, labels: list[str]) -> list[str]:
    """Convert a (line, labels) pair back into a list of syllable strings"""
    syllables = []
    current = ""
    for char, label in zip(line, labels):
        if label == "O":
            if current:
                syllables.append(current)
                current = ""
            continue
        if label == "B" and current:
            syllables.append(current)
            current = char 
        else:
            current += char
    if current:
        syllables.append(current)
    
    return syllables 

def predict_syllables(bundle: dict, line: str) -> list[str]:
    labels = predict_labels(bundle, line)
    return labels_to_syllables(line, labels)

# --------------------
# Save/load
# --------------------

def save_model(bundle: dict, path: str = "crf_syllabifier.joblib"):
    import joblib
    joblib.dump(bundle, path)
    print(f"saved model to {path}")

def load_model(path: str = "crf_syllabifier.joblib") -> dict:
    import joblib
    return joblib.load(path)


if __name__ == "__main__":
    # examples = load_lines_from_json("scraped_texts_fixed/*.json")
    # count = 0
    # for idx, ex in enumerate(examples):
    #     try:
    #         line_to_features(ex["line"])
    #     except IndexError as e:
    #         count += 1
    #         print(f"CRASH at example {idx}: {ex['line']!r}")
    #         print(f"  error: {e}")
    #         continue  # stop at the first one so you can inspect it
    
    # # print(count)
    examples = load_lines_from_json("scraped_texts_fixed/*json")

    bundle = train(examples)
    save_model(bundle)

    sample_text = examples[0]["line"]
    print("Sample line:", sample_text)
    print("Predicted syllables:", predict_syllables(bundle, sample_text))
    print("Actual syllables: ", labels_to_syllables(sample_text, examples[0]["labels"]))




    