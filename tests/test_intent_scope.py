import unittest

import pandas as pd

from intent_scope import INITIAL_INTENTS, prepare_training_data


class IntentScopeTests(unittest.TestCase):
    def test_only_the_five_approved_intents_are_kept(self):
        frame = pd.DataFrame([
            {"user_message": "Add this product to my cart", "actual_intent": "add_to_cart"},
            {"user_message": "Show my orders", "actual_intent": "show_orders"},
            {"user_message": "Hello", "actual_intent": "greeting"},
        ])

        cleaned, report = prepare_training_data(frame)

        self.assertEqual(set(cleaned["training_intent"]), {
            "add_to_cart", "show_orders"
        })
        self.assertEqual(report["rows_fetched"], 3)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(len(INITIAL_INTENTS), 5)

    def test_case_and_whitespace_duplicates_are_removed(self):
        frame = pd.DataFrame([
            {"user_message": " Add this product to my cart ", "actual_intent": "add_to_cart"},
            {"user_message": "add   this product to my cart", "actual_intent": "add_to_cart"},
        ])

        cleaned, report = prepare_training_data(frame)

        self.assertEqual(len(cleaned), 1)
        self.assertEqual(report["duplicate_rows_removed"], 1)
        self.assertEqual(
            cleaned.iloc[0]["user_message"],
            "add this product to my cart",
        )

    def test_conflicting_duplicate_labels_are_rejected(self):
        frame = pd.DataFrame([
            {"user_message": "check my order", "actual_intent": "show_orders"},
            {"user_message": " CHECK   MY ORDER ", "actual_intent": "track_order"},
        ])

        with self.assertRaisesRegex(ValueError, "Conflicting human-reviewed labels"):
            prepare_training_data(frame)

    def test_blank_messages_and_out_of_scope_intents_are_excluded(self):
        frame = pd.DataFrame([
            {"user_message": "   ", "actual_intent": "add_to_cart"},
            {"user_message": "Hello", "actual_intent": "greeting"},
            {"user_message": "Show my cart", "actual_intent": "view_cart"},
        ])

        cleaned, _ = prepare_training_data(frame)

        self.assertEqual(cleaned["training_intent"].tolist(), ["view_cart"])


if __name__ == "__main__":
    unittest.main()
