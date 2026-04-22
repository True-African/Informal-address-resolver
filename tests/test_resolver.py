import unittest

from resolver import detect_language_mix, normalize_text, resolve


class ResolverTests(unittest.TestCase):
    def test_required_demo_phrase(self):
        result = resolve("inyuma ya big pharmacy on RN3, red gate")
        self.assertIn("lat", result)
        self.assertIn("lon", result)
        self.assertIn("confidence", result)
        self.assertEqual(result["matched_landmark"], "RN3 Big Pharmacy")
        self.assertGreaterEqual(result["confidence"], 0.6)

    def test_french_phrase(self):
        result = resolve("derriere marche de kimironko, portail rouge")
        self.assertEqual(result["matched_landmark"], "Kimironko Market")
        self.assertEqual(result["modifier"], "behind")

    def test_kinyarwanda_phrase(self):
        result = resolve("hafi ya gare ya nyabugogo")
        self.assertEqual(result["matched_landmark"], "Nyabugogo Bus Park")
        self.assertIn("KIN", result["language_signals"])

    def test_empty_input_escalates(self):
        result = resolve("")
        self.assertIsNone(result["matched_landmark"])
        self.assertTrue(result["escalation_required"])
        self.assertEqual(result["confidence"], 0.0)

    def test_unknown_landmark_escalates(self):
        result = resolve("behind the blue mango tree after the unknown hill")
        self.assertTrue(result["escalation_required"])
        self.assertLess(result["confidence"], 0.62)

    def test_confidence_range(self):
        result = resolve("opposite Kigali Convention Centre")
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)

    def test_normalization_removes_accents_and_punctuation(self):
        self.assertEqual(normalize_text("Derriere l'eglise!!!"), "derriere l eglise")

    def test_language_detection(self):
        self.assertIn("FR", detect_language_mix("derriere marche de kimironko"))


if __name__ == "__main__":
    unittest.main()
