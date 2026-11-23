-- =========================================================
-- PURPOSE:
-- Check the quality and distribution of human-labelled
-- Assistant intent training records.
--
-- WHAT THIS QUERY RETURNS:
-- 1. actual_intent:
--    The human-assigned intent category.
--
-- 2. reviewed_rows:
--    Total records available for this intent.
--
-- 3. unique_training_messages:
--    Unique messages after trimming whitespace.
--    Helps identify duplicate training examples.
--
-- 4. audited_review_rows:
--    Records with reviewer_user_id and reviewed_at.
--    Helps identify reviews with audit information.
--
-- WHY WE NEED THIS:
-- The ML pipeline trains only on non-empty actual_intent.
-- We need to understand which intent categories have
-- enough unique examples before attempting retraining.
--
-- EXPECTED RESULT:
-- One row per intent category.
-- Sorted from the smallest unique dataset to the largest.
-- =========================================================

SELECT
    actual_intent,

    COUNT(*) AS reviewed_rows,

    COUNT(DISTINCT BTRIM(user_message))
        AS unique_training_messages,

    COUNT(*) FILTER (
        WHERE reviewer_user_id IS NOT NULL
          AND reviewed_at IS NOT NULL
    ) AS audited_review_rows

FROM public.assistant_training_logs

WHERE actual_intent IS NOT NULL
  AND BTRIM(actual_intent) <> ''
  AND user_message IS NOT NULL
  AND BTRIM(user_message) <> ''

GROUP BY actual_intent

ORDER BY unique_training_messages ASC;
