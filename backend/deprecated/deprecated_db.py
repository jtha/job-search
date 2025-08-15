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