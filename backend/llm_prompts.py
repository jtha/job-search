"""Legacy manual prompt seeding script.

This script now reuses the centralized initial prompt catalog and the same
seed function used at API startup. Running this manually will attempt the
same insert-if-missing logic so it is safe to invoke after initial startup.
"""

import asyncio
from .prompt_seed import seed_initial_prompts


def main():  # pragma: no cover - thin wrapper
    async def _run():
        from .utilities import get_logger, setup_logging
        setup_logging()
        logger = get_logger(__name__)
        from .db import Database
        await Database.get_instance()  # ensure connection
        result = await seed_initial_prompts()
        logger.info(
            "Manual seed run complete: inserted=%d existing=%d required=%d",
            len(result.inserted_run_types),
            len(result.existing_run_types),
            result.total_required,
        )

    asyncio.run(_run())


if __name__ == "__main__":
    main()