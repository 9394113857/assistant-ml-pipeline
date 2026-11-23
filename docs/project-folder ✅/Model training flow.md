Before today's coding starts, we're going to do a proper two-repository audit, including the previous work in this Project. We won't start inserting more synthetic records or changing code until we understand the complete flow.

And one important distinction: we have two separate problems to investigate:
1. Model training problem: the ML pipeline may refuse to save a new model because its validation accuracy or data-quality requirements aren't met.
2. Live training-data problem: messages sent through the Angular chatbot may not be reaching assistant_training_logs, so the dataset isn't growing with actual user activity.
The Render 422 response is a separate clue. It indicates a rejected chat request, but doesn't establish that low model accuracy caused that response.
What we've established from our previous work
- Both repositories use the same Assistant Supabase database.
- The ML pipeline reads assistant_training_logs.
- Training uses human-reviewed actual_intent, not merely predicted_intent.
- The pipeline requires at least 30 usable records, at least 2 intent classes, at least 5 reviewed examples per class, and validation accuracy of at least 70%.
- A model is saved only after the validation gates pass.
- The earlier ML workflow had a problem where a training failure could still be reported as workflow success.
- We also identified a scikit-learn version mismatch: the saved model was created with 1.5.0, while the Render service was using 1.9.1.
These are important things to preserve while auditing the current code.
