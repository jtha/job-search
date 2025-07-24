-- Stores the master list of job_ids to skip during job processing.
CREATE TABLE IF NOT EXISTS job_quarantine (
    job_quarantine_id TEXT PRIMARY KEY,
    job_id                  TEXT NOT NULL,
    job_quarantine_reason   TEXT,
    job_quarantine_timestamp INTEGER DEFAULT (strftime('%s', 'now')),

    -- Define foreign key to job_details table with ON DELETE CASCADE
    FOREIGN KEY (job_id) REFERENCES job_details (job_id) ON DELETE CASCADE
);