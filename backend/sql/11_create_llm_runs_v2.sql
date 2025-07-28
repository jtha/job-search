CREATE TABLE IF NOT EXISTS llm_runs_v2 (
    llm_run_id TEXT PRIMARY KEY,
    job_id TEXT,
    llm_run_type TEXT,
    llm_run_model_id TEXT,
    llm_run_system_prompt_id TEXT,
    llm_run_input TEXT,
    llm_run_output TEXT,
    llm_run_input_tokens INTEGER,
    llm_run_output_tokens INTEGER,
    llm_run_thinking_tokens INTEGER,
    llm_run_total_tokens INTEGER,
    llm_run_start REAL,
    llm_run_end REAL,
    FOREIGN KEY (job_id) REFERENCES job_details(job_id),
    FOREIGN KEY (llm_run_model_id) REFERENCES llm_models(model_id),
    FOREIGN KEY (llm_run_system_prompt_id) REFERENCES prompt(prompt_id)
);
