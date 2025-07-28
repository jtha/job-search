import os
import uuid
import time
import json
import asyncio
from jinja2 import Template
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.types import Schema, Type

from .utilities import setup_logging, get_logger
from .db import (
    get_document_master_resume,
    upsert_job_quarantine,
    get_latest_prompt,
    get_job_details_without_assessment,
    get_quarantined_job_details_for_assessment,
    upsert_llm_run_v2,
    upsert_job_skills
)

load_dotenv()
setup_logging()
logger = get_logger(__name__)

client = genai.Client( api_key=os.getenv("GEMINI_API_KEY") )

# Define response schemas for structured generation

response_schema_2_1=Schema(
    type = Type.OBJECT,
    required = ["tagged_list"],
    properties = {
        "tagged_list": Schema(
            type = Type.ARRAY,
            items = Schema(
                type = Type.OBJECT,
                required = ["2A_raw_string", "2B_category"],
                properties = {
                    "2A_raw_string": Schema(
                        type = Type.STRING,
                    ),
                    "2B_category": Schema(
                        type = Type.STRING,
                        enum = ["required", "additional"],
                    ),
                },
                property_ordering=[
                    "2A_raw_string",
                    "2B_category",
                ]
            ),
        ),
    }
)

response_schema_2_2 = Schema(
    type = Type.OBJECT,
    required = ["atomic_objects"],
    properties = {
        "atomic_objects": Schema(
            type = Type.ARRAY,
            items = Schema(
                type = Type.OBJECT,
                required = ["2A_atomic_string", "2B_category"],
                properties = {
                    "2A_atomic_string": Schema(
                        type = Type.STRING,
                    ),
                    "2B_category": Schema(
                        type = Type.STRING,
                        enum = ["required", "additional"],
                    ),
                },
                property_ordering=[
                    "2A_atomic_string",
                    "2B_category",
                ]
            ),
        ),
    },
)

response_schema_2_3 = Schema(
    type = Type.OBJECT,
    required = ["classification"],
    properties = {
        "classification": Schema(
            type = Type.STRING,
            enum = ["required_qualification", "additional_qualification", "evaluated_qualification"],
        ),
    }
)

response_schema_3_1 = Schema(
            type = Type.OBJECT,
            required = ["3A_match_reasoning", "3B_match"],
            properties = {
                "3A_match_reasoning": Schema(
                    type = Type.STRING,
                ),
                "3B_match": Schema(
                    type = Type.BOOLEAN,
                ),
            },
            property_ordering=[
                "3A_match_reasoning",
                "3B_match",
            ]
        )

async def generate(
        content: str, 
        system_instructions: str, 
        model:str, 
        temperature: float, 
        response_schema,
        thinking_config,
        job_id: str,
        llm_run_system_prompt_id: str,
        llm_run_type: str,
        max_output_tokens: Optional[int] = 2000
        ):
    llm_run_id = str(uuid.uuid4())
    
    try:
        time_start = time.time()
        response = await client.aio.models.generate_content(
            model=model,
            contents=content,
            config=types.GenerateContentConfig(
                system_instruction=system_instructions,
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=temperature,
                thinking_config=thinking_config,
                max_output_tokens=max_output_tokens
            )
        )
        time_end = time.time()
        # logger.info(f"Completed {llm_run_type} generation for job {job_id} with model {model}.")
        thoughts_token_count = getattr(response.usage_metadata, "thoughts_token_count", 0) or 0
        # logger.info(f"Input:{response.usage_metadata.prompt_token_count}, Output:{response.usage_metadata.candidates_token_count + thoughts_token_count}")  # type: ignore
        await upsert_llm_run_v2(
            llm_run_id=llm_run_id,
            job_id=job_id,
            llm_run_type=llm_run_type,
            llm_run_model_id=model,
            llm_run_system_prompt_id=llm_run_system_prompt_id,
            llm_run_input=content,
            llm_run_output=json.dumps(response.parsed),  # type: ignore
            llm_run_input_tokens=response.usage_metadata.prompt_token_count,  # type: ignore
            llm_run_output_tokens=response.usage_metadata.candidates_token_count,  # type: ignore
            llm_run_thinking_tokens=thoughts_token_count,  # type: ignore
            llm_run_total_tokens=response.usage_metadata.total_token_count,  # type: ignore
            llm_run_start=time_start,
            llm_run_end=time_end,
        )
        return {
            "data": response.parsed,
            "tokens": {
                "model": model,
                "input_tokens": response.usage_metadata.prompt_token_count,  # type: ignore
                "output_tokens": response.usage_metadata.candidates_token_count,  # type: ignore
                "thinking_tokens": thoughts_token_count,
                "total_tokens": response.usage_metadata.total_token_count,  # type: ignore
            }
        }
    except Exception as e:
        logger.exception(f"Error generating content: {e}")
        raise e

async def process_single_job_assessment(
    job: dict, 
    resume: dict,
    prompt_configuration_2_1: dict,
    prompt_configuration_2_2: dict, 
    prompt_configuration_2_3: dict,
    prompt_configuration_3_1: dict,
    semaphore: asyncio.Semaphore
) -> None:
    """Process assessment for a single job with semaphore control for concurrency."""
    async with semaphore:
        job_id = job['job_id']
        logger.info(f"Generating job assessment for job_id {job_id}")
        
        has_errors = False
        token_details_by_model = {}  # Track detailed token consumption by model
        
        # Step 2.1: Job description tagging
        content_2_1_template = Template(prompt_configuration_2_1['prompt_template'])
        content_2_1 = content_2_1_template.render(job_description=job['job_description'])
        try:
            result_2_1 = await generate(
                content=content_2_1,
                system_instructions=prompt_configuration_2_1['prompt_system_prompt'],
                model=prompt_configuration_2_1['model_id'],
                temperature=prompt_configuration_2_1['prompt_temperature'],
                response_schema=response_schema_2_1,
                thinking_config=types.ThinkingConfig(thinking_budget=prompt_configuration_2_1['prompt_thinking_budget']),
                job_id=job['job_id'],
                llm_run_system_prompt_id=prompt_configuration_2_1['prompt_id'],
                llm_run_type=prompt_configuration_2_1['llm_run_type']
            )
            # Track token usage
            model_name = result_2_1['tokens']['model']
            if model_name not in token_details_by_model:
                token_details_by_model[model_name] = {'input': 0, 'output': 0, 'thinking': 0}
            token_details_by_model[model_name]['input'] += result_2_1['tokens']['input_tokens']
            token_details_by_model[model_name]['output'] += result_2_1['tokens']['output_tokens']
            token_details_by_model[model_name]['thinking'] += result_2_1['tokens']['thinking_tokens']
        except Exception as e:
            logger.exception(f"Error generating job description tagging for job {job['job_id']}: {e}")
            await upsert_job_quarantine(
                job_quarantine_id=str(uuid.uuid4()),
                job_id=job['job_id'],
                job_quarantine_reason="failed_generate_jobdesc_tagging",
                job_quarantine_timestamp=int(time.time())
            )
            return

        # Step 2.2: Job description atomizing
        content_2_2_template = Template(prompt_configuration_2_2['prompt_template'])
        content_2_2 = content_2_2_template.render(tagged_list=str(result_2_1['data']['tagged_list'])) # type: ignore
        try:
            result_2_2 = await generate(
                content=content_2_2,
                system_instructions=prompt_configuration_2_2['prompt_system_prompt'],
                model=prompt_configuration_2_2['model_id'],
                temperature=prompt_configuration_2_2['prompt_temperature'],
                response_schema=response_schema_2_2,
                thinking_config=types.ThinkingConfig(thinking_budget=prompt_configuration_2_2['prompt_thinking_budget']),
                job_id=job['job_id'],
                llm_run_system_prompt_id=prompt_configuration_2_2['prompt_id'],
                llm_run_type=prompt_configuration_2_2['llm_run_type'],
                max_output_tokens=4000
            )
            # Track token usage
            model_name = result_2_2['tokens']['model']
            if model_name not in token_details_by_model:
                token_details_by_model[model_name] = {'input': 0, 'output': 0, 'thinking': 0}
            token_details_by_model[model_name]['input'] += result_2_2['tokens']['input_tokens']
            token_details_by_model[model_name]['output'] += result_2_2['tokens']['output_tokens']
            token_details_by_model[model_name]['thinking'] += result_2_2['tokens']['thinking_tokens']
        except Exception as e:
            logger.exception(f"Error generating job description atomizing for job {job['job_id']}: {e}")
            await upsert_job_quarantine(
                job_quarantine_id=str(uuid.uuid4()),
                job_id=job['job_id'],
                job_quarantine_reason="failed_generate_jobdesc_atomizing",
                job_quarantine_timestamp=int(time.time())
            )
            return

        # Step 2.3: Final classification for each atomic object
        final_classifications = []
        for item in result_2_2['data']['atomic_objects']:  # type: ignore
            new_item = {
                "atomic_string": item['2A_atomic_string'],  # type: ignore
                "category": item['2B_category']  # type: ignore
            }
            content_2_3_template = Template(prompt_configuration_2_3['prompt_template'])
            content_2_3 = content_2_3_template.render(input_object=str(new_item))
            try:
                result_2_3 = await generate(
                    content=content_2_3,
                    system_instructions=prompt_configuration_2_3['prompt_system_prompt'],
                    model=prompt_configuration_2_3['model_id'],
                    temperature=prompt_configuration_2_3['prompt_temperature'],
                    response_schema=response_schema_2_3,
                    thinking_config=types.ThinkingConfig(thinking_budget=prompt_configuration_2_3['prompt_thinking_budget']),
                    job_id=job['job_id'],
                    llm_run_system_prompt_id=prompt_configuration_2_3['prompt_id'],
                    llm_run_type=prompt_configuration_2_3['llm_run_type']
                )
                # Track token usage
                model_name = result_2_3['tokens']['model']
                if model_name not in token_details_by_model:
                    token_details_by_model[model_name] = {'input': 0, 'output': 0, 'thinking': 0}
                token_details_by_model[model_name]['input'] += result_2_3['tokens']['input_tokens']
                token_details_by_model[model_name]['output'] += result_2_3['tokens']['output_tokens']
                token_details_by_model[model_name]['thinking'] += result_2_3['tokens']['thinking_tokens']
                
                final_classifications.append({
                    "atomic_string": item['2A_atomic_string'],  # type: ignore
                    "classification": result_2_3['data']['classification']  # type: ignore
                })
            except Exception as e:
                logger.exception(f"Error generating final classification for job {job['job_id']}: {e}")
                has_errors = True
                break

        if has_errors:
            await upsert_job_quarantine(
                job_quarantine_id=str(uuid.uuid4()),
                job_id=job['job_id'],
                job_quarantine_reason="failed_generate_jobdesc_final",
                job_quarantine_timestamp=int(time.time())
            )
            return

        # Step 3.1: Assessment for each filtered item
        filtered_items = [item for item in final_classifications if item['classification'] != 'evaluated_qualification']
        for item in filtered_items:
            content_3_1_template = Template(prompt_configuration_3_1['prompt_template'])
            content_3_1 = content_3_1_template.render(
                candidate_profile=resume['document_markdown'],
                requirement_string=item['atomic_string'],  # type: ignore
            )
            try:
                result_3_1 = await generate(
                    content=content_3_1,
                    system_instructions=prompt_configuration_3_1['prompt_system_prompt'],
                    model=prompt_configuration_3_1['model_id'],
                    temperature=prompt_configuration_3_1['prompt_temperature'],
                    response_schema=response_schema_3_1,
                    thinking_config=types.ThinkingConfig(thinking_budget=prompt_configuration_3_1['prompt_thinking_budget']),
                    job_id=job['job_id'],
                    llm_run_system_prompt_id=prompt_configuration_3_1['prompt_id'],
                    llm_run_type=prompt_configuration_3_1['llm_run_type']
                )
                # Track token usage
                model_name = result_3_1['tokens']['model']
                if model_name not in token_details_by_model:
                    token_details_by_model[model_name] = {'input': 0, 'output': 0, 'thinking': 0}
                token_details_by_model[model_name]['input'] += result_3_1['tokens']['input_tokens']
                token_details_by_model[model_name]['output'] += result_3_1['tokens']['output_tokens']
                token_details_by_model[model_name]['thinking'] += result_3_1['tokens']['thinking_tokens']
                
                item['match_reasoning'] = result_3_1['data']['3A_match_reasoning']  # type: ignore
                item['match'] = result_3_1['data']['3B_match']  # type: ignore
            except Exception as e:
                logger.exception(f"Error generating assessment for job {job['job_id']}: {e}")
                has_errors = True
                break

        if has_errors:
            await upsert_job_quarantine(
                job_quarantine_id=str(uuid.uuid4()),
                job_id=job['job_id'],
                job_quarantine_reason="failed_generate_assessment",
                job_quarantine_timestamp=int(time.time())
            )
            return

        # Only upsert job skills if there were no errors in any preceding steps
        for item in filtered_items:
            await upsert_job_skills(
                job_skill_id=str(uuid.uuid4()),
                job_id=job['job_id'],
                job_skills_atomic_string=item['atomic_string'],  
                job_skills_type=item['classification'],  
                job_skills_match=item['match'],  
                job_skills_match_reasoning=item['match_reasoning'],
                job_skills_resume_id=resume['document_id'],
            )
        
        # Log completion with detailed token summary
        token_summary_parts = []
        for model, details in token_details_by_model.items():
            summary = f"{model}: input={details['input']}, output={details['output']}, thinking={details['thinking']}"
            token_summary_parts.append(summary)
        token_summary = "; ".join(token_summary_parts)
        logger.info(f"Job assessment finished for job_id {job_id}, token consumption by model: {token_summary}")

async def generate_job_assessment(limit:int=100, days_back:int=14, semaphore_count:int=5):

    resume = await get_document_master_resume()
    if resume["document_markdown"] is None:
        logger.error("Master resume not found.")
        return None

    prompt_configuration_2_1 = await get_latest_prompt("ja_2_1_jobdesc_tagging")
    if prompt_configuration_2_1 is None:
        logger.error("Prompt configuration for job description tagging not found.")
        return None
    prompt_configuration_2_2 = await get_latest_prompt("ja_2_2_jobdesc_atomizing")
    if prompt_configuration_2_2 is None:
        logger.error("Prompt configuration for job description atomizing not found.")
        return None
    prompt_configuration_2_3 = await get_latest_prompt("ja_2_3_jobdesc_final")
    if prompt_configuration_2_3 is None:
        logger.error("Prompt configuration for job description final processing not found.")
        return None
    prompt_configuration_3_1 = await get_latest_prompt("ja_3_1_assessment")
    if prompt_configuration_3_1 is None:
        logger.error("Prompt configuration for job assessment not found.")
        return None

    job_details = await get_job_details_without_assessment(limit=limit, days_back=days_back)
    if not job_details:
        # logger.info(f"No job details found without assessment for the last {days_back}")
        return None
    
    # logger.info(f"Found {len(job_details)} job details without assessment for the last {days_back} days.")

    # Create semaphore for controlling concurrency
    semaphore = asyncio.Semaphore(semaphore_count)
    
    # Create tasks for concurrent processing
    tasks = [
        process_single_job_assessment(
            job=job,
            resume=resume,
            prompt_configuration_2_1=prompt_configuration_2_1,
            prompt_configuration_2_2=prompt_configuration_2_2,
            prompt_configuration_2_3=prompt_configuration_2_3,
            prompt_configuration_3_1=prompt_configuration_3_1,
            semaphore=semaphore
        )
        for job in job_details
    ]
    
    # Execute all tasks concurrently with semaphore control
    # logger.info(f"Starting concurrent job assessment processing with {semaphore_count} concurrent tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    # logger.info(f"Completed processing {len(job_details)} jobs")

async def generate_failed_job_assessment(limit:int=100, days_back:int=14, semaphore_count:int=5):
    """
    Generates job assessments for quarantined jobs that failed previously.
    Uses the same logic as generate_job_assessment but filters for quarantined jobs.
    """
    resume = await get_document_master_resume()
    if resume["document_markdown"] is None:
        logger.error("Master resume not found.")
        return None

    prompt_configuration_2_1 = await get_latest_prompt("ja_2_1_jobdesc_tagging")
    if prompt_configuration_2_1 is None:
        logger.error("Prompt configuration for job description tagging not found.")
        return None
    prompt_configuration_2_2 = await get_latest_prompt("ja_2_2_jobdesc_atomizing")
    if prompt_configuration_2_2 is None:
        logger.error("Prompt configuration for job description atomizing not found.")
        return None
    prompt_configuration_2_3 = await get_latest_prompt("ja_2_3_jobdesc_final")
    if prompt_configuration_2_3 is None:
        logger.error("Prompt configuration for job description final processing not found.")
        return None
    prompt_configuration_3_1 = await get_latest_prompt("ja_3_1_assessment")
    if prompt_configuration_3_1 is None:
        logger.error("Prompt configuration for job assessment not found.")
        return None

    job_details = await get_quarantined_job_details_for_assessment(limit=limit, days_back=days_back)
    if not job_details:
        # logger.info(f"No quarantined job details found for assessment for the last {days_back} days")
        return None
    
    # logger.info(f"Found {len(job_details)} quarantined job details for assessment for the last {days_back} days.")

    # Create semaphore for controlling concurrency
    semaphore = asyncio.Semaphore(semaphore_count)
    
    # Create tasks for concurrent processing
    tasks = [
        process_single_job_assessment(
            job=job,
            resume=resume,
            prompt_configuration_2_1=prompt_configuration_2_1,
            prompt_configuration_2_2=prompt_configuration_2_2,
            prompt_configuration_2_3=prompt_configuration_2_3,
            prompt_configuration_3_1=prompt_configuration_3_1,
            semaphore=semaphore
        )
        for job in job_details
    ]
    
    # Execute all tasks concurrently with semaphore control
    # logger.info(f"Starting concurrent failed job assessment processing with {semaphore_count} concurrent tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    # logger.info(f"Completed processing {len(job_details)} quarantined jobs")