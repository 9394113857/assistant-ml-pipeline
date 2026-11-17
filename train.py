
import os
import sys
import pandas as pd
import joblib

# SQLAlchemy is used to connect Python with PostgreSQL / Supabase.
from sqlalchemy import create_engine

# Machine Learning libraries
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

# Used to divide the dataset into training and testing data.
from sklearn.model_selection import train_test_split

# Used to evaluate how accurately our model predicts intents.
from sklearn.metrics import accuracy_score


# ==========================================================
# ASSISTANT ML PIPELINE
# ==========================================================
#
# Overall workflow:
#
# 1. Read DATABASE_URL from GitHub Actions environment.
# 2. Connect to our shared Assistant Supabase database.
# 3. Fetch messages and their corresponding intents.
# 4. Validate and clean the training data.
# 5. Split data into training and testing datasets.
# 6. Train the ML model using TF-IDF + Logistic Regression.
# 7. Evaluate model accuracy.
# 8. Save the trained model as a .pkl file.
#
# ==========================================================

print("\n🚀 Starting Assistant Model Training...")


# ==========================================================
# STEP 1: LOAD DATABASE CONNECTION URL
# ==========================================================

# DATABASE_URL is configured in GitHub repository secrets.
#
# GitHub Actions passes this secret to Python as an
# environment variable.
#
# We do not hardcode the database password in this file.
#
# Example format:
# postgresql://username:password@host:5432/database

DATABASE_URL = os.getenv("DATABASE_URL")


# Check whether DATABASE_URL exists.
# Without it, Python cannot connect to Supabase.

if not DATABASE_URL:

    print("❌ DATABASE_URL is not configured.")

    # Exit code 1 means failure.
    sys.exit(1)


print("✅ DATABASE_URL found.")


# ==========================================================
# STEP 2: CONNECT TO SUPABASE POSTGRESQL
# ==========================================================

try:

    # create_engine() prepares a SQLAlchemy database engine.
    # This engine will be used to execute SQL queries.

    engine = create_engine(DATABASE_URL)

    # Actually test the database connection.
    # Creating an engine alone does not guarantee
    # that the database is reachable.

    with engine.connect():

        print("✅ Successfully connected to Supabase PostgreSQL.")

except Exception as e:

    print("❌ Database connection failed.")
    print(f"Error details: {e}")

    sys.exit(1)


# ==========================================================
# STEP 3: FETCH TRAINING DATA FROM DATABASE
# ==========================================================

# We are reading two columns from our existing table:
#
# assistant_training_logs
#
# user_message:
#     The original message entered by the user.
#
# predicted_intent:
#     The intent currently stored for that message.
#
# Example:
#
# user_message                  predicted_intent
# ------------------------------------------------
# Hello                         greeting
# Show my orders                order_status
# I want to buy a product       product_search
#
# IMPORTANT:
# At this stage, we are using predicted_intent as the
# training target because that is what your current
# database schema and code provide.
#
# Later, we should verify whether these are human-verified
# labels or predictions from the existing model.

query = """
SELECT
    user_message,
    predicted_intent
FROM assistant_training_logs
WHERE predicted_intent IS NOT NULL
  AND user_message IS NOT NULL
  AND TRIM(user_message) <> ''
"""


try:

    # Execute the SQL query and load its results into
    # a Pandas DataFrame.
    #
    # A DataFrame is a table-like structure in Python.

    df = pd.read_sql(query, engine)

    print("✅ Training data fetched successfully.")

except Exception as e:

    print("❌ Failed to fetch training data from database.")
    print(f"Error details: {e}")

    sys.exit(1)

finally:

    # Close the database engine connections after fetching.
    engine.dispose()


# Display how many records were retrieved.

print(f"\n📊 Total training rows fetched: {len(df)}")


# ==========================================================
# STEP 4: VALIDATE AND CLEAN TRAINING DATA
# ==========================================================

# First, check whether we have enough records.
#
# Your current minimum requirement is 20 records.
#
# If the database returns only 2 records,
# the training process must stop.

MINIMUM_RECORDS = 20

if len(df) < MINIMUM_RECORDS:

    print(
        f"❌ Not enough training data. "
        f"Required: {MINIMUM_RECORDS}, Available: {len(df)}"
    )

    # Exit code 1 tells GitHub Actions that training failed.
    # Previously you used sys.exit(0), which incorrectly
    # reported successful execution.

    sys.exit(1)


# Remove duplicate message + intent combinations.
#
# Example:
# "Hello" + "greeting"
# "Hello" + "greeting"
#
# Only one identical combination is retained.

df = df.drop_duplicates(
    subset=["user_message", "predicted_intent"]
)


# Remove any remaining missing values.

df = df.dropna(
    subset=["user_message", "predicted_intent"]
)


# Convert message and intent values into strings.
# This ensures the text-processing pipeline receives text.

df["user_message"] = df["user_message"].astype(str)
df["predicted_intent"] = df["predicted_intent"].astype(str)


# Remove empty messages and surrounding spaces.

df["user_message"] = df["user_message"].str.strip()

df = df[df["user_message"] != ""]


print(f"📊 Training rows after cleaning: {len(df)}")


# Check the minimum requirement again after cleaning.

if len(df) < MINIMUM_RECORDS:

    print("❌ Not enough unique and valid records after cleaning.")

    sys.exit(1)


# ==========================================================
# STEP 5: CHECK INTENT DISTRIBUTION
# ==========================================================

# An intent is the category of a user's message.
#
# Example:
#
# greeting       = Hello, Hi, Good morning
# order_status   = Where is my order?
# product_search = Show me available products
# contact_support = I need help
#
# We need at least two different intent categories
# to train a classification model.

intent_counts = df["predicted_intent"].value_counts()


print("\n📊 Intent Distribution:")
print(intent_counts.to_string())


# Count the number of unique intent categories.

number_of_intents = df["predicted_intent"].nunique()


if number_of_intents < 2:

    print("❌ At least 2 different intent classes are required.")

    sys.exit(1)


# Each intent must have at least 2 records.
#
# We use stratified splitting below.
# This requires enough examples of every class
# to distribute them across training and testing datasets.

if intent_counts.min() < 2:

    print(
        "❌ Each intent must have at least 2 records "
        "before train/test splitting."
    )

    sys.exit(1)


print("✅ Intent distribution validation completed.")


# ==========================================================
# STEP 6: SEPARATE INPUT (X) AND OUTPUT (y)
# ==========================================================

# X = Input messages.
#
# These are the messages the model learns from.
#
# y = Expected intent labels.
#
# The model learns the relationship between X and y.
#
# Example:
#
# X                              y
# -------------------------------------------
# Hello                          greeting
# Show my orders                 order_status
# Find a mobile phone            product_search

X = df["user_message"]

y = df["predicted_intent"]


print("\n✅ Input messages (X) and intent labels (y) prepared.")


# ==========================================================
# STEP 7: SPLIT TRAINING AND TESTING DATA
# ==========================================================

# We divide the dataset into:
#
# 80% Training data:
#     Used by the model to learn patterns.
#
# 20% Testing data:
#     Used to evaluate the model on messages it did not
#     receive during training.
#
# random_state=42:
#     Makes the split reproducible.
#
# stratify=y:
#     Preserves the approximate distribution of each
#     intent category in both datasets.

try:

    X_train, X_test, y_train, y_test = train_test_split(

        X,
        y,

        test_size=0.20,

        random_state=42,

        stratify=y

    )

except ValueError as e:

    print("❌ Failed to split training and testing data.")
    print(f"Error details: {e}")

    sys.exit(1)


print(f"\n📚 Training records: {len(X_train)}")
print(f"🧪 Testing records: {len(X_test)}")


# ==========================================================
# STEP 8: BUILD THE MACHINE LEARNING PIPELINE
# ==========================================================

# Our model contains two stages:
#
# 1. TF-IDF Vectorizer
# 2. Logistic Regression Classifier
#
# ----------------------------------------------------------
# TF-IDF:
#
# Converts text messages into numerical features.
#
# Machine learning algorithms cannot directly understand
# raw text such as:
#
# "Hello, how are you?"
#
# TF-IDF converts words into numerical representations
# based on their importance in the dataset.
#
# ----------------------------------------------------------
# Logistic Regression:
#
# This is our classification algorithm.
#
# It learns patterns from the numerical features and
# predicts the most likely intent category.
#
# max_iter=1000:
# Allows the algorithm more iterations to converge.
#
# ----------------------------------------------------------

model = Pipeline([

    (
        "tfidf",
        TfidfVectorizer()
    ),

    (
        "clf",
        LogisticRegression(max_iter=1000)
    )

])


print("\n🧠 ML Pipeline created successfully.")


# ==========================================================
# STEP 9: TRAIN THE MODEL
# ==========================================================

# model.fit():
#
# This is where the actual learning happens.
#
# The model receives:
#
# X_train = User messages
# y_train = Corresponding intent labels
#
# It learns how different words and phrases relate
# to the intent categories.

try:

    print("\n🚀 Model training started...")

    model.fit(X_train, y_train)

    print("✅ Model training completed.")

except Exception as e:

    print("❌ Model training failed.")
    print(f"Error details: {e}")

    sys.exit(1)


# ==========================================================
# STEP 10: EVALUATE THE TRAINED MODEL
# ==========================================================

# Now we test the model using X_test.
#
# These messages were not used during training.
#
# model.predict():
# Predicts the intent for each testing message.
#
# accuracy_score():
# Compares predicted intents with actual test labels.
#
# Formula:
#
# Accuracy = Correct Predictions / Total Predictions

try:

    print("\n🔍 Evaluating model...")

    predictions = model.predict(X_test)

    accuracy = accuracy_score(
        y_test,
        predictions
    )

    print(f"📊 Model Accuracy: {accuracy:.4f}")

except Exception as e:

    print("❌ Model evaluation failed.")
    print(f"Error details: {e}")

    sys.exit(1)


# ==========================================================
# STEP 11: CHECK MODEL ACCURACY
# ==========================================================

# We currently require at least 70% accuracy.
#
# If accuracy is below 70%, we do not save this model.
#
# IMPORTANT:
# Accuracy alone does not guarantee a good classifier.
# We should later inspect precision, recall and F1-score.

MINIMUM_ACCURACY = 0.70

if accuracy < MINIMUM_ACCURACY:

    print(
        f"❌ Accuracy is below the required "
        f"{MINIMUM_ACCURACY * 100:.0f}%."
    )

    print("❌ Model will NOT be saved.")

    sys.exit(1)


print("✅ Model passed the accuracy threshold.")


# ==========================================================
# STEP 12: SAVE THE TRAINED MODEL
# ==========================================================

# Create the models folder if it does not exist.
#
# exist_ok=True means Python will not raise an error
# if the folder already exists.

try:

    os.makedirs(
        "models",
        exist_ok=True
    )


    # This is the model file path.
    #
    # Keep this path consistent with the path used by
    # your Flask assistant-service when loading the model.

    model_path = "models/assistant_intent_model.pkl"


    # joblib.dump():
    #
    # Saves the complete trained ML pipeline.
    #
    # This includes:
    # - TF-IDF Vectorizer
    # - Logistic Regression Classifier
    #
    # Flask can later load this file using joblib.load().

    joblib.dump(
        model,
        model_path
    )


    print(f"🎉 Model saved successfully: {model_path}")

except Exception as e:

    print("❌ Failed to save model.")
    print(f"Error details: {e}")

    sys.exit(1)


# ==========================================================
# STEP 13: FINAL TRAINING SUMMARY
# ==========================================================

print("\n========================================")
print("       ASSISTANT ML TRAINING REPORT")
print("========================================")

print(f"Total records fetched : {len(df)}")

print(f"Training records      : {len(X_train)}")

print(f"Testing records       : {len(X_test)}")

print(f"Intent categories     : {number_of_intents}")

print(f"Model accuracy        : {accuracy:.4f}")

print(f"Model saved           : YES")

print(f"Model location        : {model_path}")

print("========================================")

print("\n🎉 ASSISTANT MODEL TRAINING COMPLETED SUCCESSFULLY!")

# Exit code 0 means everything completed successfully.
sys.exit(0)
