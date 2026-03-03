import os
import sys
import pandas as pd
import joblib
from sqlalchemy import create_engine
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


print("🚀 Starting Assistant Model Training...")

# ==========================================================
# 1️⃣ Load Database URL
# ==========================================================
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not set.")
    sys.exit(1)

try:
    engine = create_engine(DATABASE_URL)
except Exception as e:
    print(f"❌ Failed to connect to database: {e}")
    sys.exit(1)


# ==========================================================
# 2️⃣ Fetch Training Data
# ==========================================================
query = """
SELECT user_message, predicted_intent
FROM assistant_training_logs
WHERE predicted_intent IS NOT NULL
"""

try:
    df = pd.read_sql(query, engine)
except Exception as e:
    print(f"❌ Failed to fetch training data: {e}")
    sys.exit(1)

print(f"📊 Total training rows fetched: {len(df)}")

if len(df) < 20:
    print("❌ Not enough data to train (minimum 20 required).")
    sys.exit(0)


# ==========================================================
# 3️⃣ Train/Test Split
# ==========================================================
X_train, X_test, y_train, y_test = train_test_split(
    df["user_message"],
    df["predicted_intent"],
    test_size=0.2,
    random_state=42
)


# ==========================================================
# 4️⃣ Build ML Pipeline
# ==========================================================
model = Pipeline([
    ("tfidf", TfidfVectorizer()),
    ("clf", LogisticRegression(max_iter=1000))
])

print("🧠 Training model...")
model.fit(X_train, y_train)


# ==========================================================
# 5️⃣ Evaluate Model
# ==========================================================
predictions = model.predict(X_test)
accuracy = accuracy_score(y_test, predictions)

print(f"✅ Model Accuracy: {accuracy:.4f}")

if accuracy < 0.70:
    print("❌ Accuracy too low. Model will NOT be saved.")
    sys.exit(0)


# ==========================================================
# 6️⃣ Save Model
# ==========================================================
os.makedirs("models", exist_ok=True)

model_path = "models/assistant_intent_model.pkl"
joblib.dump(model, model_path)

print(f"🎉 Model saved successfully at: {model_path}")
print("✅ Training completed successfully.")