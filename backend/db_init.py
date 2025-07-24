import os
import glob
import aiosqlite
import aiofiles
import asyncio

from utilities import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)
DB_FILE = os.getenv("DB_FILE", "job_tracker.db")
SQL_DIR = "sql"

async def initialize_database():
    """
    Initializes the database for asynchronous access.
    Creates the DB file and runs all .sql scripts from the SQL_DIR.
    """

    async with aiosqlite.connect(DB_FILE, timeout=3) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        logger.info(f"Database '{DB_FILE}' created or connected successfully.")
        
        # This must be done for every connection to enforce foreign keys.
        await db.execute("PRAGMA foreign_keys = ON;")
        
        script_dir = os.path.dirname(__file__)
        sql_path = os.path.join(script_dir, SQL_DIR, '*.sql')
        sql_files = sorted(glob.glob(sql_path))
        
        if not sql_files:
            logger.warning(f"No .sql files found in '{SQL_DIR}' directory.")
            return

        logger.info("Initializing tables...")
        for sql_file in sql_files:
            async with aiofiles.open(sql_file, 'r') as f:
                sql_script = await f.read()
                await db.executescript(sql_script)
                logger.info(f"  - Executed {os.path.basename(sql_file)}")

        await db.commit()

    logger.info("\nDatabase initialization complete. All tables are ready.")

def main():
    asyncio.run(initialize_database())

if __name__ == "__main__":
    main()