from contextlib import asynccontextmanager
import uuid

from fastapi import FastAPI, Body, HTTPException, Query
from pydantic import BaseModel

from .db import (
    Database,
    upsert_job_run,
    upsert_job_detail,
    upsert_document,
    upsert_run_finding,
    upsert_llm_model,
    upsert_job_quarantine,
    upsert_prompt,
    get_job_runs,
    get_job_details,
    get_document_store,
    get_run_findings,
    get_job_assessment,
    get_llm_models,
    get_llm_runs,
    get_job_ids_without_description,
    get_job_details_without_assessment,
    get_job_skills,
    get_prompts,
    get_llm_runs_v2
)

from .crawler import scrape_linkedin_multi_page
from .utilities import setup_logging, get_logger
from .llm import generate_job_assessment, generate_failed_job_assessment
# from .db_sync import main as sync_main

# Pydantic Models

class LinkedInScrapeRequest(BaseModel):
    keywords: list[str]  # Changed to accept a list of keywords
    max_pages: int = 10

class JobDetailsWithoutAssessmentRequest(BaseModel):
    limit: int = 100
    days_back: int = 14

# --- Pydantic Models for Upserts ---

class DocumentUpsertRequest(BaseModel):
    document_id: str
    document_name: str
    document_timestamp: int
    document_markdown: str | None = None

class LLMModelUpsertRequest(BaseModel):
    model_id: str
    model_name: str
    model_provider: str | None = None
    model_cpmt_prompt: float | None = None
    model_cpmt_completion: float | None = None
    model_cpmt_thinking: float | None = None

class PromptUpsertRequest(BaseModel):
    prompt_id: str
    llm_run_type: str | None = None
    model_id: str | None = None
    prompt_system_prompt: str | None = None
    prompt_template: str | None = None
    prompt_temperature: float | None = None
    prompt_response_schema: str | None = None
    prompt_created_at: int | None = None
    prompt_thinking_budget: int | None = None

# Initialization

setup_logging()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager to initialize the database.
    """
    logger.info("Starting application lifespan...")
    db_instance = await Database.get_instance()

    yield
    logger.info("Closing database connection...")
    await db_instance.close()
    logger.info("Application shutdown complete.")

app = FastAPI(
    title="Job Search API",
    description="API for managing job search data and operations.",
    version="1.0.0",
    lifespan=lifespan
)


# Endpoints

@app.get("/")
async def read_root():
    """A simple root endpoint to confirm the server is running."""
    return {"message": "Welcome to the Job Tracker API!"}


# --- GET endpoints for each table ---
@app.get("/job_runs", response_model=list[dict])
async def get_job_runs_endpoint():
    return await get_job_runs()

@app.get("/job_details", response_model=list[dict])
async def get_job_details_endpoint():
    return await get_job_details()

@app.get("/document_store", response_model=list[dict])
async def get_document_store_endpoint():
    return await get_document_store()

@app.get("/run_findings", response_model=list[dict])
async def get_run_findings_endpoint():
    return await get_run_findings()

@app.get("/job_assessment", response_model=list[dict])
async def get_job_assessment_endpoint():
    return await get_job_assessment()

@app.get("/llm_models", response_model=list[dict])
async def get_llm_models_endpoint():
    return await get_llm_models()

@app.get("/llm_runs", response_model=list[dict])
async def get_llm_runs_endpoint():
    return await get_llm_runs()

@app.get("/get_job_ids_without_description", response_model=list[str])
async def get_job_ids_without_description_endpoint():
    return await get_job_ids_without_description()



# --- Endpoint for job_details without assessment ---
@app.post("/job_details_without_assessment", response_model=list[dict])
async def get_job_details_without_assessment_endpoint(payload: JobDetailsWithoutAssessmentRequest = Body(...)):
    """
    Returns job_details where job_skills_match is NULL, filtered by limit and days_back.
    """
    return await get_job_details_without_assessment(limit=payload.limit, days_back=payload.days_back)

@app.get("/job_skills", response_model=list[dict])
async def get_job_skills_endpoint():
    return await get_job_skills()

@app.get("/prompts", response_model=list[dict])
async def get_prompts_endpoint():
    return await get_prompts()

@app.get("/llm_runs_v2", response_model=list[dict])
async def get_llm_runs_v2_endpoint():
    return await get_llm_runs_v2()

# --- Endpoint to run LinkedIn scrape and upsert results ---

@app.post("/scrape_linkedin_multi_page")
async def scrape_linkedin_multi_page_endpoint(payload: LinkedInScrapeRequest = Body(...)):
    """
    Runs the LinkedIn multi-page scraper for each keyword in the list and upserts results into the database.
    """
    try:
        all_results = []
        for keyword in payload.keywords:
            logger.info(f"Starting LinkedIn scrape for keyword: '{keyword}'")
            results = await scrape_linkedin_multi_page(keyword, payload.max_pages)
            job_run_meta = results.get("job_run_meta", [])
            job_listings = results.get("job_listings", [])

            if not job_run_meta or not job_listings:
                logger.info(f"No jobs found for keyword '{keyword}', no data to upsert.")
                all_results.append({
                    "keyword": keyword,
                    "status": "success",
                    "job_run_id": None,
                    "jobs_found": 0,
                    "message": "No jobs found."
                })
                continue

            run_id = job_run_meta[0]["job_run_id"]
            logger.info(f"Scrape complete. Found {len(job_listings)} jobs for run_id: {run_id}.")

            # 1. Upsert job_details. These are the individual job listings.
            logger.info(f"Upserting {len(job_listings)} job details for keyword '{keyword}'.")
            for job in job_listings:
                await upsert_job_detail(
                    job_id=job.get("job_id"),
                    job_title=job.get("title"),
                    job_company=job.get("company"),
                    job_location=job.get("location"),
                    job_salary=job.get("salary"),
                    job_url=job.get("url"),
                    job_url_direct=job.get("job_url_direct"),
                    job_description=None,  # Description is fetched later
                    job_applied=0,
                    job_applied_timestamp=None
                )

            # 2. Upsert job_run. This is the parent record for this entire run.
            logger.info(f"Upserting job run for run_id: {run_id}")
            first_meta = job_run_meta[0]
            await upsert_job_run(
                job_run_id=first_meta["job_run_id"],
                job_run_timestamp=first_meta["job_run_timestamp"],
                job_run_keywords=first_meta.get("job_run_keywords")
            )

            # 3. Upsert run_findings, which links job_runs and job_details.
            logger.info(f"Upserting {len(job_run_meta)} run findings for keyword '{keyword}'.")
            for meta in job_run_meta:
                await upsert_run_finding(
                    job_run_id=meta["job_run_id"],
                    job_id=meta["job_id"],
                    job_run_page_num=meta.get("job_run_page_num"),
                    job_run_rank=meta.get("job_run_rank")
                )

            logger.info(f"All data for keyword '{keyword}' has been successfully upserted.")
            all_results.append({
                "keyword": keyword,
                "status": "success",
                "job_run_id": run_id,
                "jobs_found": len(job_listings)
            })

        return {"results": all_results}

    except Exception as e:
        logger.error(f"Failed to scrape and upsert: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")
    

# --- Endpoint to fill missing job descriptions ---
from .db import get_job_ids_without_description, upsert_job_description
from .crawler import scrape_linkedin_job_page

@app.post("/fill_missing_job_descriptions")
async def fill_missing_job_descriptions(min_length: int = 200):
    """
    Finds job_ids in job_details without a description, scrapes the job page, and upserts the description.
    """
    try:
        job_ids = await get_job_ids_without_description()
        logger.info(f"Found {len(job_ids)} job_ids without description.")
        updated = 0
        failed = []
        for job_id in job_ids:
            # Try to get the direct URL from job_details
            job_details = await get_job_details()
            job = next((j for j in job_details if j.get("job_id") == job_id), None)
            job_url = job.get("job_url_direct") if job else None
            if not job_url:
                logger.warning(f"No direct URL for job_id {job_id}, skipping.")
                failed.append(job_id)
                continue
            try:
                desc = await scrape_linkedin_job_page(job_url, min_length=min_length)
                if desc and isinstance(desc, str):
                    await upsert_job_description(job_id, desc)
                    updated += 1
                else:
                    logger.warning(f"Failed to scrape description for job_id {job_id}.")
                    failed.append(job_id)
            except Exception as e:
                logger.error(f"Error scraping job_id {job_id}: {e}")
                failed.append(job_id)
                continue
        return {"status": "success", "updated": updated, "failed": failed, "total_missing": len(job_ids)}
    except Exception as e:
        logger.error(f"Failed to fill missing job descriptions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")
    finally:
        if len(failed) > 0:
            logger.info(f"Quarantining failed job_ids: {failed}")
            for job_id in failed:
                await upsert_job_quarantine(
                    job_quarantine_id=str(uuid.uuid4()),
                    job_id=job_id,
                    job_quarantine_reason="fail_scrape_linkedin_job_page"
                )

# --- Endpoint to generate job assessments ---
@app.post("/generate_job_assessments")
async def generate_job_assessments_endpoint(
    limit: int = Query(100, gt=0, description="Number of jobs to process."),
    days_back: int = Query(14, gt=0, description="Number of days back to look for jobs without assessments."),
    semaphore_count: int = Query(5, gt=0, description="Number of concurrent tasks for processing jobs.")
):
    """
    Generates job assessments for jobs missing assessments.
    This is a long-running process that will trigger the assessment generation and return immediately.
    """
    try:
        logger.info(f"Initiating job assessment generation for up to {limit} jobs from the last {days_back} days with {semaphore_count} concurrent tasks.")
        # This endpoint will now run the generation in the background.
        # For a more robust solution, consider using a background task runner like Celery or ARQ.
        result = await generate_job_assessment(limit=limit, days_back=days_back, semaphore_count=semaphore_count)

        return {
            "status": "success",
            "message": "Job assessment generation process completed.",
            "details": {
                "limit": limit,
                "days_back": days_back,
                "semaphore_count": semaphore_count
            },
            "results": result
        }
    except Exception as e:
        logger.error(f"Failed to initiate job assessment generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

# Add new endpoint to generate failed job assessments
@app.post("/generate_failed_job_assessments")
async def generate_failed_job_assessments_endpoint(
    limit: int = Query(100, gt=0, description="Number of quarantined jobs to process."),
    days_back: int = Query(14, gt=0, description="Number of days back to look for quarantined jobs without assessments."),
    semaphore_count: int = Query(5, gt=0, description="Number of concurrent tasks for processing jobs.")
):
    """
    Generates job assessments for quarantined jobs that failed previously.
    This endpoint processes jobs that are in the job_quarantine table but still need assessments.
    This is a long-running process that will trigger the assessment generation and return immediately.
    """
    try:
        logger.info(f"Initiating failed job assessment generation for up to {limit} quarantined jobs from the last {days_back} days with {semaphore_count} concurrent tasks.")
        # This endpoint will now run the generation in the background.
        # For a more robust solution, consider using a background task runner like Celery or ARQ.
        result = await generate_failed_job_assessment(limit=limit, days_back=days_back, semaphore_count=semaphore_count)

        return {
            "status": "success",
            "message": "Failed job assessment generation process completed.",
            "details": {
                "limit": limit,
                "days_back": days_back,
                "semaphore_count": semaphore_count
            },
            "results": result
        }
    except Exception as e:
        logger.error(f"Failed to initiate failed job assessment generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

@app.post("/document_store/upsert")
async def upsert_document_endpoint(payload: DocumentUpsertRequest):
    try:
        await upsert_document(**payload.model_dump())
        return {"status": "success", "document_id": payload.document_id}
    except Exception as e:
        logger.error(f"Failed to upsert document: {e}")
        raise HTTPException(status_code=500, detail="Failed to upsert document.")

@app.post("/llm_models/upsert")
async def upsert_llm_model_endpoint(payload: LLMModelUpsertRequest):
    try:
        await upsert_llm_model(**payload.model_dump())
        return {"status": "success", "model_id": payload.model_id}
    except Exception as e:
        logger.error(f"Failed to upsert llm_model: {e}")
        raise HTTPException(status_code=500, detail="Failed to upsert llm_model.")

@app.post("/prompts/upsert")
async def upsert_prompt_endpoint(payload: PromptUpsertRequest):
    try:
        await upsert_prompt(**payload.model_dump())
        return {"status": "success", "prompt_id": payload.prompt_id}
    except Exception as e:
        logger.error(f"Failed to upsert prompt: {e}")
        raise HTTPException(status_code=500, detail="Failed to upsert prompt.")
    

# --- Endpoint to trigger BigQuery sync ---
# @app.post("/sync_to_bigquery")
# async def sync_to_bigquery_endpoint():
#     """
#     Triggers the complete BigQuery sync process for all tables.
#     This will sync data from the local SQLite database to BigQuery using the Storage Write API.
#     """
#     try:
#         logger.info("Starting BigQuery sync process via API endpoint.")

#         sync_main()
        
#         logger.info("BigQuery sync process completed successfully.")
#         return {
#             "status": "success",
#             "message": "BigQuery sync completed successfully.",
#         }
#     except Exception as e:
#         logger.error(f"Failed to complete BigQuery sync: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"BigQuery sync failed: {e}")
