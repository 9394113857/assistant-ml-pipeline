
-- ================================================================
-- QUERY: RECORD-LEVEL TRAINING LABEL PROVENANCE AUDIT
-- ================================================================
--
-- PURPOSE:
-- Inspect each training record that has an actual_intent label
-- but does not have complete reviewer audit information.
--
-- SOURCE TABLE:
-- public.assistant_training_logs
--
-- COLUMN EXPLANATIONS:
--
-- id:
--     Unique training record ID.
--
-- user_message:
--     Original message entered by the user.
--
-- predicted_intent:
--     Intent originally predicted by Assistant-Service.
--
-- actual_intent:
--     Intent label currently stored for ML training.
--
-- confidence_score:
--     Confidence score from the original prediction.
--
-- model_version:
--     Model or rule version that generated the prediction.
--
-- created_at:
--     Date/time when the training record was created.
--
-- reviewer_user_id:
--     Administrator ID that performed the review.
--
-- reviewed_at:
--     Date/time when the administrator reviewed the record.
--
-- audit_status:
--     Indicates whether reviewer audit information is complete.
--
-- WHY WE NEED THIS:
--     The previous aggregate query showed 181 labelled records
--     with missing reviewer audit information.
--
--     This query lets us inspect the actual records and identify
--     their creation dates, original predictions and labels.
--
-- IMPORTANT:
--     created_at is NOT proof of human review.
--     predicted_intent is NOT proof of human review.
--     A missing reviewer ID or timestamp must not be fabricated.
--
-- QUERY TYPE:
--     READ ONLY.
--     No INSERT, UPDATE, DELETE or database modification.
--
-- ================================================================

SELECT

    -- Unique ID of each training record.
    id,

    -- Original user message.
    user_message,

    -- Intent predicted by Assistant-Service.
    predicted_intent,

    -- Current label used as the ML training target.
    actual_intent,

    -- Confidence of the original prediction.
    confidence_score,

    -- Version of the model/rules that generated the prediction.
    model_version,

    -- Original record creation timestamp.
    created_at,

    -- Administrator ID, if available.
    reviewer_user_id,

    -- Administrator review timestamp, if available.
    reviewed_at,

    -- Explain whether the audit information is complete.
    CASE
        WHEN reviewer_user_id IS NOT NULL
         AND reviewed_at IS NOT NULL
            THEN 'AUDIT_COMPLETE'

        WHEN reviewer_user_id IS NULL
         AND reviewed_at IS NULL
            THEN 'BOTH_AUDIT_FIELDS_MISSING'

        WHEN reviewer_user_id IS NULL
            THEN 'REVIEWER_ID_MISSING'

        WHEN reviewed_at IS NULL
            THEN 'REVIEW_TIMESTAMP_MISSING'
    END AS audit_status

FROM public.assistant_training_logs

-- Only inspect records with a populated actual intent.
WHERE actual_intent IS NOT NULL
  AND TRIM(actual_intent) <> ''

  -- Exclude records that do not have a usable message.
  AND user_message IS NOT NULL
  AND TRIM(user_message) <> ''

  -- Return records missing at least one audit field.
  AND (
      reviewer_user_id IS NULL
      OR reviewed_at IS NULL
  )

-- Oldest records first, to help identify historical data.
ORDER BY
    created_at ASC,
    id ASC;

-- ================================================================
-- EXPECTED RESULT:
--
-- We expect to see the 181 records identified by the previous
-- aggregate audit, assuming no records changed in between.
--
-- NEXT ACTION:
-- Inspect creation dates, model versions and predicted labels.
-- Then determine whether these are legacy labels or records
-- that were populated outside the admin review workflow.
--
-- DO NOT UPDATE THESE RECORDS YET.
-- ================================================================
