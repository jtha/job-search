-- Stores a record of each time the job crawler is executed.
-- This is the "parent" table for a crawling event.
CREATE TABLE IF NOT EXISTS job_runs (
    job_run_id          TEXT PRIMARY KEY,
    job_run_timestamp   INTEGER NOT NULL,
    job_run_keywords    TEXT
);