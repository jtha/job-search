-- Stores the master list of all unique jobs ever discovered across all runs.
CREATE TABLE IF NOT EXISTS job_details (
    job_id                  TEXT PRIMARY KEY,
    job_title               TEXT,
    job_company             TEXT,
    job_location            TEXT,
    job_salary              TEXT,
    job_url                 TEXT,
    job_url_direct          TEXT,
    job_description         TEXT,
    job_applied             INTEGER DEFAULT 0 CHECK (job_applied IN (0, 1)),
    job_applied_timestamp   INTEGER
);