import os
import uuid
import time
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
    upsert_job_skills,
    delete_job_quarantine
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
            required = ["A_match_reasoning", "B_match"],
            properties = {
                "A_match_reasoning": Schema(
                    type = Type.STRING,
                ),
                "B_match": Schema(
                    type = Type.BOOLEAN,
                ),
            },
            property_ordering=[
                "A_match_reasoning",
                "B_match",
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
        if not response.parsed:
            llm_run_output = str(response.text)
        else:
            llm_run_output = str(response.parsed)
        await upsert_llm_run_v2(
            llm_run_id=llm_run_id,
            job_id=job_id,
            llm_run_type=llm_run_type,
            llm_run_model_id=model,
            llm_run_system_prompt_id=llm_run_system_prompt_id,
            llm_run_input=content,
            llm_run_output=llm_run_output,
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
) -> bool:
    """Process assessment for a single job with semaphore control for concurrency.
    
    Returns:
        bool: True if the job assessment was completed successfully, False if it failed.
    """
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
            return False

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
            return False

        # Step 2.3: Final classification for each atomic object
        final_classifications = []
        for item in result_2_2['data']['atomic_objects']:  # type: ignore
            content_2_3_template = Template(prompt_configuration_2_3['prompt_template'])
            content_2_3 = content_2_3_template.render(
                atomic_string=str(item['2A_atomic_string']),
                category=str(item['2B_category'])
            )
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
            return False

        # Step 3.1: Assessment for each filtered item
        filtered_items = [item for item in final_classifications if item['classification'] != 'evaluated_qualification' and item['classification'] is not None and item['classification'] != '']
        for item in filtered_items:
            content_3_1_template = Template(prompt_configuration_3_1['prompt_template'])
            content_3_1 = content_3_1_template.render(
                candidate_profile=resume['document_markdown'],
                requirement_string=item['atomic_string'],  # type: ignore
            )
            
            # Retry logic for step 3.1 with validation
            max_retries = 2
            retry_count = 0
            result_3_1 = None
            
            while retry_count <= max_retries:
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
                    
                    # Validate the result
                    if (result_3_1['data']['A_match_reasoning'] is None or 
                        result_3_1['data']['B_match'] is None):
                        if retry_count < max_retries:
                            retry_count += 1
                            logger.warning(f"Invalid result for job {job['job_id']}, retry {retry_count}/{max_retries}")
                            continue
                        else:
                            logger.error(f"Failed validation after {max_retries} retries for job {job['job_id']}")
                            has_errors = True
                            break
                    
                    # Track token usage
                    model_name = result_3_1['tokens']['model']
                    if model_name not in token_details_by_model:
                        token_details_by_model[model_name] = {'input': 0, 'output': 0, 'thinking': 0}
                    token_details_by_model[model_name]['input'] += result_3_1['tokens']['input_tokens']
                    token_details_by_model[model_name]['output'] += result_3_1['tokens']['output_tokens']
                    token_details_by_model[model_name]['thinking'] += result_3_1['tokens']['thinking_tokens']
                    
                    item['match_reasoning'] = result_3_1['data']['A_match_reasoning']  # type: ignore
                    item['match'] = result_3_1['data']['B_match']  # type: ignore
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    if retry_count < max_retries:
                        retry_count += 1
                        logger.warning(f"Error generating assessment for job {job['job_id']}, retry {retry_count}/{max_retries}: {e}")
                        continue
                    else:
                        logger.exception(f"Error generating assessment for job {job['job_id']} after {max_retries} retries: {e}")
                        has_errors = True
                        break
            
            if has_errors:
                break

        if has_errors:
            await upsert_job_quarantine(
                job_quarantine_id=str(uuid.uuid4()),
                job_id=job['job_id'],
                job_quarantine_reason="failed_generate_assessment",
                job_quarantine_timestamp=int(time.time())
            )
            return False

        # Only upsert job skills if there were no errors in any preceding steps
        # Upsert all skills from final_classifications, using match data if available
        for item in final_classifications:
            # Check if this item was processed for matching (in filtered_items)
            match_data = next((filtered_item for filtered_item in filtered_items 
                             if filtered_item['atomic_string'] == item['atomic_string']), None)
            
            if match_data:
                # Item was processed for matching, use the match data
                await upsert_job_skills(
                    job_skill_id=str(uuid.uuid4()),
                    job_id=job['job_id'],
                    job_skills_atomic_string=item['atomic_string'],  
                    job_skills_type=item['classification'],  
                    job_skills_match=match_data['match'],  
                    job_skills_match_reasoning=match_data['match_reasoning'],
                    job_skills_resume_id=resume['document_id'],
                )
            else:
                # Item was not processed for matching (e.g., evaluated_qualification), upsert without match data
                await upsert_job_skills(
                    job_skill_id=str(uuid.uuid4()),
                    job_id=job['job_id'],
                    job_skills_atomic_string=item['atomic_string'],  
                    job_skills_type=item['classification'],  
                    job_skills_match=None,  
                    job_skills_match_reasoning=None,
                    job_skills_resume_id=resume['document_id'],
                )
        
        # Log completion with detailed token summary
        token_summary_parts = []
        for model, details in token_details_by_model.items():
            summary = f"{model}: input={details['input']}, output={details['output']}, thinking={details['thinking']}"
            token_summary_parts.append(summary)
        token_summary = "; ".join(token_summary_parts)
        logger.info(f"Job assessment finished for job_id {job_id}, token consumption by model: {token_summary}")
        
        return True

async def generate_job_assessment(limit:int=100, days_back:int=14, semaphore_count:int=5):

    resume = await get_document_master_resume()
    if resume["document_markdown"] is None:
        logger.error("Master resume not found.")
        return {"error": "Master resume not found"}

    prompt_configuration_2_1 = await get_latest_prompt("ja_2_1_jobdesc_tagging")
    if prompt_configuration_2_1 is None:
        logger.error("Prompt configuration for job description tagging not found.")
        return {"error": "Prompt configuration for job description tagging not found"}
    prompt_configuration_2_2 = await get_latest_prompt("ja_2_2_jobdesc_atomizing")
    if prompt_configuration_2_2 is None:
        logger.error("Prompt configuration for job description atomizing not found.")
        return {"error": "Prompt configuration for job description atomizing not found"}
    prompt_configuration_2_3 = await get_latest_prompt("ja_2_3_jobdesc_final")
    if prompt_configuration_2_3 is None:
        logger.error("Prompt configuration for job description final processing not found.")
        return {"error": "Prompt configuration for job description final processing not found"}
    prompt_configuration_3_1 = await get_latest_prompt("ja_3_1_assessment")
    if prompt_configuration_3_1 is None:
        logger.error("Prompt configuration for job assessment not found.")
        return {"error": "Prompt configuration for job assessment not found"}

    job_details = await get_job_details_without_assessment(limit=limit, days_back=days_back)
    if not job_details:
        # logger.info(f"No job details found without assessment for the last {days_back}")
        return {"total_processed": 0, "successful": 0, "failed": 0, "exceptions": 0, "message": "No jobs found without assessment"}
    
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
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Count successful vs failed jobs for logging
    successful_count = sum(1 for result in results if isinstance(result, bool) and result)
    failed_count = sum(1 for result in results if isinstance(result, bool) and not result)
    exception_count = sum(1 for result in results if isinstance(result, Exception))
    
    # logger.info(f"Completed processing {len(job_details)} jobs: {successful_count} succeeded, {failed_count} failed, {exception_count} had exceptions")
    
    # Return summary of results
    return {
        "total_processed": len(job_details),
        "successful": successful_count,
        "failed": failed_count,
        "exceptions": exception_count
    }

async def generate_failed_job_assessment(limit:int=100, days_back:int=14, semaphore_count:int=5):
    """
    Generates job assessments for quarantined jobs that failed previously.
    Uses the same logic as generate_job_assessment but filters for quarantined jobs.
    """
    resume = await get_document_master_resume()
    if resume["document_markdown"] is None:
        logger.error("Master resume not found.")
        return {"error": "Master resume not found"}

    prompt_configuration_2_1 = await get_latest_prompt("ja_2_1_jobdesc_tagging")
    if prompt_configuration_2_1 is None:
        logger.error("Prompt configuration for job description tagging not found.")
        return {"error": "Prompt configuration for job description tagging not found"}
    prompt_configuration_2_2 = await get_latest_prompt("ja_2_2_jobdesc_atomizing")
    if prompt_configuration_2_2 is None:
        logger.error("Prompt configuration for job description atomizing not found.")
        return {"error": "Prompt configuration for job description atomizing not found"}
    prompt_configuration_2_3 = await get_latest_prompt("ja_2_3_jobdesc_final")
    if prompt_configuration_2_3 is None:
        logger.error("Prompt configuration for job description final processing not found.")
        return {"error": "Prompt configuration for job description final processing not found"}
    prompt_configuration_3_1 = await get_latest_prompt("ja_3_1_assessment")
    if prompt_configuration_3_1 is None:
        logger.error("Prompt configuration for job assessment not found.")
        return {"error": "Prompt configuration for job assessment not found"}

    job_details = await get_quarantined_job_details_for_assessment(limit=limit, days_back=days_back)
    if not job_details:
        # logger.info(f"No quarantined job details found for assessment for the last {days_back} days")
        return {"total_processed": 0, "successful": 0, "failed": 0, "exceptions": 0, "quarantine_removed": 0, "message": "No quarantined jobs found for assessment"}
    
    # logger.info(f"Found {len(job_details)} quarantined job details for assessment for the last {days_back} days.")

    # Create semaphore for controlling concurrency
    semaphore = asyncio.Semaphore(semaphore_count)
    
    # Create tasks for concurrent processing with job info
    job_assessment_tasks = [
        (job, process_single_job_assessment(
            job=job,
            resume=resume,
            prompt_configuration_2_1=prompt_configuration_2_1,
            prompt_configuration_2_2=prompt_configuration_2_2,
            prompt_configuration_2_3=prompt_configuration_2_3,
            prompt_configuration_3_1=prompt_configuration_3_1,
            semaphore=semaphore
        ))
        for job in job_details
    ]
    
    # Execute all tasks concurrently with semaphore control
    # logger.info(f"Starting concurrent failed job assessment processing with {semaphore_count} concurrent tasks")
    results = await asyncio.gather(*[task for _, task in job_assessment_tasks], return_exceptions=True)
    
    # Process results and delete quarantine records for successful jobs
    successful_jobs = []
    failed_count = 0
    exception_count = 0
    
    for i, (job, result) in enumerate(zip([job for job, _ in job_assessment_tasks], results)):
        if isinstance(result, bool) and result:  # Success
            successful_jobs.append(job['job_id'])
            await delete_job_quarantine(job['job_id'])
        elif isinstance(result, bool) and not result:  # Failed
            failed_count += 1
        elif isinstance(result, Exception):
            logger.exception(f"Task failed with exception for job {job['job_id']}: {result}")
            exception_count += 1
    
    if successful_jobs:
        logger.info(f"Successfully processed and removed quarantine for {len(successful_jobs)} jobs: {successful_jobs}")
    
    # logger.info(f"Completed processing {len(job_details)} quarantined jobs, {len(successful_jobs)} succeeded")
    
    # Return summary of results
    return {
        "total_processed": len(job_details),
        "successful": len(successful_jobs),
        "failed": failed_count,
        "exceptions": exception_count,
        "quarantine_removed": len(successful_jobs)
    }