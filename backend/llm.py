import os
from pathlib import Path
from typing import Optional, Type, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from openai import AsyncOpenAI, NotGiven

from utilities import setup_logging, get_logger

load_dotenv()
setup_logging()
logger = get_logger(__name__)

client = AsyncOpenAI(
    api_key = os.getenv("OPENAI_API_KEY"),
    base_url = os.getenv("OPENAI_BASE_URL")
)

class JobPosting(BaseModel):
    rating: str
    assessment_details: str
    required_qualifications_matched_count: int
    required_qualifications_count: int
    additional_qualifications_matched_count: int
    additional_qualifications_count: int
    list_required_qualifications: list[str]
    list_matched_required_qualifications: list[str]
    list_additional_qualifications: list[str]
    list_matched_additional_qualifications: list[str]

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
    
async def generate_job_assessment(job_posting: str):
    resume = md_to_string("../backend/llm_prompts/master_resume.md")
    system_prompt = md_to_string("../backend/llm_prompts/generate_job_assessment.md")
    user_prompt = f"<resume>\n{resume}\n</resume>\n\n<job_posting>\n{job_posting}\n</job_posting>"
    logger.info("Generating job assessment...")
    result = await generate_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model="gemini-2.5-flash",
        temperature=0,
        response_model=JobPosting,
        reasoning_effort="medium"
    )
    if result is not None:
        logger.info(f"prompt:{result.usage.prompt_tokens}, completion:{result.usage.completion_tokens}, thinking:{result.usage.total_tokens-result.usage.prompt_tokens-result.usage.completion_tokens} total:{result.usage.total_tokens}") # type: ignore