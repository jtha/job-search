-- Stores raw documents, like resumes or job-specific cover letters, in Markdown format.
CREATE TABLE IF NOT EXISTS document_store (
    document_id         TEXT PRIMARY KEY,
    document_name       TEXT NOT NULL,
    document_timestamp  INTEGER NOT NULL,
    document_markdown   TEXT
);