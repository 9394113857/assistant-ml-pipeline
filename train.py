
import os
import sys
import math
import pandas as pd
import joblib

from sqlalchemy import create_engine, text

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report


# ==========================================================
# ASSISTANT ML PIPELINE
# ==========================================================
#
# PURPOSE:
# Automatically train the Assistant intent classification
# model using records stored in Supabase PostgreSQL.
#
# DATABASE TABLE:
# public.assistant_training_logs
#
# INPUT:
# user_message
#
# TARGET:
# actual_intent from records with complete review audit metadata.
#
# MODEL:
# TF-IDF + Logistic Regression
#
# OUTPUT:
# models/assistant_intent_model.pkl
#
# IMPORTANT:
# Only records with a populated actual_intent AND both
# reviewer_user_id and reviewed_at are eligible for training.
# predicted_intent is not used as a training-label fallback.
#
# ==========================================================


# ==========================================================
# CONFIGURATION
# ==========================================================

MINIMUM_RECORDS = 30

MINIMUM_ACCURACY = 0.70

MINIMUM_EXAMPLES_PER_INTENT = 5

# Only audit-qualified actual_intent labels are eligible for training.
# Complete audit metadata is required; predicted intents are not labels.

MODEL_PATH = "models/assistant_intent_model.pkl"

TABLE_NAME = "public.assistant_training_logs"


# ==========================================================
# HELPER FUNCTION: STOP TRAINING WITH A CLEAR STATUS
# ==========================================================

training_rows = 0
model_accuracy = "N/A"


def stop_training(message, status="FAILED"):

    print("\n" + "=" * 55)
    print(f"❌ TRAINING STATUS: {status}")
    print(f"REASON: {message}")
    print("=" * 55)

    # Always emit the workflow reporting contract, including on rejection.
    print(f"TRAINING_STATUS={status}")
    print(f"TRAINING_ROWS={training_rows}")
    print(f"MODEL_ACCURACY={model_accuracy}")
    print("MODEL_SAVED=false")
    print(f"MODEL_PATH={MODEL_PATH}")

    # A non-zero exit code tells GitHub Actions
    # that the training step failed or did not produce
    # a deployable model.
    #
    # The workflow will still attempt to send an email
    # because its email step uses if: always().

    sys.exit(1)


# ==========================================================
# STEP 1: START TRAINING
# ==========================================================

print("\n" + "=" * 55)
print("🚀 ASSISTANT ML MODEL TRAINING")
print("=" * 55)

print("\n📌 Training configuration")
print(f"Minimum records : {MINIMUM_RECORDS}")
print(f"Minimum accuracy: {MINIMUM_ACCURACY * 100:.0f}%")
print(f"Database table  : {TABLE_NAME}")
print(f"Model output    : {MODEL_PATH}")


# ==========================================================
# STEP 2: LOAD DATABASE URL
# ==========================================================

# DATABASE_URL is stored in GitHub Actions Secrets.
#
# Never hardcode the database password here.
# Never print the complete DATABASE_URL in GitHub logs.

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:

    stop_training(
        "DATABASE_URL secret is missing."
    )

print("\n✅ DATABASE_URL environment variable found.")


# ==========================================================
# STEP 3: CONNECT TO SUPABASE
# ==========================================================

try:

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True
    )

    # Test the connection and inspect the database context.
    # This diagnostic query helps compare GitHub Actions
    # with the Supabase SQL Editor.

    diagnostic_query = text("""
        SELECT
            current_database() AS database_name,
            current_user AS database_user,
            current_schema() AS current_schema,
            (
                SELECT COUNT(*)
                FROM public.assistant_training_logs
            ) AS training_records
    """)

    with engine.connect() as connection:

        result = connection.execute(diagnostic_query)

        row = result.fetchone()

    print("\n🔍 DATABASE DIAGNOSTICS")
    print("-" * 40)

    print(f"Database          : {row.database_name}")
    print(f"Database user     : {row.database_user}")
    print(f"Current schema    : {row.current_schema}")
    print(f"Database row count: {row.training_records}")

    print("-" * 40)

    print("✅ Supabase connection successful.")

except Exception as e:

    stop_training(
        f"Database connection or diagnostic query failed: {e}"
    )

finally:

    # If connection creation succeeded, close the engine
    # after fetching the data.
    #
    # The engine may not exist if create_engine itself failed.

    if "engine" in locals():
        engine.dispose()


# ==========================================================
# STEP 4: FETCH TRAINING DATA
# ==========================================================

# Fetch candidate messages, actual labels, and review audit metadata.
# A record is eligible only when actual_intent, reviewer_user_id,
# and reviewed_at are all populated. Empty messages are excluded.

query = """
SELECT
    user_message,
    actual_intent,
    reviewer_user_id,
    reviewed_at
FROM public.assistant_training_logs
WHERE actual_intent IS NOT NULL
  AND TRIM(actual_intent) <> ''
  AND user_message IS NOT NULL
  AND TRIM(user_message) <> ''
ORDER BY id ASC
"""


try:

    # Re-create the engine because the diagnostic engine
    # was disposed after its connection test.

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True
    )

    df = pd.read_sql(
        query,
        engine
    )

except Exception as e:

    stop_training(
        f"Failed to fetch records from {TABLE_NAME}: {e}"
    )

finally:

    if "engine" in locals():
        engine.dispose()


print("\n📊 DATABASE FETCH REPORT")
print("-" * 40)

print(f"Total training rows fetched: {len(df)}")

print("-" * 40)


# ==========================================================
# STEP 5: CLEAN TRAINING DATA
# ==========================================================

# Remove records missing required message or label values.
df = df.dropna(
    subset=["user_message", "actual_intent"]
).copy()

# Normalize the message and target text.
df["user_message"] = df["user_message"].astype(str).str.strip()
df["actual_intent"] = df["actual_intent"].astype(str).str.strip()

# Require BOTH audit fields. A populated actual_intent alone
# is not sufficient evidence of a reviewed training example.
audit_valid = (
    df["reviewer_user_id"].notna()
    & df["reviewed_at"].notna()
)
audit_rejected_rows = int((~audit_valid).sum())

df = df[audit_valid].copy()

# Exclude blank messages and labels after trimming.
df = df[
    (df["user_message"] != "")
    & (df["actual_intent"] != "")
].copy()

# The target is exclusively the audit-qualified actual_intent.
df["training_intent"] = df["actual_intent"]

# Remove exact duplicate message + intent combinations.
df = df.drop_duplicates(
    subset=["user_message", "training_intent"]
).reset_index(drop=True)


print("\n🧹 DATA CLEANING AND AUDIT REPORT")
print("-" * 40)

training_rows = len(df)

print(f"Rows rejected for incomplete audit: {audit_rejected_rows}")
print(f"Eligible unique audited rows: {training_rows}")

print("-" * 40)


# ==========================================================
# STEP 6: CHECK MINIMUM RECORD COUNT
# ==========================================================

if len(df) < MINIMUM_RECORDS:

    stop_training(
        f"Insufficient training data. "
        f"Required: {MINIMUM_RECORDS}, "
        f"Available after cleaning: {len(df)}.",
        status="INSUFFICIENT_DATA"
    )


# ==========================================================
# STEP 7: CHECK INTENT DISTRIBUTION
# ==========================================================

intent_counts = df["training_intent"].value_counts()

number_of_intents = len(intent_counts)

print("\n📊 INTENT DISTRIBUTION")
print("-" * 40)

print(intent_counts.to_string())

print("-" * 40)

print(f"Unique intent categories: {number_of_intents}")


# At least two intent classes are required
# for a classification model.

if number_of_intents < 2:

    stop_training(
        "At least two different intent categories are required."
    )


# Require enough verified examples per class to reduce highly
# unstable evaluation and avoid training on one-off labels.
if intent_counts.min() < MINIMUM_EXAMPLES_PER_INTENT:

    stop_training(
        f"Every intent needs at least {MINIMUM_EXAMPLES_PER_INTENT} "
        "human-verified examples.",
        status="INSUFFICIENT_DATA"
    )


# Check that the 20% testing dataset can contain
# at least one example of every intent category.

test_record_count = math.ceil(len(df) * 0.20)

train_record_count = len(df) - test_record_count

if test_record_count < number_of_intents:

    stop_training(
        "Not enough testing records to represent every intent."
    )

if train_record_count < number_of_intents:

    stop_training(
        "Not enough training records to represent every intent."
    )


# ==========================================================
# STEP 8: PREPARE INPUT X AND TARGET y
# ==========================================================

# X = User messages.
#
# y = actual_intent from records with complete review audit metadata.
#
# Example:
#
# X                         y
# --------------------------------
# hi                        greeting
# hello                     greeting
# show products list        show_products
# recommend one             recommend_product

X = df["user_message"]

y = df["training_intent"]

print(f"Audit-qualified labels used: {len(df)}")
print("\n✅ INPUT AND TARGET DATA PREPARED.")


# ==========================================================
# STEP 9: TRAIN / TEST SPLIT
# ==========================================================

# 80% of records are used for training.
# 20% of records are used for evaluation.
#
# stratify=y preserves the intent distribution
# as far as possible in both datasets.

try:

    X_train, X_test, y_train, y_test = train_test_split(

        X,
        y,

        test_size=0.20,

        random_state=42,

        stratify=y

    )

except Exception as e:

    stop_training(
        f"Train/test split failed: {e}"
    )


print("\n📚 DATASET SPLIT")
print("-" * 40)

print(f"Training records: {len(X_train)}")

print(f"Testing records : {len(X_test)}")

print("-" * 40)


# ==========================================================
# STEP 10: CREATE ML PIPELINE
# ==========================================================

# TF-IDF:
# Converts text messages into numerical features.
#
# Logistic Regression:
# Learns patterns from those features and predicts
# the appropriate intent category.
#
# Pipeline:
# Combines both steps into one reusable ML model.
#
# Saving this pipeline allows Flask to load both
# the vectorizer and classifier together.

model = Pipeline([

    (
        "tfidf",
        TfidfVectorizer()
    ),

    (
        "classifier",
        LogisticRegression(
            max_iter=1000
        )
    )

])


print("\n🧠 ML PIPELINE CREATED.")


# ==========================================================
# STEP 11: TRAIN THE MODEL
# ==========================================================

try:

    print("\n🚀 MODEL TRAINING STARTED...")

    model.fit(
        X_train,
        y_train
    )

    print("✅ MODEL TRAINING COMPLETED.")

except Exception as e:

    stop_training(
        f"Model fitting failed: {e}"
    )


# ==========================================================
# STEP 12: EVALUATE MODEL
# ==========================================================

try:

    print("\n🔍 MODEL EVALUATION STARTED...")

    predictions = model.predict(X_test)

    accuracy = accuracy_score(
        y_test,
        predictions
    )
    model_accuracy = f"{accuracy:.4f}"

    print(f"\n📊 MODEL ACCURACY: {accuracy:.4f}")

    print("\n📋 CLASSIFICATION REPORT")

    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0
        )
    )

except Exception as e:

    stop_training(
        f"Model evaluation failed: {e}"
    )


# ==========================================================
# STEP 13: CHECK ACCURACY THRESHOLD
# ==========================================================

if accuracy < MINIMUM_ACCURACY:

    stop_training(
        f"Model accuracy {accuracy:.4f} is below "
        f"the required {MINIMUM_ACCURACY:.2f}. "
        "Model will not be saved.",
        status="QUALITY_REJECTED"
    )


print("\n✅ MODEL PASSED ACCURACY VALIDATION.")


# ==========================================================
# STEP 14: SAVE TRAINED MODEL
# ==========================================================

try:

    # Create the output folder if necessary.

    os.makedirs(
        "models",
        exist_ok=True
    )

    # Save the complete trained pipeline.

    joblib.dump(
        model,
        MODEL_PATH
    )

    # Verify that the file exists and is not empty.

    if not os.path.exists(MODEL_PATH):

        stop_training(
            "Model file was not created."
        )

    if os.path.getsize(MODEL_PATH) == 0:

        stop_training(
            "Model file is empty."
        )

    print(f"\n🎉 MODEL SAVED: {MODEL_PATH}")

except Exception as e:

    stop_training(
        f"Model saving failed: {e}"
    )


# ==========================================================
# STEP 15: FINAL TRAINING REPORT
# ==========================================================

print("\n" + "=" * 55)

print("       ASSISTANT ML TRAINING REPORT")

print("=" * 55)

print(f"Training rows fetched : {len(df)}")

print(f"Training records      : {len(X_train)}")

print(f"Testing records       : {len(X_test)}")

print(f"Intent categories     : {number_of_intents}")

print(f"Model accuracy        : {accuracy:.4f}")

print(f"Accuracy threshold    : {MINIMUM_ACCURACY:.2f}")

print("Model saved           : YES")

print(f"Model location        : {MODEL_PATH}")

print("=" * 55)

# These markers are read by GitHub Actions
# to construct the final email report.

print("TRAINING_STATUS=TRAINED")

print("MODEL_SAVED=true")

print(f"MODEL_ACCURACY={accuracy:.4f}")

print(f"TRAINING_ROWS={len(df)}")

print("MODEL_PATH=models/assistant_intent_model.pkl")

print("\n🎉 ASSISTANT ML TRAINING COMPLETED SUCCESSFULLY!")

sys.exit(0)
