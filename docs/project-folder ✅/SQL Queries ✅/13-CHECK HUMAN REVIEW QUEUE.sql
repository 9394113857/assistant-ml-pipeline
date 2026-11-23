
-- ============================================================
-- P1 AUDIT - SECTION 5
-- CHECK HUMAN REVIEW QUEUE
--
-- PURPOSE:
-- Identify records that have not yet been reviewed.
-- Check whether the review queue contains all records.
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
    created_at,

    CASE
        WHEN actual_intent IS NULL
          OR TRIM(actual_intent) = ''
            THEN 'PENDING_LABEL'

        WHEN reviewer_user_id IS NULL
          OR reviewed_at IS NULL
            THEN 'PENDING_AUDIT'

        ELSE 'FULLY_REVIEWED'
    END AS review_status

FROM public.assistant_training_logs

WHERE actual_intent IS NULL
   OR TRIM(actual_intent) = ''
   OR reviewer_user_id IS NULL
   OR reviewed_at IS NULL

ORDER BY id ASC;
