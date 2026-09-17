import joblib
from collections import Counter

bundle = joblib.load("crf_syllabifier.joblib")
model = bundle["model"]

print("=== Loss every 10 iternations ===")
for iter in model.training_log_.iterations:
    if iter["num"] == 1 or iter["num"] % 10 == 0:
        print(f"iter {iter["num"]} loss={iter["loss"]:.4f}"
              f"active_features={iter["active_features"]}"
              f"error_norm={iter["error_norm"]:.4f}")

print("=== Sample of state_features_(feature, label) -> weight ===")
for (attr, label), weight in list(model.state_features_.items())[:5]:
    print(f"  ({attr!r}, {label!r} -> {weight})")
print(f"  (total state features: {len(model.state_features_)})")
print()

print("=== transitions_features_ (from_label, to_label) -> weight ===")
for (from_label, to_label), weight in model.transition_features_.items():
    print(f"  {from_label} -> {to_label}: {weight}")
print()

print("==== features that are ambiguous ====")
features_weights = Counter()
for (attr, label), weight in model.state_features_.items():
    if weight < 0.85:
        features_weights[(attr, label)] = weight
print(f"the number of ambiguous features are: {len(features_weights)}")

print("=== Targeted lookups: purpose-built features ===")
features_of_interest = [
    "rule_says_boundary",
    "is_known_synizesis_pair_prev",
    "is_mute_cum_liquid_prev",
    "is_non_liquid_cluster_prev",
    "synecphonesis_trigger",
    "rule_and_synec",
    "rule_and_synizesis_prev",
    "rule_and_mute_prev",
]

for feat_name in features_of_interest:
    print(f"   {feat_name}:")
    found_any = False
    for (feat, label), weight in model.state_features_.items():
        if feat == feat_name or feat.startswith(feat_name + ":"):
            print(f"   ({feat!r}, {label!r} -> {weight})")
            found_any = True
    
    if not found_any:
        print("feature is not found")
    
    print()

print("=== Top 15 features by absolute weight ===")
top = sorted(model.state_features_.items(), key=lambda kv: abs(kv[1]), reverse=True)[:15]
for (feat, label), weight in top:
    print(f"   ({feat!r}, {label!r}) -> {weight}")

