import joblib
import crf_syllabifier as cs

bundle = joblib.load("crf_syllabifier.joblib")
test_set = bundle["test_set"]

correct_lines = 0
correct_chars = 0
total_chars = 0

for ex in test_set:
    true_labels = ex["labels"]
    predicted_labels = cs.rule_based_labels(ex["line"])

    if true_labels == predicted_labels:
        correct_lines += 1

    
    for p, t in zip(predicted_labels, true_labels):
        total_chars += 1
        if p == t:
            correct_chars += 1

total_lines = len(test_set)
print(f"the percentage of lines that are 100% correct is {correct_lines / total_lines}")
print(f"the accuracy of chars is: {correct_chars / total_chars }")