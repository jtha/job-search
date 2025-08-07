import os
import uuid
import time
import asyncio
import json
from jinja2 import Template
from typing import Optional, List
from enum import Enum
from typing import Type

from dotenv import load_dotenv
import httpx
from pydantic import BaseModel, Field

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
from .llm_examples import LLMExamples

load_dotenv()
setup_logging()
logger = get_logger(__name__)


# Pydantic models for response schemas

class CategoryEnum(str, Enum):
    required = "required"
    additional = "additional"

class ClassificationEnum(str, Enum):
    required_qualification = "required_qualification"
    additional_qualification = "additional_qualification"
    evaluated_qualification = "evaluated_qualification"

class TaggedList(BaseModel):
    raw_string: str = Field(..., description="Extracted qualification/skill from the job description")
    category: CategoryEnum = Field(..., description="The category of the raw string, can either be 'required' or 'additional'")

class AtomicObject(BaseModel):
    requirement_string: str = Field(..., description="The atomic string result from breaking down of qualifications/skills into atomic components")
    category: CategoryEnum = Field(..., description="The category of the atomic string, can either be 'required' or 'additional'")

class ClassifiedObject(BaseModel):
    requirement_string: str = Field(..., description="The provided requirement string")
    classification: ClassificationEnum = Field(..., description="The classification of the atomic string, can either be 'required_qualification', 'additional_qualification', or 'evaluated_qualification'")

class AssessedObject(BaseModel):
    requirement_string: str = Field(..., description="The atomic string requirement to be assessed against the candidate profile")
    match_reasoning: str = Field(..., description="The reasoning behind the match decision")
    match: bool = Field(..., description="Boolean indicating if the requirement matches the candidate profile")

class ResponseData_2_1(BaseModel):
    tagged_list: List[TaggedList] = Field(..., description="A list of tagged qualifications/skills extracted from the job description.")

class ResponseData_2_2(BaseModel):
    atomic_objects: List[AtomicObject] = Field(..., description="A list of atomic objects.")

class ResponseData_2_3(BaseModel):
    classified_objects: List[ClassifiedObject] = Field(..., description="A list of classified objects.")

class ResponseData_3_1(BaseModel):
    assessed_objects: List[AssessedObject] = Field(..., description="A list of assessed objects with match reasoning and boolean match.")

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
    "Content-Type": "application/json"
}

async def fetch_response(
    content: str, 
    system_instructions: str, 
    model: str, 
    temperature: float, 
    response_schema: Type[BaseModel], 
    max_reasoning_tokens: Optional[int] = 2000,
    examples: Optional[List[dict]] = None):

    # logger.info(f"Fetching response from OpenRouter for model {model} with temperature {temperature} and max reasoning tokens {max_reasoning_tokens}")

    messages = [{"role": "system", "content": system_instructions}]
    if examples:
        messages.extend(examples)
    messages.append({"role": "user", "content": content})

    payload = {
        "model": model,
        "messages": messages,
        "reasoning": {
            "effort": "low"
        },
        "response_format": {
            "type": "json_schema",
            "json_schema": response_schema.model_json_schema(),
        },
        "provider": {
            "order": ["deepinfra/fp4","nebius/fp4","fireworks"],
            "allow_fallbacks": False,
            "require_parameters": True
        },
        "usage": {
            "include": True
        },
        "temperature": temperature
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            text = response.json()['choices'][0]['message']['content']
            try:
                response_schema.model_validate_json(text)
                return response.json()
            except ValueError as ve:
                logger.exception(f"Response content: {text}")
                raise ValueError(f"Response validation error: {ve}")
        except httpx.HTTPStatusError as e:
            logger.exception(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            raise e

async def generate(
        content: str, 
        system_instructions: str, 
        model:str, 
        temperature: float, 
        response_schema,
        job_id: str,
        llm_run_system_prompt_id: str,
        llm_run_type: str,
        max_thinking: Optional[int] = 2000,
        examples: Optional[List[dict]] = None
        ):
    llm_run_id = str(uuid.uuid4())
    
    try:
        time_start = time.time()
        response = await fetch_response(
            content=content,
            system_instructions=system_instructions,
            model=model,
            temperature=temperature,
            response_schema=response_schema,
            max_reasoning_tokens=max_thinking,
            examples=examples
        )
        time_end = time.time()
        
        # Extract response data
        message_content = response['choices'][0]['message']['content']
        parsed_data = json.loads(message_content)
        
        # Extract token counts
        usage = response['usage']
        input_tokens = usage['prompt_tokens']
        output_tokens = usage['completion_tokens']
        reasoning_tokens = usage.get('completion_tokens_details', {}).get('reasoning_tokens', 0) or 0
        total_tokens = usage['total_tokens']
        
        llm_run_output = str(parsed_data)
        
        await upsert_llm_run_v2(
            llm_run_id=llm_run_id,
            job_id=job_id,
            llm_run_type=llm_run_type,
            llm_run_model_id=model,
            llm_run_system_prompt_id=llm_run_system_prompt_id,
            llm_run_input=content,
            llm_run_output=llm_run_output,
            llm_run_input_tokens=input_tokens,
            llm_run_output_tokens=output_tokens,
            llm_run_thinking_tokens=reasoning_tokens,
            llm_run_total_tokens=total_tokens,
            llm_run_start=time_start,
            llm_run_end=time_end,
        )
        
        return {
            "data": parsed_data,
            "tokens": {
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "thinking_tokens": reasoning_tokens,
                "total_tokens": total_tokens,
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
                response_schema=ResponseData_2_1,
                max_thinking=prompt_configuration_2_1['prompt_thinking_budget'],
                job_id=job['job_id'],
                llm_run_system_prompt_id=prompt_configuration_2_1['prompt_id'],
                llm_run_type=prompt_configuration_2_1['llm_run_type'],
                examples=LLMExamples.example_2_1
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
                response_schema=ResponseData_2_2,
                max_thinking=prompt_configuration_2_2['prompt_thinking_budget'],
                job_id=job['job_id'],
                llm_run_system_prompt_id=prompt_configuration_2_2['prompt_id'],
                llm_run_type=prompt_configuration_2_2['llm_run_type'],
                examples=LLMExamples.example_2_2
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

        # Step 2.3: Final classification for all atomic objects at once
        content_2_3_template = Template(prompt_configuration_2_3['prompt_template'])
        content_2_3 = content_2_3_template.render(atomic_objects=result_2_2['data']['atomic_objects'])  # type: ignore
        try:
            result_2_3 = await generate(
                content=content_2_3,
                system_instructions=prompt_configuration_2_3['prompt_system_prompt'],
                model=prompt_configuration_2_3['model_id'],
                temperature=prompt_configuration_2_3['prompt_temperature'],
                response_schema=ResponseData_2_3,
                max_thinking=prompt_configuration_2_3['prompt_thinking_budget'],
                job_id=job['job_id'],
                llm_run_system_prompt_id=prompt_configuration_2_3['prompt_id'],
                llm_run_type=prompt_configuration_2_3['llm_run_type'],
                examples=LLMExamples.example_2_3
            )
            # Track token usage
            model_name = result_2_3['tokens']['model']
            if model_name not in token_details_by_model:
                token_details_by_model[model_name] = {'input': 0, 'output': 0, 'thinking': 0}
            token_details_by_model[model_name]['input'] += result_2_3['tokens']['input_tokens']
            token_details_by_model[model_name]['output'] += result_2_3['tokens']['output_tokens']
            token_details_by_model[model_name]['thinking'] += result_2_3['tokens']['thinking_tokens']
            
            # Extract final classifications from the response
            final_classifications = []
            for classified_obj in result_2_3['data']['classified_objects']:  # type: ignore
                final_classifications.append({
                    "requirement_string": classified_obj['requirement_string'],
                    "classification": classified_obj['classification']
                })
        except Exception as e:
            logger.exception(f"Error generating final classification for job {job['job_id']}: {e}")
            has_errors = True

        if has_errors:
            await upsert_job_quarantine(
                job_quarantine_id=str(uuid.uuid4()),
                job_id=job['job_id'],
                job_quarantine_reason="failed_generate_jobdesc_final",
                job_quarantine_timestamp=int(time.time())
            )
            return False

        # Step 3.1: Assessment for all filtered items at once
        filtered_items = [item for item in final_classifications if item['classification'] != 'evaluated_qualification' and item['classification'] is not None and item['classification'] != '']
        
        if filtered_items:  # Only proceed if there are items to assess
            content_3_1_template = Template(prompt_configuration_3_1['prompt_template'])
            content_3_1 = content_3_1_template.render(
                candidate_profile=resume['document_markdown'],
                requirement_strings=filtered_items  # Pass the whole list
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
                        response_schema=ResponseData_3_1,
                        max_thinking=prompt_configuration_3_1['prompt_thinking_budget'],
                        job_id=job['job_id'],
                        llm_run_system_prompt_id=prompt_configuration_3_1['prompt_id'],
                        llm_run_type=prompt_configuration_3_1['llm_run_type'],
                        examples=LLMExamples.example_3_1
                    )
                    
                    # Validate the result - check if we have assessments for all filtered items
                    assessed_objects = result_3_1['data']['assessed_objects']  # type: ignore
                    if (not assessed_objects or 
                        len(assessed_objects) != len(filtered_items) or
                        any(obj['match_reasoning'] is None or obj['match'] is None for obj in assessed_objects)):
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
                    
                    # Map assessment results back to filtered_items
                    for i, assessed_obj in enumerate(assessed_objects):
                        if i < len(filtered_items):
                            filtered_items[i]['match_reasoning'] = assessed_obj['match_reasoning']
                            filtered_items[i]['match'] = assessed_obj['match']
                    
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
                             if filtered_item['requirement_string'] == item['requirement_string']), None)
            
            if match_data:
                # Item was processed for matching, use the match data
                await upsert_job_skills(
                    job_skill_id=str(uuid.uuid4()),
                    job_id=job['job_id'],
                    job_skills_atomic_string=item['requirement_string'],  
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
                    job_skills_atomic_string=item['requirement_string'],  
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

    prompt_configuration_2_1 = await get_latest_prompt("ja_2_1_assessment")
    if prompt_configuration_2_1 is None:
        logger.error("Prompt configuration for job description tagging not found.")
        return {"error": "Prompt configuration for job description tagging not found"}
    prompt_configuration_2_2 = await get_latest_prompt("ja_2_2_assessment")
    if prompt_configuration_2_2 is None:
        logger.error("Prompt configuration for job description atomizing not found.")
        return {"error": "Prompt configuration for job description atomizing not found"}
    prompt_configuration_2_3 = await get_latest_prompt("ja_2_3_assessment")
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

    prompt_configuration_2_1 = await get_latest_prompt("ja_2_1_assessment")
    if prompt_configuration_2_1 is None:
        logger.error("Prompt configuration for job description tagging not found.")
        return {"error": "Prompt configuration for job description tagging not found"}
    prompt_configuration_2_2 = await get_latest_prompt("ja_2_2_assessment")
    if prompt_configuration_2_2 is None:
        logger.error("Prompt configuration for job description atomizing not found.")
        return {"error": "Prompt configuration for job description atomizing not found"}
    prompt_configuration_2_3 = await get_latest_prompt("ja_2_3_assessment")
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