



# @app.post("/scrape_linkedin_multi_page")
# async def scrape_linkedin_multi_page_endpoint(payload: LinkedInScrapeRequest = Body(...)):
#     """
#     Runs the LinkedIn multi-page scraper for each keyword in the list and upserts results into the database.
#     """
#     try:
#         all_results = []
#         for keyword in payload.keywords:
#             logger.info(f"Starting LinkedIn scrape for keyword: '{keyword}'")
#             results = await scrape_linkedin_multi_page(keyword, payload.max_pages)
#             job_run_meta = results.get("job_run_meta", [])
#             job_listings = results.get("job_listings", [])

#             if not job_run_meta or not job_listings:
#                 logger.info(f"No jobs found for keyword '{keyword}', no data to upsert.")
#                 all_results.append({
#                     "keyword": keyword,
#                     "status": "success",
#                     "job_run_id": None,
#                     "jobs_found": 0,
#                     "message": "No jobs found."
#                 })
#                 continue

#             run_id = job_run_meta[0]["job_run_id"]
#             logger.info(f"Scrape complete. Found {len(job_listings)} jobs for run_id: {run_id}.")

#             # 1. Upsert job_details. These are the individual job listings.
#             logger.info(f"Upserting {len(job_listings)} job details for keyword '{keyword}'.")
#             for job in job_listings:
#                 await upsert_job_detail(
#                     job_id=job.get("job_id"),
#                     job_title=job.get("title"),
#                     job_company=job.get("company"),
#                     job_location=job.get("location"),
#                     job_salary=job.get("salary"),
#                     job_url=job.get("url"),
#                     job_url_direct=job.get("job_url_direct"),
#                     job_description=None,  # Description is fetched later
#                     job_applied=0,
#                     job_applied_timestamp=None
#                 )

#             # 2. Upsert job_run. This is the parent record for this entire run.
#             logger.info(f"Upserting job run for run_id: {run_id}")
#             first_meta = job_run_meta[0]
#             await upsert_job_run(
#                 job_run_id=first_meta["job_run_id"],
#                 job_run_timestamp=first_meta["job_run_timestamp"],
#                 job_run_keywords=first_meta.get("job_run_keywords")
#             )

#             # 3. Upsert run_findings, which links job_runs and job_details.
#             logger.info(f"Upserting {len(job_run_meta)} run findings for keyword '{keyword}'.")
#             for meta in job_run_meta:
#                 await upsert_run_finding(
#                     job_run_id=meta["job_run_id"],
#                     job_id=meta["job_id"],
#                     job_run_page_num=meta.get("job_run_page_num"),
#                     job_run_rank=meta.get("job_run_rank")
#                 )

#             logger.info(f"All data for keyword '{keyword}' has been successfully upserted.")
#             all_results.append({
#                 "keyword": keyword,
#                 "status": "success",
#                 "job_run_id": run_id,
#                 "jobs_found": len(job_listings)
#             })

#         return {"results": all_results}

#     except Exception as e:
#         logger.error(f"Failed to scrape and upsert: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")
    

# # --- Endpoint to fill missing job descriptions ---
# from .db import get_job_ids_without_description, upsert_job_description
# from .crawler import scrape_linkedin_job_page

# @app.post("/fill_missing_job_descriptions")
# async def fill_missing_job_descriptions(min_length: int = 200):
#     """
#     Finds job_ids in job_details without a description, scrapes the job page, and upserts the description.
#     """
#     try:
#         job_ids = await get_job_ids_without_description()
#         logger.info(f"Found {len(job_ids)} job_ids without description.")
#         updated = 0
#         failed = []
#         for job_id in job_ids:
#             # Try to get the direct URL from job_details
#             job_details = await get_job_details()
#             job = next((j for j in job_details if j.get("job_id") == job_id), None)
#             job_url = job.get("job_url_direct") if job else None
#             if not job_url:
#                 logger.warning(f"No direct URL for job_id {job_id}, skipping.")
#                 failed.append(job_id)
#                 continue
#             try:
#                 desc = await scrape_linkedin_job_page(job_url, min_length=min_length)
#                 if desc and isinstance(desc, str):
#                     await upsert_job_description(job_id, desc)
#                     updated += 1
#                 else:
#                     logger.warning(f"Failed to scrape description for job_id {job_id}.")
#                     failed.append(job_id)
#             except Exception as e:
#                 logger.error(f"Error scraping job_id {job_id}: {e}")
#                 failed.append(job_id)
#                 continue
#         return {"status": "success", "updated": updated, "failed": failed, "total_missing": len(job_ids)}
#     except Exception as e:
#         logger.error(f"Failed to fill missing job descriptions: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")
#     finally:
#         if len(failed) > 0:
#             logger.info(f"Quarantining failed job_ids: {failed}")
#             for job_id in failed:
#                 await upsert_job_quarantine(
#                     job_quarantine_id=str(uuid.uuid4()),
#                     job_id=job_id,
#                     job_quarantine_reason="fail_scrape_linkedin_job_page"
#                 )

# # --- Endpoint to generate job assessments ---
# @app.post("/generate_job_assessments")
# async def generate_job_assessments_endpoint(
#     limit: int = Query(200, gt=0, description="Number of jobs to process."),
#     days_back: int = Query(7, gt=0, description="Number of days back to look for jobs without assessments."),
#     semaphore_count: int = Query(8, gt=0, description="Number of concurrent tasks for processing jobs.")
# ):
#     """
#     Generates job assessments for jobs missing assessments.
#     This is a long-running process that will trigger the assessment generation and return immediately.
#     """
#     try:
#         logger.info(f"Initiating job assessment generation for up to {limit} jobs from the last {days_back} days with {semaphore_count} concurrent tasks.")
#         # This endpoint will now run the generation in the background.
#         # For a more robust solution, consider using a background task runner like Celery or ARQ.
#         result = await generate_job_assessment(limit=limit, days_back=days_back, semaphore_count=semaphore_count)

#         return {
#             "status": "success",
#             "message": "Job assessment generation process completed.",
#             "details": {
#                 "limit": limit,
#                 "days_back": days_back,
#                 "semaphore_count": semaphore_count
#             },
#             "results": result
#         }
#     except Exception as e:
#         logger.error(f"Failed to initiate job assessment generation: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

## Add new endpoint to generate failed job assessments
# @app.post("/generate_failed_job_assessments")
# async def generate_failed_job_assessments_endpoint(
#     limit: int = Query(200, gt=0, description="Number of quarantined jobs to process."),
#     days_back: int = Query(7, gt=0, description="Number of days back to look for quarantined jobs without assessments."),
#     semaphore_count: int = Query(8, gt=0, description="Number of concurrent tasks for processing jobs.")
# ):
#     """
#     Generates job assessments for quarantined jobs that failed previously.
#     This endpoint processes jobs that are in the job_quarantine table but still need assessments.
#     This is a long-running process that will trigger the assessment generation and return immediately.
#     """
#     try:
#         logger.info(f"Initiating failed job assessment generation for up to {limit} quarantined jobs from the last {days_back} days with {semaphore_count} concurrent tasks.")
#         # This endpoint will now run the generation in the background.
#         # For a more robust solution, consider using a background task runner like Celery or ARQ.
#         result = await generate_failed_job_assessment(limit=limit, days_back=days_back, semaphore_count=semaphore_count)

#         return {
#             "status": "success",
#             "message": "Failed job assessment generation process completed.",
#             "details": {
#                 "limit": limit,
#                 "days_back": days_back,
#                 "semaphore_count": semaphore_count
#             },
#             "results": result
#         }
#     except Exception as e:
#         logger.error(f"Failed to initiate failed job assessment generation: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

# --- Endpoint for job_details without assessment ---
# @app.post("/job_details_without_assessment", response_model=list[dict])
# async def get_job_details_without_assessment_endpoint(payload: JobDetailsWithoutAssessmentRequest = Body(...)):
#     """
#     Returns job_details where job_skills_match is NULL, filtered by limit and days_back.
#     """
#     return await get_job_details_without_assessment(limit=payload.limit, days_back=payload.days_back)

# @app.get("/job_skills", response_model=list[dict])
# async def get_job_skills_endpoint():
#     return await get_job_skills()

# @app.get("/llm_runs_v2", response_model=list[dict])
# async def get_llm_runs_v2_endpoint():
#     return await get_llm_runs_v2()