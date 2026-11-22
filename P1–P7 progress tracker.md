Model Accuracy (Required 70%)
Traing data threshold value atleast 70%

trained the classifier
but the validation rule  prevented the model being saved
intent labels and predicted labels

Insufficient data : for any algorithm shoudl feed best data and more data diffrent ways
Class imbalance   : Some categories have 25 records, while others have only 2 or 3.

Your test dataset has only 24 records. 
Some classes have just one test example, so the accuracy can fluctuate significantly.

The classification report also shows zero precision 
and recall for several categories, including product_category, recommend_product, and weather.

Additional workflow issues
Apart from model accuracy, I found these issues.

Issue A – Incorrect email report metrics

Your workflow tries to extract:
TRAINING_ROWS=
MODEL_ACCURACY=
TRAINING_STATUS=
MODEL_SAVED=


But the visible training output doesn't show those machine-readable values.

Consequently, your email reports:
- Training records: N/A
- Model accuracy: N/A
- Training status: FAILED
Even though the actual training output contains 118 records and 54.17% accuracy.

We need to fix the reporting contract between train.py and the GitHub Actions YAML.

Issue B – Failure handling

The workflow correctly prevents deployment when training fails.

However, the final validation step checks both the training result and model verification, then exits with code 1.

This is why the overall workflow remains failed even though the email notification succeeds.

We should distinguish:
- Pipeline execution failure.
- Model quality rejection.
- Successful notification of a rejected model.

Issue C – Runtime warning

The log contains a Node.js 20 deprecation warning for the GitHub Actions dependencies.

This is not causing the current failure, but we should eventually upgrade compatible action versions.


========================
P1–P7 progress tracker:-

Priority	Work													   	Status
P1		Human-verified labels and data quality safeguards	Code committed; data correction and run validation 	pending
P2		Dataset size and intent balance										   	Pending
P3		Model comparison and improvement										Pending
P4		Training metrics and email reporting										Pending
P5		Evaluation and validation improvements										Pending
P6		Workflow status and failure handling										Pending
P7		Model artifact and Assistant-Service runtime verification							Pending

Next: We'll finish validating P1 before moving to P2. I won't lower the accuracy threshold just to make the workflow green, and I won't deploy an unverified model.

all each p1 wise to p7 should be green first and then test okay.


I found your previous assistant_training_logs verification from 21 November 2026:
- Total records: 93
- Effective labels included assistant_about, unknown, greeting, show_products, show_orders, recommend_product, product_category, and weather.
- Your earlier training run had 79 valid unique rows, 11 intents, and 31.25% accuracy. The model wasn't saved or deployed.
I also found the later training run from 22 November: it had 155 fetched rows, but only 3 human-corrected labels. That's why P1 now reports only 3 eligible records after we removed the predicted-label fallback.

next we should finish P1 by fixing the source of the missing human-verified labels, not by changing the accuracy threshold.

Our previous logs show that the database grew from 93 to 155 records, but the human-corrected labels remained at just 3. More records alone won't solve that.








  
