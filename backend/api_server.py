from contextlib import asynccontextmanager

from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel

from .db import (
    initialize_database,
    upsert_job_run,
    upsert_job_detail,
    upsert_document,
    upsert_run_finding,
    upsert_job_assessment,
    upsert_llm_model,
    upsert_llm_run,
    get_job_runs,
    get_job_details,
    get_document_store,
    get_run_findings,
    get_job_assessment,
    get_llm_models,
    get_llm_runs
)
from .crawler import scrape_linkedin_multi_page
from .utilities import setup_logging, get_logger

# Pydantic Models

class LinkedInScrapeRequest(BaseModel):
    keywords: str
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
    await initialize_database()
    logger.info("Database initialized successfully.")
    yield
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


# --- Endpoint to run LinkedIn scrape and upsert results ---

@app.post("/scrape_linkedin_multi_page")
async def scrape_linkedin_multi_page_endpoint(payload: LinkedInScrapeRequest = Body(...)):
    """
    Runs the LinkedIn multi-page scraper and upserts results into the database.
    """
    try:
        logger.info(f"Starting LinkedIn scrape for keywords: '{payload.keywords}'")
        results = await scrape_linkedin_multi_page(payload.keywords, payload.max_pages)
        job_run_meta = results.get("job_run_meta", [])
        job_listings = results.get("job_listings", [])

        if not job_run_meta or not job_listings:
            logger.info("No jobs found, no data to upsert.")
            return {"status": "success", "job_run_id": None, "jobs_found": 0, "message": "No jobs found."}

        run_id = job_run_meta[0]["job_run_id"]
        logger.info(f"Scrape complete. Found {len(job_listings)} jobs for run_id: {run_id}.")

        # 1. Upsert job_details. These are the individual job listings.
        logger.info(f"Upserting {len(job_listings)} job details.")
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
        logger.info(f"Upserting {len(job_run_meta)} run findings.")
        for meta in job_run_meta:
            await upsert_run_finding(
                job_run_id=meta["job_run_id"],
                job_id=meta["job_id"],
                job_run_page_num=meta.get("job_run_page_num"),
                job_run_rank=meta.get("job_run_rank")
            )

        logger.info("All data has been successfully upserted.")
        return {"status": "success", "job_run_id": run_id, "jobs_found": len(job_listings)}

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

# # --- POST endpoints for each table ---

# @app.post("/job_runs/upsert")
# async def upsert_job_run_endpoint(payload: JobRunUpsertRequest):
#     try:
#         await upsert_job_run(
#             job_run_id=payload.job_run_id,
#             job_run_timestamp=payload.job_run_timestamp,
#             job_run_keywords=payload.job_run_keywords
#         )
#         return {"status": "success", "job_run_id": payload.job_run_id}
#     except Exception as e:
#         logger.error(f"Failed to upsert job_run: {e}")
#         raise HTTPException(status_code=500, detail="Failed to upsert job_run.")

# @app.post("/job_details/upsert")
# async def upsert_job_detail_endpoint(payload: JobDetailUpsertRequest):
#     try:
#         await upsert_job_detail(**payload.model_dump())
#         return {"status": "success", "job_id": payload.job_id}
#     except Exception as e:
#         logger.error(f"Failed to upsert job_detail: {e}")
#         raise HTTPException(status_code=500, detail="Failed to upsert job_detail.")

# @app.post("/document_store/upsert")
# async def upsert_document_endpoint(payload: DocumentUpsertRequest):
#     try:
#         await upsert_document(**payload.model_dump())
#         return {"status": "success", "document_id": payload.document_id}
#     except Exception as e:
#         logger.error(f"Failed to upsert document: {e}")
#         raise HTTPException(status_code=500, detail="Failed to upsert document.")

# @app.post("/run_findings/upsert")
# async def upsert_run_finding_endpoint(payload: RunFindingUpsertRequest):
#     try:
#         await upsert_run_finding(**payload.model_dump())
#         return {"status": "success", "job_run_id": payload.job_run_id, "job_id": payload.job_id}
#     except Exception as e:
#         logger.error(f"Failed to upsert run_finding: {e}")
#         raise HTTPException(status_code=500, detail="Failed to upsert run_finding.")

# @app.post("/job_assessment/upsert")
# async def upsert_job_assessment_endpoint(payload: JobAssessmentUpsertRequest):
#     try:
#         await upsert_job_assessment(**payload.model_dump())
#         return {"status": "success", "job_assessment_id": payload.job_assessment_id}
#     except Exception as e:
#         logger.error(f"Failed to upsert job_assessment: {e}")
#         raise HTTPException(status_code=500, detail="Failed to upsert job_assessment.")

@app.post("/llm_models/upsert")
async def upsert_llm_model_endpoint(payload: LLMModelUpsertRequest):
    try:
        await upsert_llm_model(**payload.model_dump())
        return {"status": "success", "model_id": payload.model_id}
    except Exception as e:
        logger.error(f"Failed to upsert llm_model: {e}")
        raise HTTPException(status_code=500, detail="Failed to upsert llm_model.")

# @app.post("/llm_runs/upsert")
# async def upsert_llm_run_endpoint(payload: LLMRunUpsertRequest):
#     try:
#         await upsert_llm_run(**payload.model_dump())
#         return {"status": "success", "llm_run_id": payload.llm_run_id}
#     except Exception as e:
#         logger.error(f"Failed to upsert llm_run: {e}")
#         raise HTTPException(status_code=500, detail="Failed to upsert llm_run.")

