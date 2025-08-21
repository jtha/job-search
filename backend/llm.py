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
import json_repair

from .utilities import setup_logging, get_logger
from .db import (
    get_document_master_resume,
    get_document_master_resume_json,
    upsert_job_quarantine,
    get_latest_prompt,
    get_job_details,
    upsert_llm_run_v2,
    upsert_job_skills,
    get_job_skills_for_job
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

# HTTP timeout and retry configuration (env-overridable)
DEFAULT_HTTP_READ_TIMEOUT = float(os.getenv("LLM_HTTP_TIMEOUT", "180"))  # seconds
DEFAULT_HTTP_CONNECT_TIMEOUT = float(os.getenv("LLM_HTTP_CONNECT_TIMEOUT", "30"))
DEFAULT_HTTP_WRITE_TIMEOUT = float(os.getenv("LLM_HTTP_WRITE_TIMEOUT", "180"))
DEFAULT_HTTP_POOL_TIMEOUT = float(os.getenv("LLM_HTTP_POOL_TIMEOUT", "30"))
DEFAULT_HTTP_MAX_RETRIES = int(os.getenv("LLM_HTTP_MAX_RETRIES", "2"))
DEFAULT_HTTP_BACKOFF_BASE = float(os.getenv("LLM_HTTP_BACKOFF_BASE", "0.75"))  # seconds

async def fetch_response(
    content: str, 
    system_instructions: str, 
    model: str, 
    temperature: float, 
    response_schema: Type[BaseModel], 
    max_reasoning_tokens: Optional[int] = 2000,
    examples: Optional[List[dict]] = None,
    timeout_read: Optional[float] = None,
    timeout_connect: Optional[float] = None,
    timeout_write: Optional[float] = None,
    max_retries: Optional[int] = None):
    """Call the OpenRouter chat completions endpoint with a JSON schema enforced response.

    This function:
      * Assembles the messages (system + optional few-shot examples + user)
      * Specifies a JSON schema (pydantic model) the model must conform to
      * Implements retry logic for transient network/server errors with exponential backoff
      * Attempts several lightweight repairs of model output (code fences, key aliases, category normalization)
      * Validates (or re-validates) the repaired JSON against the provided pydantic schema

    Parameters
    ----------
    content : str
        The user message / main prompt content.
    system_instructions : str
        The system prompt / instructions.
    model : str
        Model identifier (OpenRouter routing string).
    temperature : float
        Sampling temperature.
    response_schema : Type[BaseModel]
        Pydantic model that constrains and validates the JSON response.
    max_reasoning_tokens : Optional[int]
        Reserved reasoning token budget passed to provider (if applicable).
    examples : Optional[List[dict]]
        Few-shot example messages (each item must have role+content as expected by API).
    timeout_read / timeout_connect / timeout_write : Optional[float]
        Optional overrides for httpx timeout phases (seconds).
    max_retries : Optional[int]
        Override for number of retry attempts on transient failures.

    Returns
    -------
    dict
        Raw (repaired if needed) JSON response object from OpenRouter with validated content.

    Raises
    ------
    ValueError
        If the response cannot be validated against the schema after repair attempts.
    httpx.HTTPError
        For non-retriable HTTP failures.
    """

    logger.debug(
        "Fetching response from OpenRouter for model %s (temp=%s, max_reasoning_tokens=%s)",
        model, temperature, max_reasoning_tokens
    )

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
        # "provider": {
        #     "order": ["fireworks","together","openai","ncompass"],
        #     "allow_fallbacks": True,
        #     "require_parameters": True
        # },
        "usage": {
            "include": True
        },
        "temperature": temperature
    }

    # Determine effective timeouts and retries
    read_t = timeout_read if timeout_read is not None else DEFAULT_HTTP_READ_TIMEOUT
    conn_t = timeout_connect if timeout_connect is not None else DEFAULT_HTTP_CONNECT_TIMEOUT
    write_t = timeout_write if timeout_write is not None else DEFAULT_HTTP_WRITE_TIMEOUT
    retries = DEFAULT_HTTP_MAX_RETRIES if max_retries is None else max_retries

    def _strip_code_fences(s: str) -> str:
        s_strip = s.strip()
        if s_strip.startswith("```") and s_strip.endswith("```"):
            s_strip = s_strip.strip("`")
            # After stripping backticks, there may be a leading language tag like 'json' and a newline
            lines = s_strip.splitlines()
            if lines and lines[0].strip().lower() in {"json", "json5", "javascript"}:
                s_strip = "\n".join(lines[1:])
            return s_strip
        return s

    def _normalize_categories(val: Optional[str]) -> Optional[str]:
        if val is None:
            return None
        v = str(val).strip().lower()
        if v in {"required", "must", "mandatory"}:
            return "required"
        if v in {"additional", "nice to have", "desired", "preferred", "plus"}:
            return "additional"
        return val

    def _normalize_classification(val: Optional[str]) -> Optional[str]:
        if val is None:
            return None
        v = str(val).strip().lower()
        mapping = {
            "required": "required_qualification",
            "additional": "additional_qualification",
            "evaluated": "evaluated_qualification",
            "required_qualification": "required_qualification",
            "additional_qualification": "additional_qualification",
            "evaluated_qualification": "evaluated_qualification",
        }
        return mapping.get(v, val)

    def _repair_payload_for_schema(obj: dict) -> dict:
        # Generic repairs for known response shapes
        if isinstance(obj, dict):
            # 2.1 tagged_list
            if isinstance(obj.get("tagged_list"), list):
                for item in obj["tagged_list"]:
                    if isinstance(item, dict):
                        if "raw_string" not in item:
                            if "raw" in item:
                                item["raw_string"] = item.pop("raw")
                            elif "text" in item:
                                item["raw_string"] = item.pop("text")
                        if "category" in item:
                            item["category"] = _normalize_categories(item.get("category")) or item.get("category")

            # 2.2 atomic_objects
            if isinstance(obj.get("atomic_objects"), list):
                for item in obj["atomic_objects"]:
                    if isinstance(item, dict):
                        if "requirement_string" not in item and "requirement" in item:
                            item["requirement_string"] = item.pop("requirement")
                        if "category" in item:
                            item["category"] = _normalize_categories(item.get("category")) or item.get("category")

            # 2.3 classified_objects
            if isinstance(obj.get("classified_objects"), list):
                for item in obj["classified_objects"]:
                    if isinstance(item, dict):
                        if "requirement_string" not in item and "requirement" in item:
                            item["requirement_string"] = item.pop("requirement")
                        if "classification" in item:
                            item["classification"] = _normalize_classification(item.get("classification"))

            # 3.1 assessed_objects
            if isinstance(obj.get("assessed_objects"), list):
                for item in obj["assessed_objects"]:
                    if isinstance(item, dict):
                        if "requirement_string" not in item and "requirement" in item:
                            item["requirement_string"] = item.pop("requirement")
                        if "match_reasoning" not in item and "reasoning" in item:
                            item["match_reasoning"] = item.pop("reasoning")
                        if "match" in item:
                            mv = item["match"]
                            if isinstance(mv, str):
                                mvs = mv.strip().lower()
                                if mvs in {"yes", "true"}:
                                    item["match"] = True
                                elif mvs in {"no", "false"}:
                                    item["match"] = False
        return obj

    attempt = 0
    while True:
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=conn_t, read=read_t, write=write_t, pool=DEFAULT_HTTP_POOL_TIMEOUT)
            ) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                # resp_json = response.json()
                resp_json = json_repair.repair_json(response.text, return_objects=True)
                text = resp_json['choices'][0]['message']['content'] # type: ignore
                # First, strip potential code fences
                candidate_text = _strip_code_fences(text)
                try:
                    response_schema.model_validate_json(candidate_text)
                    # If we stripped fences, embed the cleaned text back; otherwise return original
                    if candidate_text != text:
                        resp_json['choices'][0]['message']['content'] = candidate_text # type: ignore
                    return resp_json
                except ValueError:
                    # Attempt to repair common key/format issues and revalidate
                    try:
                        data_obj = json.loads(candidate_text)
                        repaired = _repair_payload_for_schema(data_obj)
                        repaired_text = json.dumps(repaired, ensure_ascii=False)
                        response_schema.model_validate_json(repaired_text)
                        resp_json['choices'][0]['message']['content'] = repaired_text # type: ignore
                        return resp_json
                    except Exception as ve2:
                        logger.exception(f"Response content: {text}")
                        raise ValueError(f"Response validation error: {ve2}")
        except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.RemoteProtocolError) as e:
            if attempt >= retries:
                logger.exception(
                    f"HTTP timeout-related error after {attempt+1} attempt(s): {e}"
                )
                raise
            # Exponential backoff with small jitter based on loop time fraction
            jitter = 0.1 * (asyncio.get_running_loop().time() % 1)
            backoff = DEFAULT_HTTP_BACKOFF_BASE * (2 ** attempt) + jitter
            logger.warning(
                f"Timeout-related error (attempt {attempt+1}/{retries+1}) for model {model}; "
                f"retrying in {backoff:.2f}s... Error: {type(e).__name__}"
            )
            await asyncio.sleep(backoff)
            attempt += 1
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            is_server_error = 500 <= status < 600
            if is_server_error and attempt < retries:
                jitter = 0.1 * (asyncio.get_running_loop().time() % 1)
                backoff = DEFAULT_HTTP_BACKOFF_BASE * (2 ** attempt) + jitter
                logger.warning(
                    f"HTTP {status} from OpenRouter (attempt {attempt+1}/{retries+1}); retrying in {backoff:.2f}s..."
                )
                await asyncio.sleep(backoff)
                attempt += 1
                continue
            logger.exception(f"HTTP error occurred: {status} - {e.response.text}")
            raise

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
    """High-level wrapper around `fetch_response` that records metadata in persistence layer.

    Responsibilities:
      * Invoke the LLM (structured) via `fetch_response`.
      * Parse validated JSON content.
      * Extract usage metrics (tokens, reasoning tokens if available).
      * Record the run (audit trail) to the database via `upsert_llm_run_v2`.

    Returns
    -------
    dict
        {"data": <parsed json>, "tokens": {model, input_tokens, output_tokens, thinking_tokens, total_tokens}}
    """
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
        message_content = response['choices'][0]['message']['content']  # type: ignore
        parsed_data = json.loads(message_content)

        # Extract token counts
        usage = response['usage']  # type: ignore
        input_tokens = usage['prompt_tokens']  # type: ignore
        output_tokens = usage['completion_tokens']  # type: ignore
        reasoning_tokens = usage.get('completion_tokens_details', {}).get('reasoning_tokens', 0) or 0  # type: ignore
        total_tokens = usage['total_tokens']  # type: ignore

        llm_run_output = str(parsed_data)

        await upsert_llm_run_v2(
            llm_run_id=llm_run_id,
            job_id=job_id,
            llm_run_type=llm_run_type,
            llm_run_model_id=model,
            llm_run_system_prompt_id=llm_run_system_prompt_id,
            llm_run_input=content,
            llm_run_output=llm_run_output,
            llm_run_input_tokens=input_tokens,  # type: ignore
            llm_run_output_tokens=output_tokens,  # type: ignore
            llm_run_thinking_tokens=reasoning_tokens,
            llm_run_total_tokens=total_tokens,  # type: ignore
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
    resume_json: dict,
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
    # Helper for consistent token usage aggregation (local, inner to avoid exporting globally)
    def _accumulate_tokens(model_name: str, token_details_by_model: dict, result: dict):
        details = token_details_by_model.setdefault(model_name, {'input': 0, 'output': 0, 'thinking': 0})
        details['input'] += result['tokens']['input_tokens']
        details['output'] += result['tokens']['output_tokens']
        details['thinking'] += result['tokens']['thinking_tokens']
    async with semaphore:
        job_id = job['job_id']
        logger.info(f"Generating job assessment for job_id {job_id}")

        has_errors = False
        token_details_by_model: dict = {}  # Track detailed token consumption by model

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
            _accumulate_tokens(result_2_1['tokens']['model'], token_details_by_model, result_2_1)
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
        content_2_2 = content_2_2_template.render(tagged_list=str(result_2_1['data']['tagged_list']))  # type: ignore
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
            _accumulate_tokens(result_2_2['tokens']['model'], token_details_by_model, result_2_2)
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
            _accumulate_tokens(result_2_3['tokens']['model'], token_details_by_model, result_2_3)

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

        if filtered_items:
            content_3_1_template = Template(prompt_configuration_3_1['prompt_template'])
            content_3_1 = content_3_1_template.render(
                candidate_profile=resume_json['document_markdown'],
                resume_text=resume['document_markdown'],
                requirement_strings=filtered_items
            )

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

                    _accumulate_tokens(result_3_1['tokens']['model'], token_details_by_model, result_3_1)

                    for i, assessed_obj in enumerate(assessed_objects):
                        if i < len(filtered_items):
                            filtered_items[i]['match_reasoning'] = assessed_obj['match_reasoning']
                            filtered_items[i]['match'] = assessed_obj['match']

                    break

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

        for item in final_classifications:
            match_data = next((filtered_item for filtered_item in filtered_items
                               if filtered_item['requirement_string'] == item['requirement_string']), None)

            if match_data:
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
                await upsert_job_skills(
                    job_skill_id=str(uuid.uuid4()),
                    job_id=job['job_id'],
                    job_skills_atomic_string=item['requirement_string'],
                    job_skills_type=item['classification'],
                    job_skills_match=None,
                    job_skills_match_reasoning=None,
                    job_skills_resume_id=resume['document_id'],
                )

        token_summary = "; ".join(
            f"{model}: input={d['input']}, output={d['output']}, thinking={d['thinking']}"
            for model, d in token_details_by_model.items()
        )
        logger.info(f"Completed job assessment for job_id {job_id}")
        logger.info(f"Usage for job_id {job_id}: {token_summary}")

        return True

async def generate_job_assessment_with_id(job_id: str):
    """
    Generate job assessment for a specific job_id if not yet performed.
    - If job_skills already exist for the job_id, return them immediately.
    - Otherwise, run the same pipeline used in generate_job_assessment for that single job,
      then return the resulting job_skills for the job_id.
    """
    # NOTE: This function intentionally keeps a linear flow for clarity; early returns handle failure cases.

    try:
        existing = await get_job_skills_for_job(job_id)
    except Exception as e:
        logger.exception(f"Failed to query existing job skills for job_id {job_id}: {e}")
        return {"error": f"Failed to query existing job skills for job_id {job_id}"}

    if existing:
        return existing

    try:
        all_jobs = await get_job_details()
        job = next((j for j in all_jobs if j.get("job_id") == job_id), None)
    except Exception as e:
        logger.exception(f"Failed to load job details for job_id {job_id}: {e}")
        return {"error": f"Failed to load job details for job_id {job_id}"}

    if not job:
        return {"error": f"job_id {job_id} not found in job_details"}
    if not job.get("job_description"):
        return {"error": f"job_id {job_id} has no job_description"}

    resume_json = await get_document_master_resume_json()
    resume = await get_document_master_resume()

    if resume_json["document_markdown"] is None:
        logger.error("Master resume not found.")
        return {"error": "Master resume not found"}

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

    semaphore = asyncio.Semaphore(1)
    try:
        success = await process_single_job_assessment(
            job={"job_id": job_id, "job_description": job["job_description"]},
            resume=resume,
            resume_json=resume_json,
            prompt_configuration_2_1=prompt_configuration_2_1,
            prompt_configuration_2_2=prompt_configuration_2_2,
            prompt_configuration_2_3=prompt_configuration_2_3,
            prompt_configuration_3_1=prompt_configuration_3_1,
            semaphore=semaphore,
        )
    except Exception as e:
        logger.exception(f"Exception while processing assessment for job_id {job_id}: {e}")
        return {"error": f"Failed to generate assessment for job_id {job_id}"}

    if not success:
        # Return empty skills to indicate no data created (or user can inspect quarantine)
        return []

    try:
        return await get_job_skills_for_job(job_id)
    except Exception as e:
        logger.exception(f"Failed to load generated job skills for job_id {job_id}: {e}")
        return {"error": f"Generated assessment but failed to load job skills for job_id {job_id}"}



