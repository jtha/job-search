import os
import uuid
import time
import json

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.types import Schema, Type

from .utilities import setup_logging, get_logger
from .db import (
    get_document_prompt_generate_job_assessment,
    get_document_master_resume,
    upsert_job_quarantine
)

load_dotenv()
setup_logging()
logger = get_logger(__name__)

client = genai.Client( api_key=os.getenv("GEMINI_API_KEY") )

job_assessment_schema = Schema(
    type=Type.OBJECT,
    properties={
        # 'job_assessment_rating': Schema(type=Type.STRING),
        # 'job_assessment_details': Schema(type=Type.STRING),
        'job_assessment_required_qualifications_matched_count': Schema(type=Type.INTEGER),
        'job_assessment_required_qualifications_count': Schema(type=Type.INTEGER),
        'job_assessment_additional_qualifications_matched_count': Schema(type=Type.INTEGER),
        'job_assessment_additional_qualifications_count': Schema(type=Type.INTEGER),
        'job_assessment_list_required_qualifications': Schema(
            type=Type.ARRAY,
            items=Schema(type=Type.STRING)
        ),
        'job_assessment_list_matched_required_qualifications': Schema(
            type=Type.ARRAY,
            items=Schema(type=Type.STRING)
        ),
        'job_assessment_list_additional_qualifications': Schema(
            type=Type.ARRAY,
            items=Schema(type=Type.STRING)
        ),
        'job_assessment_list_matched_additional_qualifications': Schema(
            type=Type.ARRAY,
            items=Schema(type=Type.STRING)
        ),
    },
    property_ordering=[
        'job_assessment_list_required_qualifications',
        'job_assessment_list_additional_qualifications',
        'job_assessment_list_matched_required_qualifications',
        'job_assessment_list_matched_additional_qualifications',
        'job_assessment_required_qualifications_count',
        'job_assessment_required_qualifications_matched_count',
        'job_assessment_additional_qualifications_count',
        'job_assessment_additional_qualifications_matched_count',
        # 'job_assessment_details',
        # 'job_assessment_rating',
    ]
)
    
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
        result = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                # max_output_tokens=10000,
                system_instruction=system_prompt["document_markdown"],
                response_mime_type="application/json",
                response_schema=job_assessment_schema
            )
        )

        # To do: Handle 429 and other errors

        if result is not None:
            logger.info("Job assessment generated successfully.")
            job_assessment_payload = result.parsed
            logger.info(f"prompt:{result.usage_metadata.prompt_token_count}, completion:{result.usage_metadata.candidates_token_count}, thinking:{result.usage_metadata.thoughts_token_count} total:{result.usage_metadata.total_token_count}") # type: ignore
            job_assessment_id = str(uuid.uuid4())

            # Convert list fields to JSON strings to store in the database
            job_assessment_payload["job_assessment_list_required_qualifications"] = json.dumps(job_assessment_payload["job_assessment_list_required_qualifications"]) # type: ignore
            job_assessment_payload["job_assessment_list_matched_required_qualifications"] = json.dumps(job_assessment_payload["job_assessment_list_matched_required_qualifications"]) # type: ignore
            job_assessment_payload["job_assessment_list_additional_qualifications"] = json.dumps(job_assessment_payload["job_assessment_list_additional_qualifications"]) # type: ignore
            job_assessment_payload["job_assessment_list_matched_additional_qualifications"] = json.dumps(job_assessment_payload["job_assessment_list_matched_additional_qualifications"]) # type: ignore

            # Add additional fields required for the job_assessment table to the job assessment payload
            job_assessment_payload["job_assessment_id"] = job_assessment_id # type: ignore
            job_assessment_payload["job_id"] = job_id # type: ignore
            job_assessment_payload['job_assessment_timestamp'] = int(time.time()) # type: ignore
            job_assessment_payload['job_assessment_resume_document_id'] = resume["document_id"] # type: ignore
            job_assessment_payload['job_assessment_prompt_document_id'] = system_prompt["document_id"] # type: ignore

            llm_runs_payload = {
                'llm_run_id': llm_run_id,
                'llm_run_type': 'generate_job_assessment',
                'llm_model_id': model,
                'job_id': job_id,
                'llm_prompt_document_id': system_prompt["document_id"],
                'llm_run_prompt_tokens': result.usage_metadata.prompt_token_count, # type: ignore
                'llm_run_completion_tokens': result.usage_metadata.candidates_token_count, # type: ignore
                'llm_run_thinking_tokens': result.usage_metadata.thoughts_token_count, # type: ignore
                'llm_run_total_tokens': result.usage_metadata.total_token_count, # type: ignore
                'assessment_id_link': job_assessment_id
            }

            return {'job_assessment': job_assessment_payload, 'llm_run': llm_runs_payload}
    except Exception as e:
        logger.exception("Error generating job assessment: %s", e)
        quarantine_id = str(uuid.uuid4())
        await upsert_job_quarantine(
            job_quarantine_id=quarantine_id,
            job_id=job_id,
            job_quarantine_reason="fail_generate_job_assessment"
                        )
        return None
    


