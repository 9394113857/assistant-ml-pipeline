
-- ============================================================
-- QUERY: VERIFY HUMAN-REVIEWED TRAINING DATA
-- ============================================================
--
-- PURPOSE:
-- Check whether human-labelled intent records have complete
-- reviewer audit information in Supabase.
--
-- TABLE:
-- public.assistant_training_logs
--
-- IMPORTANT COLUMNS:
--
-- actual_intent:
--     The intent category assigned by a human reviewer.
--
-- reviewer_user_id:
--     The ID of the administrator who reviewed the record.
--
-- reviewed_at:
--     The date and time when the record was reviewed.
--
-- user_message:
--     The original message entered by the user.
--
-- ============================================================
-- WHAT THIS QUERY CHECKS:
--
-- 1. labelled_records:
--    Total human-labelled records for each intent.
--
-- 2. audited_records:
--    Records having BOTH reviewer_user_id and reviewed_at.
--
-- 3. missing_audit_records:
--    Records missing either reviewer_user_id or reviewed_at.
--
-- 4. unique_messages:
--    Number of unique messages for each intent.
--    LOWER() ignores uppercase/lowercase differences.
--    TRIM() removes unnecessary spaces.
--
-- ============================================================
-- WHY WE NEED THIS:
--
-- Our ML pipeline uses actual_intent as its training label.
--
-- Before trusting these labels, we need to inspect their
-- human-review audit information.
--
-- This helps identify whether the training dataset has
-- properly traceable review records.
--
-- ============================================================
-- EXPECTED OUTPUT:
--
-- actual_intent | labelled_records | audited_records
--               | missing_audit_records | unique_messages
--
-- One row per human-labelled intent category.
--
-- ============================================================
-- IMPORTANT:
-- THIS IS A READ-ONLY SELECT QUERY.
-- IT DOES NOT INSERT, UPDATE OR DELETE ANY DATA.
-- ============================================================


SELECT

    -- Human-reviewed intent category
    actual_intent,

    -- Total number of records assigned to this intent
    COUNT(*) AS labelled_records,

    -- Count records where BOTH audit fields are populated
    COUNT(*) FILTER (
        WHERE reviewer_user_id IS NOT NULL
          AND reviewed_at IS NOT NULL
    ) AS audited_records,

    -- Count records where either audit field is missing
    COUNT(*) FILTER (
        WHERE reviewer_user_id IS NULL
           OR reviewed_at IS NULL
    ) AS missing_audit_records,

    -- Count unique messages after normalizing case and spaces
    COUNT(
        DISTINCT LOWER(TRIM(user_message))
    ) AS unique_messages


-- Source table containing Assistant training records
FROM public.assistant_training_logs


-- Consider only records with a valid human-assigned intent
WHERE actual_intent IS NOT NULL

  -- Exclude blank intent labels
  AND TRIM(actual_intent) <> ''

  -- Exclude missing user messages
  AND user_message IS NOT NULL

  -- Exclude blank user messages
  AND TRIM(user_message) <> ''


-- Group records by their human-reviewed intent category
GROUP BY actual_intent


-- Display categories alphabetically for easier inspection
ORDER BY actual_intent;
