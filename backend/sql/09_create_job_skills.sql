-- Stores job skills details, linking jobs to required skills and the qualification results
CREATE TABLE IF NOT EXISTS job_skills (
    job_skill_id                TEXT PRIMARY KEY,
    job_id                      TEXT NOT NULL,
    job_skills_atomic_string    TEXT NOT NULL,
    job_skills_type             TEXT NOT NULL,
    job_skills_match_reasoning  TEXT,
    job_skills_match            BOOLEAN,
    job_skills_resume_id         TEXT,

    FOREIGN KEY (job_id) REFERENCES job_details (job_id) ON DELETE NO ACTION
);