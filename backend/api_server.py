import asyncio
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
    upsert_job_assessment,
    upsert_llm_model,
    upsert_llm_run,
    upsert_job_quarantine,
    get_job_runs,
    get_job_details,
    get_document_store,
    get_run_findings,
    get_job_assessment,
    get_llm_models,
    get_llm_runs,
    get_job_ids_without_description,
    get_job_ids_without_assessment,
)
from .crawler import scrape_linkedin_multi_page
from .utilities import setup_logging, get_logger
from .llm import generate_job_assessment

# Pydantic Models

class LinkedInScrapeRequest(BaseModel):
    keywords: list[str]  # Changed to accept a list of keywords
    max_pages: int = 10

# --- Pydantic Models for Upserts ---
class JobRunUpsertRequest(BaseModel):
    job_run_id: str
    job_run_timestamp: int
    job_run_keywords: str | None = None

class JobDetailUpsertRequest(BaseModel):
    job_id: str
    job_title: str | None = None
    job_company: str | None = None
    job_location: str | None = None
    job_salary: str | None = None
    job_url: str | None = None
    job_url_direct: str | None = None
    job_description: str | None = None
    job_applied: int = 0
    job_applied_timestamp: int | None = None

class DocumentUpsertRequest(BaseModel):
    document_id: str
    document_name: str
    document_timestamp: int
    document_markdown: str | None = None

class RunFindingUpsertRequest(BaseModel):
    job_run_id: str
    job_id: str
    job_run_page_num: int | None = None
    job_run_rank: int | None = None

class JobAssessmentUpsertRequest(BaseModel):
    job_assessment_id: str
    job_id: str
    job_assessment_timestamp: int
    job_assessment_rating: str | None = None
    job_assessment_details: str | None = None
    job_assessment_required_qualifications_matched_count: int | None = None
    job_assessment_required_qualifications_count: int | None = None
    job_assessment_additional_qualifications_matched_count: int | None = None
    job_assessment_additional_qualifications_count: int | None = None
    job_assessment_list_required_qualifications: str | None = None
    job_assessment_list_matched_required_qualifications: str | None = None
    job_assessment_list_additional_qualifications: str | None = None
    job_assessment_list_matched_additional_qualifications: str | None = None
    job_assessment_resume_document_id: str | None = None
    job_assessment_prompt_document_id: str | None = None

class LLMModelUpsertRequest(BaseModel):
    model_id: str
    model_name: str
    model_provider: str | None = None
    model_cpmt_prompt: float | None = None
    model_cpmt_completion: float | None = None
    model_cpmt_thinking: float | None = None

class LLMRunUpsertRequest(BaseModel):
    llm_run_id: str
    llm_run_type: str
    llm_model_id: str | None = None
    job_id: str | None = None
    llm_prompt_document_id: str | None = None
    llm_run_prompt_tokens: int | None = None
    llm_run_completion_tokens: int | None = None
    llm_run_thinking_tokens: int | None = None
    llm_run_total_tokens: int | None = None
    assessment_id_link: str | None = None
    generated_document_id_link: str | None = None

# Initialize Logging and FastAPI
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

@app.get("/get_job_ids_without_description", response_model=list[dict])
async def get_job_ids_without_description_endpoint():
    return await get_job_ids_without_description()

@app.get("/get_job_ids_without_assessment", response_model=list[dict])
async def get_job_ids_without_assessment_endpoint():
    return await get_job_ids_without_assessment()


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
            desc = await scrape_linkedin_job_page(job_url, min_length=min_length)
            if desc and isinstance(desc, str):
                await upsert_job_description(job_id, desc)
                updated += 1
            else:
                logger.warning(f"Failed to scrape description for job_id {job_id}.")
                failed.append(job_id)
        return {"status": "success", "updated": updated, "failed": failed, "total_missing": len(job_ids)}
    except Exception as e:
        logger.error(f"Failed to fill missing job descriptions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")


# --- Endpoint to generate job assessments ---
@app.post("/generate_job_assessments")
async def generate_job_assessments_endpoint(
    jobs_to_run: int = Query(..., gt=0, description="Number of job assessments to generate"),
    concurrency: int = Query(3, gt=0, description="Number of concurrent requests to run.")
):
    """
    Generates job assessments for jobs missing assessments, upserts results to job_assessment and llm_runs tables.
    """
    async def process_job(job: dict, semaphore: asyncio.Semaphore):
        job_id = job.get("job_id")
        job_description = job.get("job_description")
        if not job_id or not job_description:
            logger.warning(f"Skipping job due to missing id or description: {job_id}")
            return {"status": "failed", "job_id": job_id}

        async with semaphore:
            logger.info(f"Processing job_id: {job_id}")
            try:
                result = await generate_job_assessment(job_id, job_description)
                if result and result.get("job_assessment") and result.get("llm_run"):
                    # Upsert job_assessment
                    try:
                        await upsert_job_assessment(**result["job_assessment"])
                    except Exception as e:
                        logger.error(f"Failed to upsert job_assessment for job_id {job_id}: {e}", exc_info=True)
                        quarantine_id = str(uuid.uuid4())
                        await upsert_job_quarantine(
                            job_quarantine_id=quarantine_id,
                            job_id=job_id,
                            job_quarantine_reason="fail_upsert_job_assessment"
                        )
                        return {"status": "failed", "job_id": job_id}
                    # Upsert llm_run
                    try:
                        await upsert_llm_run(**result["llm_run"])
                    except Exception as e:
                        logger.error(f"Failed to upsert llm_run for job_id {job_id}: {e}", exc_info=True)
                        quarantine_id = str(uuid.uuid4())
                        await upsert_job_quarantine(
                            job_quarantine_id=quarantine_id,
                            job_id=job_id,
                            job_quarantine_reason="fail_upsert_llm_run"
                        )
                        return {"status": "failed", "job_id": job_id}
                    logger.info(f"Successfully processed and upserted assessment for job_id: {job_id}")
                    return {"status": "success", "job_id": job_id}
                else:
                    logger.warning(f"Failed to generate assessment for job_id: {job_id}. Result was empty.")
                    return {"status": "failed", "job_id": job_id}
            except Exception as e:
                logger.error(f"An exception occurred while processing job_id {job_id}: {e}", exc_info=True)
                return {"status": "failed", "job_id": job_id}

    try:
        jobs_to_process = await get_job_ids_without_assessment()
        if not jobs_to_process:
            return {"status": "success", "message": "No jobs found without assessment.", "jobs_processed": 0}

        jobs_to_process = jobs_to_process[:jobs_to_run]
        semaphore = asyncio.Semaphore(concurrency)
        tasks = [process_job(job, semaphore) for job in jobs_to_process]
        
        results = await asyncio.gather(*tasks)

        processed = sum(1 for r in results if r['status'] == 'success')
        failed = [r['job_id'] for r in results if r['status'] == 'failed']

        return {
            "status": "success",
            "jobs_processed": processed,
            "failed_jobs": failed,
            "total_requested": jobs_to_run,
            "total_available": len(jobs_to_process)
        }
    except Exception as e:
        logger.error(f"Failed to generate job assessments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

# # --- POST endpoints for each table ---

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