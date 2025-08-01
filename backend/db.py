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

# --- Upsert for document_store ---
async def upsert_document(
    document_id: str,
    document_name: str,
    document_timestamp: int,
    document_markdown: Optional[str] = None
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

# --- Upsert for job_assessment ---
async def upsert_job_assessment(
    job_assessment_id: str,
    job_id: str,
    job_assessment_timestamp: int,
    job_assessment_required_qualifications_matched_count: Optional[int] = None,
    job_assessment_required_qualifications_count: Optional[int] = None,
    job_assessment_additional_qualifications_matched_count: Optional[int] = None,
    job_assessment_additional_qualifications_count: Optional[int] = None,
    job_assessment_list_required_qualifications: Optional[str] = None,
    job_assessment_list_matched_required_qualifications: Optional[str] = None,
    job_assessment_list_additional_qualifications: Optional[str] = None,
    job_assessment_list_matched_additional_qualifications: Optional[str] = None,
    job_assessment_resume_document_id: Optional[str] = None,
    job_assessment_prompt_document_id: Optional[str] = None
):
    """
    Upserts a record into the job_assessment table.
    """
    db = await get_db()
    await db.execute(
        """
        INSERT INTO job_assessment (
            job_assessment_id, job_id, job_assessment_timestamp,
            job_assessment_required_qualifications_matched_count, job_assessment_required_qualifications_count,
            job_assessment_additional_qualifications_matched_count, job_assessment_additional_qualifications_count,
            job_assessment_list_required_qualifications, job_assessment_list_matched_required_qualifications,
            job_assessment_list_additional_qualifications, job_assessment_list_matched_additional_qualifications,
            job_assessment_resume_document_id, job_assessment_prompt_document_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_assessment_id) DO UPDATE SET
            job_id=excluded.job_id,
            job_assessment_timestamp=excluded.job_assessment_timestamp,
            job_assessment_required_qualifications_matched_count=excluded.job_assessment_required_qualifications_matched_count,
            job_assessment_required_qualifications_count=excluded.job_assessment_required_qualifications_count,
            job_assessment_additional_qualifications_matched_count=excluded.job_assessment_additional_qualifications_matched_count,
            job_assessment_additional_qualifications_count=excluded.job_assessment_additional_qualifications_count,
            job_assessment_list_required_qualifications=excluded.job_assessment_list_required_qualifications,
            job_assessment_list_matched_required_qualifications=excluded.job_assessment_list_matched_required_qualifications,
            job_assessment_list_additional_qualifications=excluded.job_assessment_list_additional_qualifications,
            job_assessment_list_matched_additional_qualifications=excluded.job_assessment_list_matched_additional_qualifications,
            job_assessment_resume_document_id=excluded.job_assessment_resume_document_id,
            job_assessment_prompt_document_id=excluded.job_assessment_prompt_document_id;
        """,
        (
            job_assessment_id, job_id, job_assessment_timestamp,
            job_assessment_required_qualifications_matched_count, job_assessment_required_qualifications_count,
            job_assessment_additional_qualifications_matched_count, job_assessment_additional_qualifications_count,
            job_assessment_list_required_qualifications, job_assessment_list_matched_required_qualifications,
            job_assessment_list_additional_qualifications, job_assessment_list_matched_additional_qualifications,
            job_assessment_resume_document_id, job_assessment_prompt_document_id
        )
    )
    await db.commit()
    # logger.info(f"Upserted job_assessment: {job_assessment_id}")

# --- Upsert for llm_models ---
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


# --- Get functions for each table ---
async def get_job_runs() -> list[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM job_runs") as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_job_details() -> list[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM job_details") as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
        
# Insert new function to get a list of job_id in job_details without description

async def get_job_ids_without_description() -> list[str]:
    """
    Returns a list of job_id values from job_details where job_description is NULL or empty, excluding those in job_quarantine.
    """
    db = await get_db()
    async with db.execute("""
        SELECT job_id FROM job_details 
        WHERE (job_description IS NULL OR job_description = '')
        AND job_id NOT IN (SELECT DISTINCT job_id FROM job_quarantine)
    """) as cursor:
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def get_document_store() -> list[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM document_store") as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_run_findings() -> list[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM run_findings") as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_job_assessment() -> list[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM job_assessment") as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_llm_models() -> list[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM llm_models") as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_llm_runs() -> list[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM llm_runs") as cursor:
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

async def get_document_master_resume() -> dict:
    """
    Returns the master resume markdown content.
    """
    db = await get_db()
    async with db.execute("SELECT document_id, document_markdown FROM document_store WHERE document_name = 'master_resume_json' ORDER BY document_timestamp DESC") as cursor:
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
    
async def get_job_ids_without_assessment() -> list[dict]:
    """
    Returns a list of job_id values from job_details where job_assessment_id is NULL or empty.
    """
    quarantine_list = await get_job_quarantine()

    db = await get_db()
    async with db.execute("SELECT jd.job_id, jd.job_description from job_details jd LEFT JOIN job_assessment ja ON jd.job_id = ja.job_id WHERE ja.job_assessment_id IS NULL AND jd.job_description IS NOT NULL AND jd.job_description != ''") as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows if row["job_id"] not in quarantine_list]

# --- Get all job_skills ---
async def get_job_skills() -> list[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM job_skills") as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

# --- Get all prompts ---
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

# --- Get all llm_runs_v2 ---
async def get_llm_runs_v2() -> list[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM llm_runs_v2") as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
# get job_details where job_skills_match is null
async def get_job_details_without_assessment(limit:int=100, days_back:int=14) -> list[dict]:
    """
    Returns a list of job_details where job_skills_match is NULL.
    """
    db = await get_db()
    async with db.execute("""\
        WITH 
        raw_skills AS (select distinct job_id from job_skills),
        raw as (
            SELECT
                jd.job_id,
                jd.job_description,
                DATE(jr.job_run_timestamp, 'unixepoch') as first_run_date,
                row_number() OVER (PARTITION BY jd.job_id ORDER BY jr.job_run_timestamp ASC) as rn
            FROM
                job_details jd
                LEFT JOIN run_findings rf ON jd.job_id = rf.job_id
                LEFT JOIN job_runs jr ON rf.job_run_id = jr.job_run_id
                LEFT JOIN job_quarantine jq ON jd.job_id = jq.job_id
                LEFT JOIN raw_skills rs ON jd.job_id = rs.job_id
            WHERE
                jd.job_description IS NOT NULL
                AND jd.job_description != ''
                AND jq.job_id IS NULL
                AND rs.job_id IS NULL
            ORDER BY
                jd.job_id,
                jr.job_run_timestamp DESC
        )

        SELECT
            job_id,
            job_description,
            first_run_date
        FROM
            raw
        WHERE
            rn = 1
            and julianday('NOW') - julianday(first_run_date) <= ?
        ORDER BY
            first_run_date DESC
        LIMIT
            ?
        """, (days_back, limit)) as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_quarantined_job_details_for_assessment(limit:int=100, days_back:int=14) -> list[dict]:
    """
    Returns a list of job_details for quarantined jobs where job_skills assessment is still needed.
    1. First gets distinct job_ids from job_quarantine table (failed jobs)
    2. Excludes those that already have job_skills entries (might have been rerun successfully)
    3. Returns job details with same structure as get_job_details_without_assessment
    """
    db = await get_db()
    async with db.execute("""\
        WITH 
        quarantined_jobs AS (SELECT DISTINCT job_id FROM job_quarantine),
        raw_skills AS (SELECT DISTINCT job_id FROM job_skills),
        raw as (
            SELECT
                jd.job_id,
                jd.job_description,
                DATE(jr.job_run_timestamp, 'unixepoch') as first_run_date,
                row_number() OVER (PARTITION BY jd.job_id ORDER BY jr.job_run_timestamp ASC) as rn
            FROM
                job_details jd
                LEFT JOIN run_findings rf ON jd.job_id = rf.job_id
                LEFT JOIN job_runs jr ON rf.job_run_id = jr.job_run_id
                INNER JOIN quarantined_jobs qj ON jd.job_id = qj.job_id
                LEFT JOIN raw_skills rs ON jd.job_id = rs.job_id
            WHERE
                jd.job_description IS NOT NULL
                AND jd.job_description != ''
                AND rs.job_id IS NULL
            ORDER BY
                jd.job_id,
                jr.job_run_timestamp DESC
        )

        SELECT
            job_id,
            job_description,
            first_run_date
        FROM
            raw
        WHERE
            rn = 1
            and julianday('NOW') - julianday(first_run_date) <= ?
        ORDER BY
            first_run_date DESC
        LIMIT
            ?
        """, (days_back, limit)) as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

# --- Delete quarantine records for a job_id ---
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

