
CREATE TABLE IF NOT EXISTS prompt (
    prompt_id TEXT PRIMARY KEY,
    llm_run_type TEXT,
    model_id TEXT,
    prompt_system_prompt TEXT,
    prompt_template TEXT,
    prompt_temperature REAL,
    prompt_response_schema TEXT,
    prompt_created_at INTEGER,
    prompt_thinking_budget INTEGER,
    FOREIGN KEY (model_id) REFERENCES llm_models(model_id)
);
