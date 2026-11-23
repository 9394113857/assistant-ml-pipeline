
-- ============================================================
-- P1 TRAINING DATA AUDIT
-- SECTION 1: OVERALL RECORD RECONCILIATION
--
-- PURPOSE:
-- Understand the current quality of training labels.
--
-- READ ONLY:
-- This query only reads data.
-- No INSERT, UPDATE, DELETE or schema changes.
-- ============================================================

SELECT

    -- Total records in the training table
    COUNT(*) AS total_records,

    -- Records having a populated actual intent
    COUNT(*) FILTER (
        WHERE actual_intent IS NOT NULL
          AND TRIM(actual_intent) <> ''
    ) AS records_with_actual_intent,

    -- Records with both human-review audit fields populated
    COUNT(*) FILTER (
        WHERE reviewer_user_id IS NOT NULL
          AND reviewed_at IS NOT NULL
    ) AS fully_audited_records,

    -- Records labelled but missing one or both review fields
    COUNT(*) FILTER (
        WHERE actual_intent IS NOT NULL
          AND TRIM(actual_intent) <> ''
          AND (
              reviewer_user_id IS NULL
              OR reviewed_at IS NULL
          )
    ) AS labelled_but_not_fully_audited,

    -- Records without an actual intent label
    COUNT(*) FILTER (
        WHERE actual_intent IS NULL
           OR TRIM(actual_intent) = ''
    ) AS records_without_actual_intent

FROM public.assistant_training_logs;
