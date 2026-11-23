
-- ================================================================
-- QUERY: P1 TRAINING DATA RECONCILIATION
-- ================================================================
--
-- PURPOSE:
-- Reconcile the aggregate count with the individual record export.
-- Also inspect prediction/actual-label differences by model version.
--
-- SOURCE:
-- public.assistant_training_logs
--
-- OUTPUT SECTION 1:
-- total_labelled_records:
--     Number of records with a populated actual_intent.
--
-- complete_audit_records:
--     Records with BOTH reviewer_user_id and reviewed_at.
--
-- missing_audit_records:
--     Records missing either reviewer audit field.
--
-- prediction_matches:
--     Records where predicted_intent equals actual_intent.
--
-- prediction_mismatches:
--     Records where predicted_intent differs from actual_intent.
--
-- OUTPUT SECTION 2:
-- model_version:
--     Rule/model version associated with the prediction.
--
-- labelled_records:
--     Number of labelled records for that version.
--
-- mismatches:
--     Number of records where prediction and actual label differ.
--
-- READ ONLY:
-- No INSERT, UPDATE, DELETE or database modification.
-- ================================================================


-- SECTION 1: OVERALL RECONCILIATION

SELECT

    COUNT(*) AS total_labelled_records,

    COUNT(*) FILTER (
        WHERE reviewer_user_id IS NOT NULL
          AND reviewed_at IS NOT NULL
    ) AS complete_audit_records,

    COUNT(*) FILTER (
        WHERE reviewer_user_id IS NULL
           OR reviewed_at IS NULL
    ) AS missing_audit_records,

    COUNT(*) FILTER (
        WHERE LOWER(TRIM(predicted_intent))
              = LOWER(TRIM(actual_intent))
    ) AS prediction_matches,

    COUNT(*) FILTER (
        WHERE LOWER(TRIM(predicted_intent))
              <> LOWER(TRIM(actual_intent))
    ) AS prediction_mismatches

FROM public.assistant_training_logs

WHERE actual_intent IS NOT NULL
  AND TRIM(actual_intent) <> ''
  AND user_message IS NOT NULL
  AND TRIM(user_message) <> '';


-- SECTION 2: BREAKDOWN BY MODEL VERSION

SELECT

    model_version,

    COUNT(*) AS labelled_records,

    COUNT(*) FILTER (
        WHERE LOWER(TRIM(predicted_intent))
              = LOWER(TRIM(actual_intent))
    ) AS prediction_matches,

    COUNT(*) FILTER (
        WHERE LOWER(TRIM(predicted_intent))
              <> LOWER(TRIM(actual_intent))
    ) AS prediction_mismatches,

    COUNT(*) FILTER (
        WHERE reviewer_user_id IS NOT NULL
          AND reviewed_at IS NOT NULL
    ) AS complete_audit_records,

    MIN(created_at) AS first_record_created,

    MAX(created_at) AS latest_record_created

FROM public.assistant_training_logs

WHERE actual_intent IS NOT NULL
  AND TRIM(actual_intent) <> ''
  AND user_message IS NOT NULL
  AND TRIM(user_message) <> ''

GROUP BY model_version

ORDER BY model_version;
