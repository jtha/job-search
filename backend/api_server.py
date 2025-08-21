from contextlib import asynccontextmanager
import os
from typing import Optional

from fastapi import FastAPI, Body, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx

from .db import (
    Database,
    upsert_job_detail,
    upsert_document,
    upsert_llm_model,
    upsert_prompt,
    update_job_applied,
    clear_job_applied,
    delete_job_skills_by_job_id,
    get_job_detail_by_id,
    get_job_details,
    get_document_store,
    get_llm_models,
    get_recent_job_skills,
    get_job_skills_for_job,
    get_prompts,
    get_recent_assessed_jobs,
    get_document_master_resume,
    is_job_quarantined,
    get_last_assessed_at,
    get_latest_quarantine,
    delete_job_quarantine,
    cleanup_stale_quarantine,
)
from .crawler import manual_extract
from .utilities import setup_logging, get_logger
from .llm import generate_job_assessment_with_id
from .prompt_seed import seed_initial_prompts

class RegenerateJobAssessmentRequest(BaseModel):
    job_id: str

class DocumentUpsertRequest(BaseModel):
    document_id: str
    document_name: str
    document_timestamp: int
    document_markdown: str | None = None
    document_job_id_reference: Optional[str] = None
    document_job_type: Optional[str] | None = None

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

class HtmlPayload(BaseModel):
    html: str
    url: str

class UpdateJobAppliedRequest(BaseModel):
    job_id: str

setup_logging()
logger = get_logger(__name__)
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager to initialize the database."""
    logger.info("Starting application lifespan...")
    db_instance = await Database.get_instance()
    # Phase 0: initial prompt seed (insert-only, one-time; safe idempotent)
    if os.getenv("INITIAL_PROMPT_SEED", "1") == "1":
        try:
            result = await seed_initial_prompts()
            logger.info(
                "Prompt seed summary: inserted=%d existing=%d required=%d",
                len(result.inserted_run_types),
                len(result.existing_run_types),
                result.total_required,
            )
        except Exception as e:
            logger.error(f"Initial prompt seeding failed (continuing startup): {e}")
    # Phase 1: cleanup stale quarantine rows (jobs that now have assessments)
    try:
        removed = await cleanup_stale_quarantine()
        if removed:
            logger.info(f"Startup quarantine cleanup removed {removed} stale quarantine job(s)")
    except Exception as e:
        logger.error(f"Failed startup quarantine cleanup: {e}")
    yield
    logger.info("Closing database connection...")
    await db_instance.close()
    logger.info("Application shutdown complete.")

app = FastAPI(
    title="Job Search API",
    description="API for managing job search data and operations.",
    version="1.0.0",
    lifespan=lifespan,
)

@app.get("/")
async def read_root():
    """A simple root endpoint to confirm the server is running."""
    return {"message": "Welcome to the Job Tracker API!"}

@app.get("/job_details", response_model=list[dict])
async def get_job_details_endpoint():
    return await get_job_details()

@app.get("/document_store", response_model=list[dict])
async def get_document_store_endpoint():
    return await get_document_store()

@app.get("/llm_models", response_model=list[dict])
async def get_llm_models_endpoint():
    return await get_llm_models()

@app.get("/prompts", response_model=list[dict])
async def get_prompts_endpoint():
    return await get_prompts()

@app.get("/job_skills_recent", response_model=list[dict])
async def get_job_skills_recent_endpoint(
    days_back: int = Query(5, gt=0, description="Days back to consider an assessment recent."),
    limit: int = Query(300, gt=0, description="Maximum number of jobs to consider when collecting skills.")
):
    return await get_recent_job_skills(days_back=days_back, limit=limit)

@app.get("/jobs_recent", response_model=list[dict])
async def get_jobs_recent_endpoint(
    days_back: int = Query(5, gt=0, description="Days back to consider an assessment recent."),
    limit: int = Query(300, gt=0, description="Maximum number of jobs to return.")
):
    return await get_recent_assessed_jobs(days_back=days_back, limit=limit)

@app.get("/openrouter_credits", response_model=dict)
async def get_openrouter_credits_endpoint():
    url = "https://openrouter.ai/api/v1/credits"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        remaining_credits = response.json()['data']['total_credits'] - response.json()['data']['total_usage']
    return {"remaining_credits": remaining_credits}

@app.get("/master_resume", response_model=dict)
async def get_master_resume_endpoint():
    return await get_document_master_resume()

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

@app.post("/html_extract")
async def html_extract_endpoint(payload: HtmlPayload, background_tasks: BackgroundTasks):
    """
    Extracts text from HTML content and returns it if it meets the minimum length requirement.
    """
    logger.info("Received HTML content for extraction.")

    html_content = payload.html
    request_url = payload.url
    try:
        extracted_data = await manual_extract(html_content, request_url)
        logger.info(f"Successfully extracted content for job id: {extracted_data['job_id']}")
        if extracted_data.get("job_id") is not None:
            await upsert_job_detail(
                job_id=extracted_data.get("job_id"),  # type: ignore
                job_title=extracted_data.get("job_title"),
                job_company=extracted_data.get("job_company"),
                job_location=extracted_data.get("job_location"),
                job_salary=extracted_data.get("job_salary"),
                job_url=extracted_data.get("job_url"),
                job_url_direct=extracted_data.get("job_url_direct"),
                job_description=extracted_data.get("job_description"),
                job_applied=0,
                job_applied_timestamp=None
            )
            # Start assessment in the background and return quickly
            background_tasks.add_task(generate_job_assessment_with_id, extracted_data.get("job_id"))  # type: ignore

            # Fetch the actual job record to get the real job_applied status
            job_record = await get_job_detail_by_id(extracted_data.get("job_id"))  # type: ignore
            actual_job_applied = job_record.get("job_applied", 0) if job_record else 0

            # Return basic data with placeholders; frontend can poll for completion
            extracted_data["required_qualifications"] = []
            extracted_data["additional_qualifications"] = []
            extracted_data["evaluated_qualifications"] = []
            extracted_data["job_applied"] = actual_job_applied
            extracted_data["assessed"] = False

        return {"status": "success", "accepted": True, "data": extracted_data}
    except Exception as e:
        logger.exception(f"Debug HTML content: \n\n{html_content}\n\n")
        logger.exception("Failed to extract HTML content.")
        return {"status": "error", "message": "Failed to extract HTML content."}

@app.get("/job/{job_id}", response_model=dict)
async def get_job_endpoint(job_id: str):
    """
    Returns a unified job payload including qualifications and an assessed flag.
    assessed = True if any job_skills exist for the job_id.
    """
    job = await get_job_detail_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"job_id not found: {job_id}")

    skills = await get_job_skills_for_job(job_id)
    assessed = len(skills) > 0
    failed = await is_job_quarantined(job_id)
    last_assessed_at = await get_last_assessed_at(job_id)
    quarantine = await get_latest_quarantine(job_id) if failed else None

    # Phase 1 quarantine cleanup (stale masking):
    # A quarantine record is considered stale if the job now has a completed assessment (skills exist)
    # but still has a quarantine entry. We mask the failed flag while surfacing that it was previously quarantined.
    stale_quarantine = False
    if failed and assessed and quarantine:
        stale_quarantine = True
        failed = False  # mask as recovered

    def map_required(skills_list):
        return [
            {
                "requirement": s.get("job_skills_atomic_string"),
                "match": s.get("job_skills_match"),
                "match_reason": s.get("job_skills_match_reasoning"),
            }
            for s in skills_list
            if s.get("job_skills_type") == "required_qualification"
        ]

    def map_additional(skills_list):
        return [
            {
                "requirement": s.get("job_skills_atomic_string"),
                "match": s.get("job_skills_match"),
                "match_reason": s.get("job_skills_match_reasoning"),
            }
            for s in skills_list
            if s.get("job_skills_type") == "additional_qualification"
        ]

    def map_evaluated(skills_list):
        return [
            {"requirement": s.get("job_skills_atomic_string")}
            for s in skills_list
            if s.get("job_skills_type") == "evaluated_qualification"
        ]

    data = {
        "job_id": job.get("job_id"),
        "job_title": job.get("job_title"),
        "job_company": job.get("job_company"),
        "job_location": job.get("job_location"),
        "job_salary": job.get("job_salary"),
        "job_url": job.get("job_url"),
        "job_url_direct": job.get("job_url_direct"),
        "job_description": job.get("job_description"),
        "job_applied": job.get("job_applied", 0),
        "required_qualifications": map_required(skills),
        "additional_qualifications": map_additional(skills),
        "evaluated_qualifications": map_evaluated(skills),
        "assessed": assessed,
        "failed": failed,
        "last_assessed_at": last_assessed_at,
        "failed_reason": quarantine.get("job_quarantine_reason") if quarantine else None,
        "failed_timestamp": quarantine.get("job_quarantine_timestamp") if quarantine else None,
    # Expose raw quarantine_reason explicitly for UI clarity (duplicate of failed_reason for now)
    "quarantine_reason": quarantine.get("job_quarantine_reason") if quarantine else None,
    "quarantine_timestamp": quarantine.get("job_quarantine_timestamp") if quarantine else None,
        "stale_quarantine": stale_quarantine,
    }

    return {"status": "success", "data": data}
    
@app.post("/regenerate_job_assessment")
async def regenerate_job_assessment_endpoint(background_tasks: BackgroundTasks, payload: RegenerateJobAssessmentRequest = Body(...)):
    """
    Deletes existing job_skills for the given job_id and regenerates the assessment in the background.
    Returns immediately with accepted=True. Clients can poll GET /job/{job_id} until assessed=True.
    """
    try:
        job_id = payload.job_id
        logger.info(f"Regenerating job assessment for job_id: {job_id}")
        job = await get_job_detail_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"job_id not found: {job_id}")
        # Clear existing skills first so assessed becomes false immediately
        await delete_job_skills_by_job_id(job_id)
        # Clear quarantine + skills then schedule regeneration
        await delete_job_quarantine(job_id)
        if background_tasks is not None:
            background_tasks.add_task(generate_job_assessment_with_id, job_id)
        else:
            # Fallback: fire-and-forget
            import asyncio
            asyncio.create_task(generate_job_assessment_with_id(job_id))

        return {"status": "success", "accepted": True, "job_id": job_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to regenerate job assessment for job_id {payload.job_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to regenerate job assessment: {e}")

@app.post("/update_job_applied")
async def update_job_applied_endpoint(payload: UpdateJobAppliedRequest = Body(...)):
    """
    Marks a job as applied by setting job_applied=1 and job_applied_timestamp to now for the given job_id.
    """
    try:
        job_id = payload.job_id
        job = await get_job_detail_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"job_id not found: {job_id}")

        affected = await update_job_applied(job_id)
        if affected == 0:
            raise HTTPException(status_code=404, detail=f"No rows updated for job_id: {job_id}")

        return {"status": "success", "job_id": job_id, "job_applied": 1}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update job_applied for {payload.job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update job_applied.")

@app.post("/update_job_unapplied")
async def update_job_unapplied_endpoint(payload: UpdateJobAppliedRequest = Body(...)):
    """
    Reverts a job to unapplied by setting job_applied=0 and job_applied_timestamp=NULL for the given job_id.
    """
    try:
        job_id = payload.job_id
        job = await get_job_detail_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"job_id not found: {job_id}")

        affected = await clear_job_applied(job_id)
        if affected == 0:
            raise HTTPException(status_code=404, detail=f"No rows updated for job_id: {job_id}")

        return {"status": "success", "job_id": job_id, "job_applied": 0}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update job_unapplied for {payload.job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update job_unapplied.")
