
-- ============================================================
-- P1 AUDIT - SECTION 3
-- FIND RECORDS WITHOUT ACTUAL INTENT
--
-- PURPOSE:
-- Identify the record excluded from labelled training data.
--
-- READ ONLY - NO DATABASE CHANGES.
-- ============================================================

SELECT
    id,
    user_message,
    predicted_intent,
    actual_intent,
    model_version,
    reviewer_user_id,
    reviewed_at,
    created_at

FROM public.assistant_training_logs

WHERE actual_intent IS NULL
   OR TRIM(actual_intent) = ''

ORDER BY id ASC;
