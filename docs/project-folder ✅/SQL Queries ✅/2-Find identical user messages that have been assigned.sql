-- =========================================================
-- PURPOSE:
-- Find identical user messages that have been assigned
-- more than one actual_intent.
--
-- WHAT EACH COLUMN RETURNS:
-- 1. normalized_user_message:
--    The message converted to lowercase and trimmed.
--    This helps identify duplicates that differ only
--    by capitalization or surrounding spaces.
--
-- 2. total_rows:
--    Number of database records containing this message.
--
-- 3. different_intent_count:
--    Number of distinct actual_intent labels assigned
--    to this same message.
--
-- 4. assigned_intents:
--    The different labels assigned to the message.
--
-- WHY WE NEED THIS:
-- The same training message should not accidentally
-- teach the classifier conflicting intent labels.
-- We need to identify these cases before retraining.
--
-- EXPECTED RESULT:
-- Only messages assigned more than one distinct intent.
-- If no rows are returned, no conflicting labels were
-- found using this normalization.
--
-- NOTE:
-- This is a read-only query. It does not modify data.
-- =========================================================

SELECT
    LOWER(BTRIM(user_message)) AS normalized_user_message,

    COUNT(*) AS total_rows,

    COUNT(DISTINCT actual_intent) AS different_intent_count,

    STRING_AGG(
        DISTINCT actual_intent,
        ', ' ORDER BY actual_intent
    ) AS assigned_intents

FROM public.assistant_training_logs

WHERE actual_intent IS NOT NULL
  AND BTRIM(actual_intent) <> ''
  AND user_message IS NOT NULL
  AND BTRIM(user_message) <> ''

GROUP BY LOWER(BTRIM(user_message))

HAVING COUNT(DISTINCT actual_intent) > 1

ORDER BY different_intent_count DESC, total_rows DESC;
