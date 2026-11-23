-- ============================================================
-- QUERY: REVIEW ALL INTENT CATEGORIES AND THEIR EXAMPLES
-- ============================================================
--
-- PURPOSE:
-- Display all human-labelled intent categories and their
-- existing example messages.
--
-- WHY:
-- We need to understand what each intent means before adding
-- new training examples. This prevents incorrect labels.
--
-- OUTPUT:
-- actual_intent | example_count | example_messages
--
-- This query only reads data. It does not modify any records.
-- ============================================================

SELECT
    actual_intent,

    -- Count distinct normalized messages for each intent
    COUNT(DISTINCT LOWER(TRIM(user_message))) AS example_count,

    -- Show up to 5 existing examples for manual review
    ARRAY_AGG(
        DISTINCT TRIM(user_message)
    ) AS example_messages

FROM public.assistant_training_logs

WHERE actual_intent IS NOT NULL
  AND TRIM(actual_intent) <> ''
  AND user_message IS NOT NULL
  AND TRIM(user_message) <> ''

GROUP BY actual_intent

ORDER BY actual_intent;
