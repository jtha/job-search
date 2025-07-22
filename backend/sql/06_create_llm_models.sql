-- Stores details and costs for different LLM models available for use.
CREATE TABLE IF NOT EXISTS llm_models (
    model_id                TEXT PRIMARY KEY,
    model_name              TEXT NOT NULL,
    model_provider          TEXT,
    model_cpmt_prompt       REAL, -- Cost Per Million Tokens (Prompt)
    model_cpmt_completion   REAL, -- Cost Per Million Tokens (Completion)
    model_cpmt_thinking     REAL  -- Cost Per Million Tokens (Thinking)
);