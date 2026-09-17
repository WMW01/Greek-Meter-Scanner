import joblib
import crf_syllabifier as cs

bundle = joblib.load("crf_syllabifier.joblib")
line = "μῆνιν ἄειδε θεὰ Πηληϊάδεω Ἀχιλῆος"
line2 = "μηδ᾽ ἐν νάπαισι Πηλίου πεσεῖν ποτε"
print(cs.predict_syllables(bundle, line))
print(cs.predict_syllables(bundle, line2))