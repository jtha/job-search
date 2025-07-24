import os
from pathlib import Path
from typing import Optional, Type, Literal
import uuid
import time
import json

from dotenv import load_dotenv
from pydantic import BaseModel
from openai import AsyncOpenAI, NotGiven

from .utilities import setup_logging, get_logger
from .db import (
    get_document_prompt_generate_job_assessment,
    get_document_master_resume
)

load_dotenv()
setup_logging()
logger = get_logger(__name__)

client = AsyncOpenAI(
    api_key = os.getenv("OPENAI_API_KEY"),
    base_url = os.getenv("OPENAI_BASE_URL")
)

class JobPosting(BaseModel):
    job_assessment_rating: str
    job_assessment_details: str
    job_assessment_required_qualifications_matched_count: int
    job_assessment_required_qualifications_count: int
    job_assessment_additional_qualifications_matched_count: int
    job_assessment_additional_qualifications_count: int
    job_assessment_list_required_qualifications: list[str]
    job_assessment_list_matched_required_qualifications: list[str]
    job_assessment_list_additional_qualifications: list[str]
    job_assessment_list_matched_additional_qualifications: list[str]

def md_to_string(md_path: str) -> str:
    return Path(md_path).read_text(encoding="utf-8")

async def generate_text(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float,
    response_model: Optional[Type[BaseModel]] = None,
    reasoning_effort: Literal["low", "medium", "high"] = "medium"
):
    try:
        completion = await client.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format=response_model if response_model else NotGiven,
            temperature=temperature,
            reasoning_effort=reasoning_effort
        )
        return completion
    except Exception as e:
        logger.exception("Error generating text: %s", e)
        return None
    
async def generate_job_assessment(job_id:str, job_description: str, model: str = "gemini-2.5-flash"):
    """ Generates a job assessment based on the provided job description and model.
    Args:
        job_id (str): The ID of the job for which the assessment is being generated.
        job_description (str): The job description to be assessed.
        model (str): The model to use for generating the assessment. Defaults to "gemini-2.5-flash".
    Returns:
        dict: A dictionary containing the job assessment details, or None if an error occurs.
    """

    resume = await get_document_master_resume()
    if resume["document_markdown"] is None:
        logger.error("Master resume not found.")
        return None
    system_prompt = await get_document_prompt_generate_job_assessment()
    if system_prompt['document_markdown'] is None:
        logger.error("System prompt for job assessment generation not found.")
        return None
    user_prompt = f"<resume>\n{resume['document_markdown']}\n</resume>\n\n<job_posting>\n{job_description}\n</job_posting>"
    logger.info("Generating job assessment...")
    llm_run_id = str(uuid.uuid4())
    try:
        result = await generate_text(
            system_prompt=system_prompt["document_markdown"],
            user_prompt=user_prompt,
            model=model,
            temperature=0.3,
            response_model=JobPosting,
            reasoning_effort="medium"
        )

        # To do: Handle 429 and other errors

        if result is not None:
            logger.info("Job assessment generated successfully.")
            job_assessment_payload = result.choices[0].message.parsed.model_dump()  # type: ignore
            logger.info(f"prompt:{result.usage.prompt_tokens}, completion:{result.usage.completion_tokens}, thinking:{result.usage.total_tokens-result.usage.prompt_tokens-result.usage.completion_tokens} total:{result.usage.total_tokens}") # type: ignore
            job_assessment_id = str(uuid.uuid4())

            # Convert list fields to JSON strings to store in the database
            job_assessment_payload["job_assessment_list_required_qualifications"] = json.dumps(job_assessment_payload["job_assessment_list_required_qualifications"])
            job_assessment_payload["job_assessment_list_matched_required_qualifications"] = json.dumps(job_assessment_payload["job_assessment_list_matched_required_qualifications"])
            job_assessment_payload["job_assessment_list_additional_qualifications"] = json.dumps(job_assessment_payload["job_assessment_list_additional_qualifications"])
            job_assessment_payload["job_assessment_list_matched_additional_qualifications"] = json.dumps(job_assessment_payload["job_assessment_list_matched_additional_qualifications"])

            # Add additional fields required for the job_assessment table to the job assessment payload
            job_assessment_payload["job_assessment_id"] = job_assessment_id
            job_assessment_payload["job_id"] = job_id
            job_assessment_payload['job_assessment_timestamp'] = int(time.time())
            job_assessment_payload['job_assessment_resume_document_id'] = resume["document_id"]
            job_assessment_payload['job_assessment_prompt_document_id'] = system_prompt["document_id"]

            llm_runs_payload = {
                'llm_run_id': llm_run_id,
                'llm_run_type': 'generate_job_assessment',
                'llm_model_id': model,
                'job_id': job_id,
                'llm_prompt_document_id': system_prompt["document_id"],
                'llm_run_prompt_tokens': result.usage.prompt_tokens,  # type: ignore
                'llm_run_completion_tokens': result.usage.completion_tokens,  # type: ignore
                'llm_run_thinking_tokens': result.usage.total_tokens - result.usage.prompt_tokens - result.usage.completion_tokens,  # type: ignore
                'llm_run_total_tokens': result.usage.total_tokens,  # type: ignore
                'assessment_id_link': job_assessment_id
            }

            return {'job_assessment': job_assessment_payload, 'llm_run': llm_runs_payload}
    except Exception as e:
        logger.exception("Error generating job assessment: %s", e)
        return None