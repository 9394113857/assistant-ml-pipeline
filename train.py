import os
import sys

import joblib
import pandas as pd
from sqlalchemy import create_engine, event, text

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from intent_scope import (
    INITIAL_INTENTS,
    MINIMUM_ACCURACY,
    MINIMUM_UNIQUE_EXAMPLES_PER_INTENT,
    RANDOM_STATE,
    TEST_SIZE,
    prepare_training_data,
)


TABLE_NAME = "public.assistant_training_logs"
MODEL_PATH = "models/assistant_intent_model.pkl"
MINIMUM_RECORDS = (
    MINIMUM_UNIQUE_EXAMPLES_PER_INTENT * len(INITIAL_INTENTS)
)

# A lack of enough approved data or a rejected quality score is an expected
# training gate, not a broken workflow. These statuses leave the old model
# untouched and allow GitHub Actions to report a successful "skipped" run.
NON_ERROR_STATUSES = {"INSUFFICIENT_DATA", "QUALITY_REJECTED"}

training_rows = 0
model_accuracy = "N/A"


def stop_training(message, status="FAILED"):
    print("\n" + "=" * 60)
    print(f"TRAINING STATUS: {status}")
    print(f"REASON: {message}")
    print("=" * 60)
    print(f"TRAINING_STATUS={status}")
    print(f"TRAINING_ROWS={training_rows}")
    print(f"MODEL_ACCURACY={model_accuracy}")
    print("MODEL_SAVED=false")
    print(f"MODEL_PATH={MODEL_PATH}")
    sys.exit(0 if status in NON_ERROR_STATUSES else 1)


def create_read_only_engine(database_url):
    """Create a PostgreSQL engine that cannot write to Supabase."""
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={
            "options": "-c default_transaction_read_only=on"
        },
    )

    @event.listens_for(engine, "connect")
    def verify_read_only_connection(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SHOW transaction_read_only")
            mode = cursor.fetchone()[0]
            if mode != "on":
                raise RuntimeError(
                    "PostgreSQL did not confirm a read-only connection."
                )
        finally:
            cursor.close()
            dbapi_connection.rollback()

    return engine


def main():
    global training_rows, model_accuracy

    print("\n" + "=" * 60)
    print("ASSISTANT ML — FIRST FIVE INTENTS")
    print("=" * 60)
    print("Allowed intents: " + ", ".join(INITIAL_INTENTS))
    print(
        "Minimum unique examples per intent: "
        f"{MINIMUM_UNIQUE_EXAMPLES_PER_INTENT}"
    )
    print(f"Minimum total unique examples: {MINIMUM_RECORDS}")
    print(f"Minimum accuracy: {MINIMUM_ACCURACY:.0%}")
    print(f"Model output: {MODEL_PATH}")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        stop_training("DATABASE_URL secret is missing.")

    # The SQL allowlist is assembled only from the fixed constant above.
    allowed_sql = ", ".join(
        "'" + intent.replace("'", "''") + "'"
        for intent in INITIAL_INTENTS
    )
    query = text(f"""
        SELECT user_message, actual_intent
        FROM {TABLE_NAME}
        WHERE actual_intent IS NOT NULL
          AND BTRIM(actual_intent) <> ''
          AND user_message IS NOT NULL
          AND BTRIM(user_message) <> ''
          AND LOWER(BTRIM(actual_intent)) IN ({allowed_sql})
        ORDER BY id ASC
    """)

    engine = None
    try:
        engine = create_read_only_engine(database_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        frame = pd.read_sql(query, engine)
    except Exception as exc:
        stop_training(
            "Supabase read-only connection or data fetch failed: "
            f"{type(exc).__name__}: {exc}"
        )
    finally:
        if engine is not None:
            engine.dispose()

    print(f"\nRows fetched for the five approved intents: {len(frame)}")

    try:
        data, report = prepare_training_data(frame)
    except ValueError as exc:
        stop_training(str(exc), status="QUALITY_REJECTED")

    training_rows = len(data)
    counts = report["unique_messages_per_intent"]

    print("\nDATA QUALITY REPORT")
    print(f"Unique messages after deduplication: {training_rows}")
    print(f"Duplicate rows removed: {report['duplicate_rows_removed']}")
    for intent in INITIAL_INTENTS:
        print(f"  {intent}: {counts[intent]} unique messages")

    missing = [
        intent for intent in INITIAL_INTENTS if counts[intent] == 0
    ]
    below_minimum = {
        intent: counts[intent]
        for intent in INITIAL_INTENTS
        if counts[intent] < MINIMUM_UNIQUE_EXAMPLES_PER_INTENT
    }

    if missing or below_minimum or training_rows < MINIMUM_RECORDS:
        details = []
        if missing:
            details.append("Missing intents: " + ", ".join(missing))
        if below_minimum:
            details.append(
                "Below minimum of "
                f"{MINIMUM_UNIQUE_EXAMPLES_PER_INTENT}: "
                + ", ".join(
                    f"{intent}={count}"
                    for intent, count in below_minimum.items()
                )
            )
        stop_training(
            "Insufficient unique human-reviewed examples. "
            + "; ".join(details),
            status="INSUFFICIENT_DATA",
        )

    X = data["user_message"]
    y = data["training_intent"]

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=TEST_SIZE,
            random_state=RANDOM_STATE,
            stratify=y,
        )
    except ValueError as exc:
        stop_training(
            f"Stratified train/test split could not be created: {exc}",
            status="INSUFFICIENT_DATA",
        )

    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
        ("classifier", LogisticRegression(max_iter=2000)),
    ])

    try:
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
    except Exception as exc:
        stop_training(
            f"Model training or prediction failed: {type(exc).__name__}: {exc}"
        )

    accuracy = accuracy_score(y_test, predictions)
    macro_f1 = f1_score(
        y_test,
        predictions,
        labels=list(INITIAL_INTENTS),
        average="macro",
        zero_division=0,
    )
    model_accuracy = f"{accuracy:.4f}"

    print("\nMODEL EVALUATION")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Macro F1: {macro_f1:.4f}")
    print("\nCLASSIFICATION REPORT")
    print(classification_report(
        y_test,
        predictions,
        labels=list(INITIAL_INTENTS),
        target_names=list(INITIAL_INTENTS),
        zero_division=0,
    ))
    print("CONFUSION MATRIX (rows=true, columns=predicted)")
    print(list(INITIAL_INTENTS))
    print(confusion_matrix(
        y_test,
        predictions,
        labels=list(INITIAL_INTENTS),
    ))

    trained_classes = set(
        str(label) for label in model.named_steps["classifier"].classes_
    )
    if trained_classes != set(INITIAL_INTENTS):
        stop_training(
            "Trained model classes do not exactly match the approved "
            "five-intent scope.",
            status="QUALITY_REJECTED",
        )

    if accuracy < MINIMUM_ACCURACY:
        stop_training(
            f"Accuracy {accuracy:.4f} is below the required "
            f"{MINIMUM_ACCURACY:.2f}. Existing model will remain unchanged.",
            status="QUALITY_REJECTED",
        )

    try:
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(model, MODEL_PATH)
        if not os.path.isfile(MODEL_PATH) or os.path.getsize(MODEL_PATH) == 0:
            stop_training("The model artifact is missing or empty.")
        # Reload once to catch serialization or deserialization problems.
        verified_model = joblib.load(MODEL_PATH)
        verified_classes = set(
            str(label)
            for label in verified_model.named_steps["classifier"].classes_
        )
        if verified_classes != set(INITIAL_INTENTS):
            stop_training(
                "Saved model failed the five-intent artifact verification.",
                status="QUALITY_REJECTED",
            )
    except Exception as exc:
        stop_training(
            f"Model artifact save/verification failed: {type(exc).__name__}: {exc}"
        )

    print("\nFINAL TRAINING REPORT")
    print(f"Training rows: {training_rows}")
    print(f"Training split: {len(X_train)}")
    print(f"Testing split: {len(X_test)}")
    print(f"Intent categories: {len(INITIAL_INTENTS)}")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Macro F1: {macro_f1:.4f}")
    print("Model saved: YES")
    print(f"Model path: {MODEL_PATH}")
    print("TRAINING_STATUS=TRAINED")
    print("MODEL_SAVED=true")
    print(f"MODEL_ACCURACY={accuracy:.4f}")
    print(f"TRAINING_ROWS={training_rows}")
    print(f"MODEL_PATH={MODEL_PATH}")


if __name__ == "__main__":
    main()
