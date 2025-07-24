-- Tracks every individual call to an LLM, its token usage, and what it was for.
-- This table is designed as an immutable ledger for LLM cost-tracking.
CREATE TABLE IF NOT EXISTS llm_runs (
    llm_run_id                  TEXT PRIMARY KEY,
    llm_run_type                TEXT NOT NULL,
    llm_model_id                TEXT,
    
    -- Context / Input columns
    job_id                      TEXT,
    llm_prompt_document_id      TEXT,

    -- Token tracking
    llm_run_prompt_tokens       INTEGER,
    llm_run_completion_tokens   INTEGER,
    llm_run_thinking_tokens     INTEGER,
    llm_run_total_tokens        INTEGER,

    -- Polymorphic Association columns for the OUTPUT of the run
    assessment_id_link          TEXT,
    generated_document_id_link  TEXT,

    -- Define all foreign keys with SET NULL to preserve historical records
    FOREIGN KEY (llm_model_id) REFERENCES llm_models (model_id) ON DELETE SET NULL,
    FOREIGN KEY (job_id) REFERENCES job_details (job_id) ON DELETE SET NULL,
    FOREIGN KEY (llm_prompt_document_id) REFERENCES document_store (document_id) ON DELETE SET NULL,
    FOREIGN KEY (assessment_id_link) REFERENCES job_assessment (job_assessment_id) ON DELETE SET NULL,
    FOREIGN KEY (generated_document_id_link) REFERENCES document_store (document_id) ON DELETE SET NULL,

    -- Define all check constraints to ensure data integrity
    CONSTRAINT chk_llm_run_link CHECK (
        (llm_run_type = 'generate_job_assessment' AND assessment_id_link IS NOT NULL AND generated_document_id_link IS NULL)
        OR
        (llm_run_type IN ('generate_tailored_resume', 'generate_tailored_cover_letter') AND generated_document_id_link IS NOT NULL AND assessment_id_link IS NULL)
        OR
        (llm_run_type NOT IN ('generate_job_assessment', 'generate_tailored_resume', 'generate_tailored_cover_letter') AND assessment_id_link IS NULL AND generated_document_id_link IS NULL)
    )
);