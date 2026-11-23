
-- ============================================================
-- P1 TRAINING DATA AUDIT
-- SECTION 2: INTENT-WISE HUMAN REVIEW COUNTS
--
-- PURPOSE:
-- Count genuinely audited records for each intent.
-- Identify how many examples each intent still needs.
--
-- TRAINING MINIMUM:
-- 5 fully audited examples per intent.
--
-- READ ONLY - NO DATABASE CHANGES.
-- ============================================================

SELECT

    -- Intent category
    actual_intent,

    -- Total records with this intent and complete review audit
    COUNT(*) AS verified_records,

    -- Distinct normalized user messages
    COUNT(
        DISTINCT LOWER(TRIM(user_message))
    ) AS unique_normalized_messages,

    -- Additional reviews needed to reach five records
    GREATEST(
        5 - COUNT(*),
        0
    ) AS additional_reviews_needed

FROM public.assistant_training_logs

WHERE actual_intent IS NOT NULL
  AND TRIM(actual_intent) <> ''

  -- Both audit fields must be populated
  AND reviewer_user_id IS NOT NULL
  AND reviewed_at IS NOT NULL

  -- Valid user messages only
  AND user_message IS NOT NULL
  AND TRIM(user_message) <> ''

GROUP BY actual_intent

ORDER BY verified_records ASC, actual_intent ASC;
