"""One-time initial prompt seeding utilities.

seed_initial_prompts() will ensure each required llm_run_type defined in
prompt_catalog_initial exists at least once in the prompt table. If a run type
already exists (any row), it is left untouched. Only missing run types are
inserted. This function is safe and idempotent to call multiple times.
"""
from __future__ import annotations
import uuid
import time
from dataclasses import dataclass
from typing import List

from .db import get_db
from .utilities import get_logger
from .prompt_catalog_initial import INITIAL_PROMPT_SPECS, REQUIRED_LLM_RUN_TYPES

logger = get_logger(__name__)

@dataclass
class SeedResult:
    inserted_run_types: List[str]
    existing_run_types: List[str]
    total_required: int

async def seed_initial_prompts() -> SeedResult:
    """Insert missing initial prompts by llm_run_type.

    Returns a SeedResult summarizing the action.
    """
    db = await get_db()

    # Fetch existing run types present already
    async with db.execute(
        "SELECT DISTINCT llm_run_type FROM prompt WHERE llm_run_type IS NOT NULL"
    ) as cursor:
        rows = await cursor.fetchall()
        existing = {r[0] for r in rows if r[0] is not None}

    inserted: List[str] = []
    for spec in INITIAL_PROMPT_SPECS:
        if spec.llm_run_type in existing:
            continue
        # Insert new prompt row
        prompt_id = str(uuid.uuid4())
        await db.execute(
            """
            INSERT INTO prompt (
                prompt_id, llm_run_type, model_id, prompt_system_prompt, prompt_template,
                prompt_temperature, prompt_response_schema, prompt_created_at, prompt_thinking_budget
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prompt_id,
                spec.llm_run_type,
                spec.model_id,
                spec.prompt_system_prompt,
                spec.prompt_template,
                spec.prompt_temperature,
                None,  # response schema not used in initial seed
                int(time.time()),
                spec.prompt_thinking_budget,
            ),
        )
        inserted.append(spec.llm_run_type)

    if inserted:
        await db.commit()
    else:
        # Still commit to release any implicit read transaction cleanly
        await db.commit()

    existing_run_types = sorted(existing.intersection(REQUIRED_LLM_RUN_TYPES))

    result = SeedResult(
        inserted_run_types=inserted,
        existing_run_types=existing_run_types,
        total_required=len(REQUIRED_LLM_RUN_TYPES),
    )

    logger.info(
        "initial_prompt_seed: inserted=%s existing=%s total_required=%d",\
        len(result.inserted_run_types), len(result.existing_run_types), result.total_required
    )
    if result.inserted_run_types:
        logger.info("initial_prompt_seed: newly inserted run_types=%s", result.inserted_run_types)

    return result
