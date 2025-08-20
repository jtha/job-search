-- This is the many-to-many linking table.
-- It records every instance of a job being found during a specific run.
CREATE TABLE IF NOT EXISTS run_findings (
    job_run_id        TEXT NOT NULL,
    job_id            TEXT NOT NULL,
    
    -- Properties specific to this finding, like its rank on the page.
    job_run_page_num  INTEGER,
    job_run_rank      INTEGER,
    
    -- The primary key is the combination of the two foreign keys.
    -- This prevents logging the same job twice for the same run.
    PRIMARY KEY (job_run_id, job_id),
    
    -- Define Foreign Keys
    -- If a job_run is deleted, all its findings are automatically deleted.
    -- If a job_detail is deleted, all records of it being found are also deleted.
    FOREIGN KEY (job_run_id) REFERENCES job_runs (job_run_id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES job_details (job_id) ON DELETE CASCADE
);