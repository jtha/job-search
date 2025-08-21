from typing import Optional
import aiosqlite

from .utilities import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

DB_FILE = "job_tracker.db"
SQL_DIR = "sql"

class Database:
    _instance = None
    _connection = None

    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance.connect()
        return cls._instance

    async def connect(self):
        if self._connection is None:
            self._connection = await aiosqlite.connect(DB_FILE, timeout=3)
            await self._connection.execute("PRAGMA journal_mode=WAL;")
            await self._connection.execute("PRAGMA foreign_keys = ON;")
            self._connection.row_factory = aiosqlite.Row
            logger.info("Database connection established.")

    async def close(self):
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database connection closed.")

    @property
    def connection(self):
        return self._connection

async def get_db():
    db_instance = await Database.get_instance()
    if db_instance.connection is None:
        raise RuntimeError("Database connection is not initialized. Did you forget to start the app or call Database.get_instance()?")
    return db_instance.connection

async def upsert_job_run(job_run_id: str, job_run_timestamp: int, job_run_keywords: Optional[str] = None):
    """
    Upserts a record into the job_runs table.
    If a record with the same job_run_id exists, it will be replaced.
    """
    db = await get_db()
    await db.execute(
        """
        INSERT INTO job_runs (job_run_id, job_run_timestamp, job_run_keywords)
        VALUES (?, ?, ?)
        ON CONFLICT(job_run_id) DO UPDATE SET
            job_run_timestamp=excluded.job_run_timestamp,
            job_run_keywords=excluded.job_run_keywords;
        """,
        (job_run_id, job_run_timestamp, job_run_keywords)
    )
    await db.commit()
    # logger.info(f"Upserted job_run: {job_run_id}")


# --- Upsert for job_details ---
async def upsert_job_detail(
    job_id: str,
    job_title: Optional[str] = None,
    job_company: Optional[str] = None,
    job_location: Optional[str] = None,
    job_salary: Optional[str] = None,
    job_url: Optional[str] = None,
    job_url_direct: Optional[str] = None,
    job_description: Optional[str] = None,
    job_applied: int = 0,
    job_applied_timestamp: Optional[int] = None
):
    """
    Upserts a record into the job_details table.
    """
    db = await get_db()
    await db.execute(
        """
        INSERT INTO job_details (
            job_id, job_title, job_company, job_location, job_salary, job_url, job_url_direct, job_description, job_applied, job_applied_timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_id) DO NOTHING;
        """,
        (job_id, job_title, job_company, job_location, job_salary, job_url, job_url_direct, job_description, job_applied, job_applied_timestamp)
    )
    await db.commit()
    # logger.info(f"Inserted job_detail (if not exists): {job_id}")

# Insert new function to upsert job_description to job_details table

async def upsert_job_description(job_id: str, job_description: str):
    """
    Upserts the job_description for a given job_id in the job_details table.
    If the job_id does not exist, it will insert a new row with only job_id and job_description.
    If the job_id exists, it will update the job_description.
    """
    db = await get_db()
    await db.execute(
        """
        INSERT INTO job_details (job_id, job_description)
        VALUES (?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
            job_description=excluded.job_description;
        """,
        (job_id, job_description)
    )
    await db.commit()
    # logger.info(f"Upserted job_description for job_id: {job_id}")

# --- Update applied status for a job ---
async def update_job_applied(
    job_id: str,
    applied: int = 1,
    applied_timestamp: Optional[int] = None,
) -> int:
    """
    Updates job_details.applied state for a given job_id.
    - applied must be 0 or 1 (schema enforces this). Defaults to 1.
    - applied_timestamp defaults to current epoch seconds if None.
    Returns the number of rows updated (0 if job_id not found).
    """
    # Normalize applied to 0/1 defensively
    applied_val = 1 if applied == 1 else 0
    db = await get_db()
    cursor = await db.execute(
        """
        UPDATE job_details
        SET job_applied = ?,
            job_applied_timestamp = COALESCE(?, CAST(strftime('%s','now') AS INTEGER))
        WHERE job_id = ?
        """,
        (applied_val, applied_timestamp, job_id),
    )
    await db.commit()
    logger.info(f"Updated job_applied={applied_val} for job_id: {job_id}")
    return cursor.rowcount or 0

async def clear_job_applied(job_id: str) -> int:
    """
    Clears the applied status for a job: sets job_applied=0 and job_applied_timestamp=NULL.
    Returns number of rows updated.
    """
    db = await get_db()
    cursor = await db.execute(
        """
        UPDATE job_details
        SET job_applied = 0,
            job_applied_timestamp = NULL
        WHERE job_id = ?
        """,
        (job_id,),
    )
    await db.commit()
    logger.info(f"Cleared job_applied for job_id: {job_id}")
    return cursor.rowcount or 0

# --- Upsert for document_store ---
async def upsert_document(
    document_id: str,
    document_name: str,
    document_timestamp: int,
    document_markdown: Optional[str] = None,
    document_job_id_reference: Optional[str] = None,
    document_job_type: Optional[str] = None
):
    """
    Upserts a record into the document_store table.
    """
    db = await get_db()
    await db.execute(
        """
        INSERT INTO document_store (
            document_id, document_name, document_timestamp, document_markdown
        ) VALUES (?, ?, ?, ?)
        ON CONFLICT(document_id) DO UPDATE SET
            document_name=excluded.document_name,
            document_timestamp=excluded.document_timestamp,
            document_markdown=excluded.document_markdown;
        """,
        (document_id, document_name, document_timestamp, document_markdown)
    )
    await db.commit()
    # logger.info(f"Upserted document: {document_id}")

# --- Upsert for run_findings ---
async def upsert_run_finding(
    job_run_id: str,
    job_id: str,
    job_run_page_num: Optional[int] = None,
    job_run_rank: Optional[int] = None
):
    """
    Upserts a record into the run_findings table.
    """
    db = await get_db()
    await db.execute(
        """
        INSERT INTO run_findings (
            job_run_id, job_id, job_run_page_num, job_run_rank
        ) VALUES (?, ?, ?, ?)
        ON CONFLICT(job_run_id, job_id) DO UPDATE SET
            job_run_page_num=excluded.job_run_page_num,
            job_run_rank=excluded.job_run_rank;
        """,
        (job_run_id, job_id, job_run_page_num, job_run_rank)
    )
    await db.commit()
    # logger.info(f"Upserted run_finding: ({job_run_id}, {job_id})")

async def upsert_llm_model(
    model_id: str,
    model_name: str,
    model_provider: Optional[str] = None,
    model_cpmt_prompt: Optional[float] = None,
    model_cpmt_completion: Optional[float] = None,
    model_cpmt_thinking: Optional[float] = None
):
    """
    Upserts a record into the llm_models table.
    """
    db = await get_db()
    await db.execute(
        """
        INSERT INTO llm_models (
            model_id, model_name, model_provider, model_cpmt_prompt, model_cpmt_completion, model_cpmt_thinking
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(model_id) DO UPDATE SET
            model_name=excluded.model_name,
            model_provider=excluded.model_provider,
            model_cpmt_prompt=excluded.model_cpmt_prompt,
            model_cpmt_completion=excluded.model_cpmt_completion,
            model_cpmt_thinking=excluded.model_cpmt_thinking;
        """,
        (model_id, model_name, model_provider, model_cpmt_prompt, model_cpmt_completion, model_cpmt_thinking)
    )
    await db.commit()
    # logger.info(f"Upserted llm_model: {model_id}")

# --- Upsert for llm_runs ---
async def upsert_llm_run(
    llm_run_id: str,
    llm_run_type: str,
    llm_model_id: Optional[str] = None,
    job_id: Optional[str] = None,
    llm_prompt_document_id: Optional[str] = None,
    llm_run_prompt_tokens: Optional[int] = None,
    llm_run_completion_tokens: Optional[int] = None,
    llm_run_thinking_tokens: Optional[int] = None,
    llm_run_total_tokens: Optional[int] = None,
    assessment_id_link: Optional[str] = None,
    generated_document_id_link: Optional[str] = None
):
    """
    Upserts a record into the llm_runs table.
    """
    db = await get_db()
    await db.execute(
        """
        INSERT INTO llm_runs (
            llm_run_id, llm_run_type, llm_model_id, job_id, llm_prompt_document_id,
            llm_run_prompt_tokens, llm_run_completion_tokens, llm_run_thinking_tokens, llm_run_total_tokens,
            assessment_id_link, generated_document_id_link
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(llm_run_id) DO UPDATE SET
            llm_run_type=excluded.llm_run_type,
            llm_model_id=excluded.llm_model_id,
            job_id=excluded.job_id,
            llm_prompt_document_id=excluded.llm_prompt_document_id,
            llm_run_prompt_tokens=excluded.llm_run_prompt_tokens,
            llm_run_completion_tokens=excluded.llm_run_completion_tokens,
            llm_run_thinking_tokens=excluded.llm_run_thinking_tokens,
            llm_run_total_tokens=excluded.llm_run_total_tokens,
            assessment_id_link=excluded.assessment_id_link,
            generated_document_id_link=excluded.generated_document_id_link;
        """,
        (
            llm_run_id, llm_run_type, llm_model_id, job_id, llm_prompt_document_id,
            llm_run_prompt_tokens, llm_run_completion_tokens, llm_run_thinking_tokens, llm_run_total_tokens,
            assessment_id_link, generated_document_id_link
        )
    )
    await db.commit()
    # logger.info(f"Upserted llm_run: {llm_run_id}")

# --- Upsert for job_quarantine ---
async def upsert_job_quarantine(
    job_quarantine_id: str,
    job_id: str,
    job_quarantine_reason: str = "",
    job_quarantine_timestamp: Optional[int] = None
):
    """
    Upserts a record into the job_quarantine table.
    If a record with the same job_quarantine_id exists, it will be replaced.
    """
    db = await get_db()
    await db.execute(
        """
        INSERT INTO job_quarantine (
            job_quarantine_id, job_id, job_quarantine_reason, job_quarantine_timestamp
        ) VALUES (?, ?, ?, COALESCE(?, strftime('%s', 'now')))
        ON CONFLICT(job_quarantine_id) DO UPDATE SET
            job_id=excluded.job_id,
            job_quarantine_reason=excluded.job_quarantine_reason,
            job_quarantine_timestamp=excluded.job_quarantine_timestamp;
        """,
        (job_quarantine_id, job_id, job_quarantine_reason, job_quarantine_timestamp)
    )
    await db.commit()
    logger.info(f"Upserted job_quarantine: {job_quarantine_id}")

# --- Upsert for job_skills ---
async def upsert_job_skills(
    job_skill_id: str,
    job_id: str,
    job_skills_atomic_string: str,
    job_skills_type: str,
    job_skills_match_reasoning: Optional[str] = None,
    job_skills_match: Optional[bool] = None,
    job_skills_resume_id: Optional[str] = None
):
    """
    Upserts a record into the job_skills table.
    If a record with the same job_skill_id exists, it will be replaced.
    """
    db = await get_db()
    await db.execute(
        """
        INSERT INTO job_skills (
            job_skill_id, job_id, job_skills_atomic_string, job_skills_type, job_skills_match_reasoning, job_skills_match, job_skills_resume_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_skill_id) DO UPDATE SET
            job_id=excluded.job_id,
            job_skills_atomic_string=excluded.job_skills_atomic_string,
            job_skills_type=excluded.job_skills_type,
            job_skills_match_reasoning=excluded.job_skills_match_reasoning,
            job_skills_match=excluded.job_skills_match,
            job_skills_resume_id=excluded.job_skills_resume_id;
        """,
        (
            job_skill_id,
            job_id,
            job_skills_atomic_string,
            job_skills_type,
            job_skills_match_reasoning,
            job_skills_match,
            job_skills_resume_id
        )
    )
    await db.commit()
    # logger.info(f"Upserted job_skill: {job_skill_id}")

# --- Upsert for prompts ---
async def upsert_prompt(
    prompt_id: str,
    llm_run_type: Optional[str] = None,
    model_id: Optional[str] = None,
    prompt_system_prompt: Optional[str] = None,
    prompt_template: Optional[str] = None,
    prompt_temperature: Optional[float] = None,
    prompt_response_schema: Optional[str] = None,
    prompt_created_at: Optional[int] = None,
    prompt_thinking_budget: Optional[int] = None
):
    """
    Upserts a record into the prompt table.
    If a record with the same prompt_id exists, it will be replaced.
    """
    db = await get_db()
    await db.execute(
        """
        INSERT INTO prompt (
            prompt_id, llm_run_type, model_id, prompt_system_prompt, prompt_template, prompt_temperature,
            prompt_response_schema, prompt_created_at, prompt_thinking_budget
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(prompt_id) DO UPDATE SET
            llm_run_type=excluded.llm_run_type,
            model_id=excluded.model_id,
            prompt_system_prompt=excluded.prompt_system_prompt,
            prompt_template=excluded.prompt_template,
            prompt_temperature=excluded.prompt_temperature,
            prompt_response_schema=excluded.prompt_response_schema,
            prompt_created_at=excluded.prompt_created_at,
            prompt_thinking_budget=excluded.prompt_thinking_budget;
        """,
        (
            prompt_id,
            llm_run_type,
            model_id,
            prompt_system_prompt,
            prompt_template,
            prompt_temperature,
            prompt_response_schema,
            prompt_created_at,
            prompt_thinking_budget
        )
    )
    await db.commit()
    # logger.info(f"Upserted prompt: {prompt_id}")

# --- Upsert for llm_runs_v2 ---
async def upsert_llm_run_v2(
    llm_run_id: str,
    job_id: Optional[str] = None,
    llm_run_type: Optional[str] = None,
    llm_run_model_id: Optional[str] = None,
    llm_run_system_prompt_id: Optional[str] = None,
    llm_run_input: Optional[str] = None,
    llm_run_output: Optional[str] = None,
    llm_run_input_tokens: Optional[int] = None,
    llm_run_output_tokens: Optional[int] = None,
    llm_run_thinking_tokens: Optional[int] = None,
    llm_run_total_tokens: Optional[int] = None,
    llm_run_start: Optional[float] = None,
    llm_run_end: Optional[float] = None
):
    """
    Upserts a record into the llm_runs_v2 table.
    If a record with the same llm_run_id exists, it will be replaced.
    """
    db = await get_db()
    await db.execute(
        """
        INSERT INTO llm_runs_v2 (
            llm_run_id, job_id, llm_run_type, llm_run_model_id, llm_run_system_prompt_id, llm_run_input, llm_run_output,
            llm_run_input_tokens, llm_run_output_tokens, llm_run_thinking_tokens, llm_run_total_tokens,
            llm_run_start, llm_run_end
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(llm_run_id) DO UPDATE SET
            job_id=excluded.job_id,
            llm_run_type=excluded.llm_run_type,
            llm_run_model_id=excluded.llm_run_model_id,
            llm_run_system_prompt_id=excluded.llm_run_system_prompt_id,
            llm_run_input=excluded.llm_run_input,
            llm_run_output=excluded.llm_run_output,
            llm_run_input_tokens=excluded.llm_run_input_tokens,
            llm_run_output_tokens=excluded.llm_run_output_tokens,
            llm_run_thinking_tokens=excluded.llm_run_thinking_tokens,
            llm_run_total_tokens=excluded.llm_run_total_tokens,
            llm_run_start=excluded.llm_run_start,
            llm_run_end=excluded.llm_run_end;
        """,
        (
            llm_run_id,
            job_id,
            llm_run_type,
            llm_run_model_id,
            llm_run_system_prompt_id,
            llm_run_input,
            llm_run_output,
            llm_run_input_tokens,
            llm_run_output_tokens,
            llm_run_thinking_tokens,
            llm_run_total_tokens,
            llm_run_start,
            llm_run_end
        )
    )
    await db.commit()
    # logger.info(f"Upserted llm_run_v2: {llm_run_id}")

async def get_job_details() -> list[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM job_details") as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_job_detail_by_id(job_id: str) -> Optional[dict]:
    """
    Returns a single job_details row for the given job_id, or None if not found.
    """
    db = await get_db()
    async with db.execute("SELECT * FROM job_details WHERE job_id = ?", (job_id,)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_document_store() -> list[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM document_store") as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_llm_models() -> list[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM llm_models") as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_document_prompt_generate_job_assessment() -> dict:
    """
    Returns the prompt for generating job assessment.
    """
    db = await get_db()
    async with db.execute("SELECT document_id, document_markdown FROM document_store WHERE document_name = 'prompt_generate_job_assessment' ORDER BY document_timestamp DESC") as cursor:
        row = await cursor.fetchone()
        if row:
            return {"document_id": row["document_id"], "document_markdown": row["document_markdown"]}
        else:
            logger.warning("No job assessment prompt found in document_store.")
            return {"document_id": None, "document_markdown": None}

async def get_document_master_resume_json() -> dict:
    """
    Returns the master resume JSON content.
    """
    db = await get_db()
    async with db.execute("SELECT document_id, document_markdown FROM document_store WHERE document_name = 'master_resume_json' ORDER BY document_timestamp DESC") as cursor:
        row = await cursor.fetchone()
        if row:
            return {"document_id": row["document_id"], "document_markdown": row["document_markdown"]}
        else:
            logger.warning("No master resume found in document_store.")
            return {"document_id": None, "document_markdown": None}
        
async def get_document_master_resume() -> dict:
    """
    Returns the master resume markdown content.
    """
    db = await get_db()
    async with db.execute("SELECT document_id, document_markdown FROM document_store WHERE document_name = 'master_resume' ORDER BY document_timestamp DESC") as cursor:
        row = await cursor.fetchone()
        if row:
            return {"document_id": row["document_id"], "document_markdown": row["document_markdown"]}
        else:
            logger.warning("No master resume found in document_store.")
            return {"document_id": None, "document_markdown": None}
        
async def get_job_quarantine() -> list[str]:
    db = await get_db()
    async with db.execute("SELECT DISTINCT job_id FROM job_quarantine") as cursor:
        rows = await cursor.fetchall()
        if not rows:
            return []
        return [row["job_id"] for row in rows]

async def is_job_quarantined(job_id: str) -> bool:
    """
    Returns True if the given job_id exists in job_quarantine.
    """
    db = await get_db()
    async with db.execute("SELECT 1 FROM job_quarantine WHERE job_id = ? LIMIT 1", (job_id,)) as cursor:
        row = await cursor.fetchone()
        return row is not None

async def get_last_assessed_at(job_id: str) -> Optional[int]:
    """Return the latest llm_run_end (epoch seconds) for a job_id from llm_runs_v2, or None."""
    db = await get_db()
    async with db.execute(
        "SELECT MAX(CAST(llm_run_end AS INTEGER)) AS last_ts FROM llm_runs_v2 WHERE job_id = ?",
        (job_id,),
    ) as cursor:
        row = await cursor.fetchone()
        if row and row["last_ts"] is not None:
            return int(row["last_ts"])
        return None

async def get_latest_quarantine(job_id: str) -> Optional[dict]:
    """Return the most recent quarantine record for a job_id with reason and timestamp."""
    db = await get_db()
    async with db.execute(
        """
        SELECT job_quarantine_reason, job_quarantine_timestamp
        FROM job_quarantine
        WHERE job_id = ?
        ORDER BY job_quarantine_timestamp DESC
        LIMIT 1
        """,
        (job_id,),
    ) as cursor:
        row = await cursor.fetchone()
        if row:
            return {
                "job_quarantine_reason": row["job_quarantine_reason"],
                "job_quarantine_timestamp": row["job_quarantine_timestamp"],
            }
        return None
    
async def get_job_ids_without_assessment() -> list[dict]:
    """
    Returns a list of job_id values from job_details where job_assessment_id is NULL or empty.
    """
    quarantine_list = await get_job_quarantine()

    db = await get_db()
    async with db.execute("SELECT jd.job_id, jd.job_description from job_details jd LEFT JOIN job_assessment ja ON jd.job_id = ja.job_id WHERE ja.job_assessment_id IS NULL AND jd.job_description IS NOT NULL AND jd.job_description != ''") as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows if row["job_id"] not in quarantine_list]

async def get_job_skills() -> list[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM job_skills") as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_job_skills_for_job(job_id: str) -> list[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM job_skills WHERE job_id = ?", (job_id,)) as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_prompts() -> list[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM prompt") as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
async def get_latest_prompt(llm_run_type: str) -> Optional[dict]:
    """
    Returns the latest prompt configuration for a given llm_run_type.
    """
    db = await get_db()
    async with db.execute("""
        SELECT * FROM prompt 
        WHERE llm_run_type = ? 
        ORDER BY prompt_created_at DESC 
        LIMIT 1
    """, (llm_run_type,)) as cursor:
        row = await cursor.fetchone()
        if row:
            return dict(row)
        else:
            logger.warning(f"No prompt found for llm_run_type: {llm_run_type}")
            return None

async def get_llm_runs_v2() -> list[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM llm_runs_v2") as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
async def get_recent_assessed_jobs(days_back: int = 5, limit: int = 200) -> list[dict]:
    """
    Returns jobs that have been assessed in the last `days_back` days based on llm_runs_v2.llm_run_end.
    - Only includes job_ids that exist in job_skills (i.e., have an assessment result stored).
    - Aggregates llm_runs_v2 by job_id to get the latest llm_run_end as assessment_time.
    - Joins job_details to enrich output; returns latest first.
    Assumes llm_run_end is epoch seconds.
    """
    db = await get_db()
    # Compute the epoch seconds cutoff in SQLite to avoid clock skew between app and DB.
    async with db.execute(
        """
        WITH latest_assessment AS (
            SELECT
                job_id,
                MAX(CAST(llm_run_end AS INTEGER)) AS assessment_time
            FROM llm_runs_v2
            WHERE llm_run_end IS NOT NULL
            GROUP BY job_id
        ),
        cutoff AS (
            SELECT CAST(strftime('%s','now') AS INTEGER) - (? * 86400) AS since_ts
        )
        SELECT
            jd.*, 
            la.assessment_time AS last_assessed_at
        FROM latest_assessment la
        INNER JOIN job_skills js ON js.job_id = la.job_id
        INNER JOIN job_details jd ON jd.job_id = la.job_id
        CROSS JOIN cutoff c
        WHERE la.assessment_time >= c.since_ts
        GROUP BY jd.job_id
        ORDER BY la.assessment_time DESC
        LIMIT ?
        """,
        (days_back, limit),
    ) as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_recent_job_skills(days_back: int = 5, limit: int = 200) -> list[dict]:
    """
    Returns job_skills rows for jobs that have been assessed in the last `days_back` days.
    The set of job_ids considered is limited to the most recently assessed jobs (same logic as get_recent_assessed_jobs),
    capped by `limit`. All job_skills rows for those job_ids are returned.
    """
    db = await get_db()
    async with db.execute(
        """
        WITH latest_assessment AS (
            SELECT
                job_id,
                MAX(CAST(llm_run_end AS INTEGER)) AS assessment_time
            FROM llm_runs_v2
            WHERE llm_run_end IS NOT NULL
            GROUP BY job_id
        ),
        cutoff AS (
            SELECT CAST(strftime('%s','now') AS INTEGER) - (? * 86400) AS since_ts
        ),
        recent_jobs AS (
            SELECT la.job_id
            FROM latest_assessment la
            INNER JOIN job_skills js ON js.job_id = la.job_id
            CROSS JOIN cutoff c
            WHERE la.assessment_time >= c.since_ts
            GROUP BY la.job_id
            ORDER BY la.assessment_time DESC
            LIMIT ?
        )
        SELECT js.*
        FROM job_skills js
        INNER JOIN recent_jobs r ON r.job_id = js.job_id
        ORDER BY js.job_id
        """,
        (days_back, limit),
    ) as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def delete_job_quarantine(job_id: str):
    """
    Deletes all quarantine records for a given job_id.
    This is typically called when a previously failed job succeeds on retry.
    """
    db = await get_db()
    await db.execute(
        "DELETE FROM job_quarantine WHERE job_id = ?",
        (job_id,)
    )
    await db.commit()
    logger.info(f"Deleted quarantine records for job_id: {job_id}")

async def delete_job_skills_by_job_id(job_id: str):
    """
    Deletes all job_skills records for the specified job_id.
    Use this before regenerating an assessment to avoid duplicate skills.
    """
    db = await get_db()
    await db.execute(
        "DELETE FROM job_skills WHERE job_id = ?",
        (job_id,)
    )
    await db.commit()
    logger.info(f"Deleted job_skills for job_id: {job_id}")

async def cleanup_stale_quarantine() -> int:
    """Delete quarantine rows for jobs that now have skills (assessment exists).
    Returns number of quarantine rows deleted.
    """
    db = await get_db()
    # Find job_ids that have both skills and quarantine rows
    async with db.execute(
        """
        SELECT DISTINCT q.job_id
        FROM job_quarantine q
        INNER JOIN job_skills s ON s.job_id = q.job_id
        """
    ) as cursor:
        rows = await cursor.fetchall()
        stale_ids = [r["job_id"] for r in rows]
    deleted = 0
    if stale_ids:
        # Use executemany for efficiency
        await db.executemany(
            "DELETE FROM job_quarantine WHERE job_id = ?",
            [(jid,) for jid in stale_ids]
        )
        await db.commit()
        deleted = len(stale_ids)
        logger.info(f"cleanup_stale_quarantine: removed quarantine rows for {deleted} job(s): {stale_ids}")
    else:
        logger.info("cleanup_stale_quarantine: no stale quarantine rows found")
    return deleted

