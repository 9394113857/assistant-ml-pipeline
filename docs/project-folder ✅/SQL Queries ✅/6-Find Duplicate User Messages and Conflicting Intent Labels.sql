
-- ================================================================
-- QUERY NAME:
-- Find Duplicate User Messages and Conflicting Intent Labels
-- ================================================================
--
-- PURPOSE:
-- Identify repeated user messages in the ML training dataset.
--
-- This query helps us find:
-- 1. Messages appearing multiple times.
-- 2. Messages assigned to different intent categories.
-- 3. Repeated examples that may overweight a particular intent.
-- 4. Potentially conflicting labels that need admin review.
--
-- SOURCE TABLE:
-- public.assistant_training_logs
--
-- IMPORTANT SOURCE COLUMNS:
--
-- user_message:
--     Original message entered by the user.
--
-- actual_intent:
--     Intent category assigned to the training record.
--
-- EXAMPLE:
--     "Show me laptops"
--
--     Record 1 -> show_products
--     Record 2 -> product_category
--
--     This is a possible conflicting-label case that needs
--     semantic review before using both records for training.
--
-- NORMALIZATION:
--     LOWER(TRIM(user_message))
--
--     LOWER() converts text to lowercase.
--     TRIM() removes leading and trailing spaces.
--
--     This helps identify messages that differ only by
--     capitalization or surrounding spaces.
--
-- OUTPUT COLUMNS:
--
-- normalized_message:
--     User message after lowercase and trimming.
--
-- total_records:
--     Total number of records containing this message.
--
-- intent_count:
--     Number of distinct intent categories assigned.
--
-- assigned_intents:
--     All distinct intent labels found for this message.
--
-- WHY THIS QUERY IS NEEDED:
--     Duplicate messages can give repeated examples extra weight.
--     Conflicting labels can teach the model contradictory patterns.
--     We need to inspect these records before finalizing P1.
--
-- IMPORTANT:
--     A duplicate is not automatically incorrect.
--     Different labels are not automatically incorrect either.
--     Review the original context and intended meaning before
--     deciding whether a label should be corrected.
--
-- QUERY TYPE:
--     READ ONLY.
--     No INSERT, UPDATE, DELETE, or database modification.
--
-- ================================================================

SELECT

    -- Normalize the user message so that capitalization
    -- and leading/trailing spaces do not create false differences.
    LOWER(TRIM(user_message)) AS normalized_message,

    -- Count all records containing this normalized message.
    COUNT(*) AS total_records,

    -- Count how many distinct intent categories were assigned.
    -- A value greater than 1 indicates possible label conflict.
    COUNT(DISTINCT actual_intent) AS intent_count,

    -- Combine all distinct intent labels into one readable field.
    -- This helps us compare labels without opening every record.
    STRING_AGG(
        DISTINCT actual_intent,
        ', '
        ORDER BY actual_intent
    ) AS assigned_intents

FROM public.assistant_training_logs

-- Include only records with a valid, non-empty human-assigned label.
WHERE actual_intent IS NOT NULL
  AND TRIM(actual_intent) <> ''

  -- Exclude records without an actual user message.
  AND user_message IS NOT NULL
  AND TRIM(user_message) <> ''

-- Group records by their normalized message.
-- Each output row represents one distinct normalized message.
GROUP BY LOWER(TRIM(user_message))

-- Return only messages that occur more than once.
HAVING COUNT(*) > 1

-- Show conflicting labels first, followed by frequently repeated
-- messages, so that the most important cases are easy to inspect.
ORDER BY
    intent_count DESC,
    total_records DESC;

-- ================================================================
-- EXPECTED RESULT:
--
-- Example:
--
-- normalized_message | total_records | intent_count | assigned_intents
-- -------------------|---------------|--------------|------------------
-- show me laptops    | 3             | 2            | product_category,
--                   |               |              | show_products
--
-- INTERPRETATION:
--
-- intent_count = 1:
--     Same message has repeated records but one consistent label.
--
-- intent_count > 1:
--     Same normalized message has multiple labels.
--     Requires manual inspection.
--
-- NEXT STEP:
--     Inspect the results and verify labels through the
--     authenticated admin review process where necessary.
-- ================================================================
