-- ============================================================
-- QUERY: FIND INTENT CATEGORIES WITH INSUFFICIENT DATA
-- ============================================================
--
-- PURPOSE:
-- Identify intent categories that currently have fewer than
-- 5 unique human-labelled training messages.
--
-- WHY WE NEED THIS:
-- Our ML training pipeline requires at least 5 unique
-- examples for every intent category.
--
-- TABLE:
-- public.assistant_training_logs
--
-- IMPORTANT COLUMNS:
-- actual_intent : Human-corrected intent label
-- user_message  : Original user message
--
-- OUTPUT:
-- actual_intent
-- unique_reviewed_examples
-- additional_examples_needed
--
-- This query only reads data. It does not modify any records.
-- ============================================================

SELECT

    -- Human-labelled intent category
    actual_intent,

    -- Count unique messages after removing extra spaces
    -- and ignoring uppercase/lowercase differences
    COUNT(
        DISTINCT LOWER(TRIM(user_message))
    ) AS unique_reviewed_examples,

    -- Calculate how many more examples are required
    -- to reach the minimum threshold of 5
    GREATEST(
        5 - COUNT(DISTINCT LOWER(TRIM(user_message))),
        0
    ) AS additional_examples_needed

FROM public.assistant_training_logs

-- Consider only records having a valid human-labelled intent
WHERE actual_intent IS NOT NULL
  AND TRIM(actual_intent) <> ''

  -- Exclude empty user messages
  AND user_message IS NOT NULL
  AND TRIM(user_message) <> ''

-- Group messages according to their actual intent
GROUP BY actual_intent

-- Display only categories having fewer than 5 examples
HAVING COUNT(
    DISTINCT LOWER(TRIM(user_message))
) < 5

-- Show categories with the biggest data gaps first
ORDER BY
    unique_reviewed_examples ASC,
    actual_intent ASC;
