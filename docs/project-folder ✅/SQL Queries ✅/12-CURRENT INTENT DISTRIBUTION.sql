
-- ============================================================
-- P1 AUDIT - SECTION 4
-- CURRENT INTENT DISTRIBUTION
--
-- PURPOSE:
-- Count records per predicted and actual intent.
-- Identify the latest rule_v4 records.
--
-- READ ONLY - NO DATABASE CHANGES.
-- ============================================================

SELECT
    model_version,
    predicted_intent,
    actual_intent,

    COUNT(*) AS total_records,

    COUNT(*) FILTER (
        WHERE reviewer_user_id IS NOT NULL
          AND reviewed_at IS NOT NULL
    ) AS fully_audited_records

FROM public.assistant_training_logs

GROUP BY
    model_version,
    predicted_intent,
    actual_intent

ORDER BY
    model_version,
    predicted_intent,
    actual_intent;
