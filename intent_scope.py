"""Canonical first-phase intent scope for the Assistant ML classifier.

The application may continue to support other rule-based intents. This allowlist
controls only the first supervised ML model.
"""

import re

import pandas as pd


INITIAL_INTENTS = (
    "add_to_cart",
    "view_cart",
    "show_orders",
    "track_order",
    "cancel_order",
)

MINIMUM_UNIQUE_EXAMPLES_PER_INTENT = 10
MINIMUM_ACCURACY = 0.70
TEST_SIZE = 0.20
RANDOM_STATE = 42


def normalize_message(value):
    """Normalize case and whitespace for duplicate/leakage detection."""
    return re.sub(r"\s+", " ", str(value or "").casefold()).strip()


def prepare_training_data(frame):
    """Return deduplicated, in-scope rows and a compact quality report.

    Only human-reviewed actual_intent values are accepted. A normalized message
    with conflicting labels is rejected instead of being silently assigned one.
    """
    required_columns = {"user_message", "actual_intent"}
    missing_columns = required_columns.difference(frame.columns)
    if missing_columns:
        raise ValueError(
            "Training data is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    data = frame.copy()
    rows_fetched = len(data)

    data = data.dropna(subset=["user_message", "actual_intent"]).copy()
    data["user_message"] = data["user_message"].astype(str).str.strip()
    data["actual_intent"] = (
        data["actual_intent"].astype(str).str.strip().str.casefold()
    )
    data["normalized_message"] = data["user_message"].map(normalize_message)

    data = data[
        (data["normalized_message"] != "")
        & data["actual_intent"].isin(INITIAL_INTENTS)
    ].copy()

    conflict_counts = (
        data.groupby("normalized_message")["actual_intent"].nunique()
    )
    conflicts = conflict_counts[conflict_counts > 1]
    if not conflicts.empty:
        examples = []
        for message in conflicts.index[:5]:
            labels = sorted(
                data.loc[
                    data["normalized_message"] == message, "actual_intent"
                ].unique().tolist()
            )
            examples.append(f"{message!r}: {labels}")
        raise ValueError(
            "Conflicting human-reviewed labels for normalized messages: "
            + "; ".join(examples)
        )

    before_deduplication = len(data)
    data = data.drop_duplicates(
        subset=["normalized_message"], keep="first"
    ).reset_index(drop=True)
    duplicate_rows_removed = before_deduplication - len(data)

    # Use the normalized text as the model input so casing/whitespace variants
    # cannot be split into separate train/test examples.
    data["user_message"] = data["normalized_message"]
    data["training_intent"] = data["actual_intent"]

    counts = {
        intent: int(data["training_intent"].eq(intent).sum())
        for intent in INITIAL_INTENTS
    }

    report = {
        "rows_fetched": rows_fetched,
        "in_scope_rows_before_deduplication": before_deduplication,
        "unique_rows_after_deduplication": len(data),
        "duplicate_rows_removed": duplicate_rows_removed,
        "unique_messages_per_intent": counts,
    }

    return data[["user_message", "actual_intent", "training_intent"]], report
