-- Stores the analysis/assessment of a job against a specific resume.
CREATE TABLE IF NOT EXISTS job_assessment (
    -- Using a unique ID for the assessment itself allows for multiple assessments
    -- of the same job over time (e.g., updated resume or updated prompt).
    job_assessment_id                                       TEXT PRIMARY KEY,
    job_id                                              TEXT NOT NULL,
    job_assessment_timestamp                            INTEGER NOT NULL,
    job_assessment_rating                               TEXT,
    job_assessment_details                              TEXT,
    job_assessment_required_qualifications_matched_count    INTEGER,
    job_assessment_required_qualifications_count            INTEGER,
    job_assessment_additional_qualifications_matched_count  INTEGER,
    job_assessment_additional_qualifications_count          INTEGER,
    job_assessment_list_required_qualifications         TEXT,
    job_assessment_list_matched_required_qualifications TEXT,
    job_assessment_list_additional_qualifications       TEXT,
    job_assessment_list_matched_additional_qualifications TEXT,
    job_assessment_resume_document_id                   TEXT,
    job_assessment_prompt_document_id                   TEXT,

    -- Define Foreign Keys
    -- If a job is deleted, its assessments should also be deleted.
    FOREIGN KEY (job_id) REFERENCES job_details (job_id) ON DELETE CASCADE,
    -- If a resume is deleted, we might want to keep the assessment but nullify the link.
    FOREIGN KEY (job_assessment_resume_document_id) REFERENCES document_store (document_id) ON DELETE SET NULL,
    FOREIGN KEY (job_assessment_prompt_document_id) REFERENCES document_store (document_id) ON DELETE SET NULL
);