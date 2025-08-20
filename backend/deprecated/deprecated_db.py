# async def get_job_details_without_assessment(limit:int=100, days_back:int=14) -> list[dict]:
#     """
#     Returns a list of job_details where job_skills_match is NULL.
#     """
#     db = await get_db()
#     async with db.execute("""\
#         WITH 
#         raw_skills AS (select distinct job_id from job_skills),
#         raw as (
#             SELECT
#                 jd.job_id,
#                 jd.job_description,
#                 DATE(jr.job_run_timestamp, 'unixepoch') as first_run_date,
#                 row_number() OVER (PARTITION BY jd.job_id ORDER BY jr.job_run_timestamp ASC) as rn
#             FROM
#                 job_details jd
#                 LEFT JOIN run_findings rf ON jd.job_id = rf.job_id
#                 LEFT JOIN job_runs jr ON rf.job_run_id = jr.job_run_id
#                 LEFT JOIN job_quarantine jq ON jd.job_id = jq.job_id
#                 LEFT JOIN raw_skills rs ON jd.job_id = rs.job_id
#             WHERE
#                 jd.job_description IS NOT NULL
#                 AND jd.job_description != ''
#                 AND jq.job_id IS NULL
#                 AND rs.job_id IS NULL
#             ORDER BY
#                 jd.job_id,
#                 jr.job_run_timestamp DESC
#         )

#         SELECT
#             job_id,
#             job_description,
#             first_run_date
#         FROM
#             raw
#         WHERE
#             rn = 1
#             and julianday('NOW') - julianday(first_run_date) <= ?
#         ORDER BY
#             first_run_date DESC
#         LIMIT
#             ?
#         """, (days_back, limit)) as cursor:
#         rows = await cursor.fetchall()
#         return [dict(row) for row in rows]

# async def get_quarantined_job_details_for_assessment(limit:int=100, days_back:int=14) -> list[dict]:
#     """
#     Returns a list of job_details for quarantined jobs where job_skills assessment is still needed.
#     1. First gets distinct job_ids from job_quarantine table (failed jobs)
#     2. Excludes those that already have job_skills entries (might have been rerun successfully)
#     3. Returns job details with same structure as get_job_details_without_assessment
#     """
#     db = await get_db()
#     async with db.execute("""\
#         WITH 
#         quarantined_jobs AS (SELECT DISTINCT job_id FROM job_quarantine),
#         raw_skills AS (SELECT DISTINCT job_id FROM job_skills),
#         raw as (
#             SELECT
#                 jd.job_id,
#                 jd.job_description,
#                 DATE(jr.job_run_timestamp, 'unixepoch') as first_run_date,
#                 row_number() OVER (PARTITION BY jd.job_id ORDER BY jr.job_run_timestamp ASC) as rn
#             FROM
#                 job_details jd
#                 LEFT JOIN run_findings rf ON jd.job_id = rf.job_id
#                 LEFT JOIN job_runs jr ON rf.job_run_id = jr.job_run_id
#                 INNER JOIN quarantined_jobs qj ON jd.job_id = qj.job_id
#                 LEFT JOIN raw_skills rs ON jd.job_id = rs.job_id
#             WHERE
#                 jd.job_description IS NOT NULL
#                 AND jd.job_description != ''
#                 AND rs.job_id IS NULL
#             ORDER BY
#                 jd.job_id,
#                 jr.job_run_timestamp DESC
#         )

#         SELECT
#             job_id,
#             job_description,
#             first_run_date
#         FROM
#             raw
#         WHERE
#             rn = 1
#             and julianday('NOW') - julianday(first_run_date) <= ?
#         ORDER BY
#             first_run_date DESC
#         LIMIT
#             ?
#         """, (days_back, limit)) as cursor:
#         rows = await cursor.fetchall()
#         return [dict(row) for row in rows]

# async def get_job_ids_without_description() -> list[str]:
#     """
#     Returns a list of job_id values from job_details where job_description is NULL or empty, excluding those in job_quarantine.
#     """
#     db = await get_db()
#     async with db.execute("""
#         SELECT job_id FROM job_details 
#         WHERE (job_description IS NULL OR job_description = '')
#         AND job_id NOT IN (SELECT DISTINCT job_id FROM job_quarantine)
#     """) as cursor:
#         rows = await cursor.fetchall()
#         return [row[0] for row in rows]

# async def get_llm_runs() -> list[dict]:
#     db = await get_db()
#     async with db.execute("SELECT * FROM llm_runs") as cursor:
#         rows = await cursor.fetchall()
#         return [dict(row) for row in rows]

# async def get_job_runs() -> list[dict]:
#     db = await get_db()
#     async with db.execute("SELECT * FROM job_runs") as cursor:
#         rows = await cursor.fetchall()
#         return [dict(row) for row in rows]

# async def get_run_findings() -> list[dict]:
#     db = await get_db()
#     async with db.execute("SELECT * FROM run_findings") as cursor:
#         rows = await cursor.fetchall()
#         return [dict(row) for row in rows]


# async def get_job_assessment() -> list[dict]:
#     db = await get_db()
#     async with db.execute("SELECT * FROM job_assessment") as cursor:
#         rows = await cursor.fetchall()
#         return [dict(row) for row in rows]

# # --- Upsert for job_assessment ---
# async def upsert_job_assessment(
#     job_assessment_id: str,
#     job_id: str,
#     job_assessment_timestamp: int,
#     job_assessment_required_qualifications_matched_count: Optional[int] = None,
#     job_assessment_required_qualifications_count: Optional[int] = None,
#     job_assessment_additional_qualifications_matched_count: Optional[int] = None,
#     job_assessment_additional_qualifications_count: Optional[int] = None,
#     job_assessment_list_required_qualifications: Optional[str] = None,
#     job_assessment_list_matched_required_qualifications: Optional[str] = None,
#     job_assessment_list_additional_qualifications: Optional[str] = None,
#     job_assessment_list_matched_additional_qualifications: Optional[str] = None,
#     job_assessment_resume_document_id: Optional[str] = None,
#     job_assessment_prompt_document_id: Optional[str] = None
# ):
#     """
#     Upserts a record into the job_assessment table.
#     """
#     db = await get_db()
#     await db.execute(
#         """
#         INSERT INTO job_assessment (
#             job_assessment_id, job_id, job_assessment_timestamp,
#             job_assessment_required_qualifications_matched_count, job_assessment_required_qualifications_count,
#             job_assessment_additional_qualifications_matched_count, job_assessment_additional_qualifications_count,
#             job_assessment_list_required_qualifications, job_assessment_list_matched_required_qualifications,
#             job_assessment_list_additional_qualifications, job_assessment_list_matched_additional_qualifications,
#             job_assessment_resume_document_id, job_assessment_prompt_document_id
#         ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         ON CONFLICT(job_assessment_id) DO UPDATE SET
#             job_id=excluded.job_id,
#             job_assessment_timestamp=excluded.job_assessment_timestamp,
#             job_assessment_required_qualifications_matched_count=excluded.job_assessment_required_qualifications_matched_count,
#             job_assessment_required_qualifications_count=excluded.job_assessment_required_qualifications_count,
#             job_assessment_additional_qualifications_matched_count=excluded.job_assessment_additional_qualifications_matched_count,
#             job_assessment_additional_qualifications_count=excluded.job_assessment_additional_qualifications_count,
#             job_assessment_list_required_qualifications=excluded.job_assessment_list_required_qualifications,
#             job_assessment_list_matched_required_qualifications=excluded.job_assessment_list_matched_required_qualifications,
#             job_assessment_list_additional_qualifications=excluded.job_assessment_list_additional_qualifications,
#             job_assessment_list_matched_additional_qualifications=excluded.job_assessment_list_matched_additional_qualifications,
#             job_assessment_resume_document_id=excluded.job_assessment_resume_document_id,
#             job_assessment_prompt_document_id=excluded.job_assessment_prompt_document_id;
#         """,
#         (
#             job_assessment_id, job_id, job_assessment_timestamp,
#             job_assessment_required_qualifications_matched_count, job_assessment_required_qualifications_count,
#             job_assessment_additional_qualifications_matched_count, job_assessment_additional_qualifications_count,
#             job_assessment_list_required_qualifications, job_assessment_list_matched_required_qualifications,
#             job_assessment_list_additional_qualifications, job_assessment_list_matched_additional_qualifications,
#             job_assessment_resume_document_id, job_assessment_prompt_document_id
#         )
#     )
#     await db.commit()
#     # logger.info(f"Upserted job_assessment: {job_assessment_id}")