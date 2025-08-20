# import asyncio
# import aiosqlite
# import os
# import sys
# from typing import Optional

# # Add the backend directory to the path so we can import utilities
# sys.path.append(os.path.dirname(__file__))
# from utilities import setup_logging, get_logger

# setup_logging()
# logger = get_logger(__name__)

# DB_FILE = os.getenv("DB_FILE", "job_tracker.db")

# async def check_column_exists(db: aiosqlite.Connection, table_name: str, column_name: str) -> bool:
#     """Check if a column exists in a table."""
#     async with db.execute(f"PRAGMA table_info({table_name})") as cursor:
#         columns = await cursor.fetchall()
#         column_names = [column[1] for column in columns]
#         return column_name in column_names

# async def backup_database():
#     """Create a backup of the database before migration."""
#     import shutil
#     from datetime import datetime
    
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     backup_name = f"{DB_FILE}.backup_{timestamp}"
    
#     try:
#         shutil.copy2(DB_FILE, backup_name)
#         logger.info(f"Database backup created: {backup_name}")
#         return backup_name
#     except Exception as e:
#         logger.error(f"Failed to create backup: {e}")
#         raise

# async def get_all_foreign_keys(db: aiosqlite.Connection) -> dict:
#     """Get all foreign key constraints for all tables."""
#     foreign_keys = {}
    
#     # Get list of all tables
#     async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'") as cursor:
#         tables = await cursor.fetchall()
    
#     for table in tables:
#         table_name = table[0]
#         async with db.execute(f"PRAGMA foreign_key_list({table_name})") as cursor:
#             fks = await cursor.fetchall()
#             if fks:
#                 foreign_keys[table_name] = fks
    
#     return foreign_keys

# async def migrate_document_store():
#     """
#     Migration script to add document_job_id_reference and document_job_type columns 
#     to the document_store table with a foreign key constraint.
#     """
#     logger.info("Starting document_store table migration...")
    
#     # Create backup first
#     backup_file = await backup_database()
    
#     try:
#         async with aiosqlite.connect(DB_FILE, timeout=10) as db:
#             # Enable foreign keys
#             await db.execute("PRAGMA foreign_keys = ON;")
            
#             # Check if columns already exist
#             job_id_ref_exists = await check_column_exists(db, "document_store", "document_job_id_reference")
#             job_type_exists = await check_column_exists(db, "document_store", "document_job_type")
            
#             if job_id_ref_exists and job_type_exists:
#                 logger.info("Migration already completed - columns already exist.")
#                 return
            
#             # Check current schema
#             logger.info("Current document_store schema:")
#             async with db.execute("PRAGMA table_info(document_store)") as cursor:
#                 columns = await cursor.fetchall()
#                 for col in columns:
#                     logger.info(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'}")
            
#             # Get current data count
#             async with db.execute("SELECT COUNT(*) FROM document_store") as cursor:
#                 row = await cursor.fetchone()
#                 row_count = row[0] if row else 0
#             logger.info(f"Current document_store contains {row_count} rows")
            
#             # Get all existing foreign keys before migration
#             logger.info("Preserving existing foreign key constraints...")
#             all_foreign_keys = await get_all_foreign_keys(db)
            
#             # Begin transaction
#             logger.info("Starting migration transaction...")
#             await db.execute("BEGIN TRANSACTION;")
            
#             try:
#                 # Step 1: Disable foreign key checks temporarily
#                 await db.execute("PRAGMA foreign_keys = OFF;")
                
#                 # Step 2: Create new table with updated schema
#                 logger.info("Creating new document_store table with additional columns...")
#                 await db.execute("""
#                     CREATE TABLE document_store_new (
#                         document_id                 TEXT PRIMARY KEY,
#                         document_name               TEXT NOT NULL,
#                         document_timestamp          INTEGER NOT NULL,
#                         document_markdown           TEXT,
#                         document_job_id_reference   TEXT,
#                         document_job_type           TEXT,
#                         FOREIGN KEY (document_job_id_reference) REFERENCES job_details(job_id)
#                     );
#                 """)
                
#                 # Step 3: Copy existing data to new table
#                 if row_count > 0:
#                     logger.info("Copying existing data to new table...")
#                     await db.execute("""
#                         INSERT INTO document_store_new (
#                             document_id, 
#                             document_name, 
#                             document_timestamp, 
#                             document_markdown,
#                             document_job_id_reference,
#                             document_job_type
#                         )
#                         SELECT 
#                             document_id, 
#                             document_name, 
#                             document_timestamp, 
#                             document_markdown,
#                             NULL as document_job_id_reference,
#                             NULL as document_job_type
#                         FROM document_store;
#                     """)
                    
#                     # Verify data was copied correctly
#                     async with db.execute("SELECT COUNT(*) FROM document_store_new") as cursor:
#                         row = await cursor.fetchone()
#                         new_row_count = row[0] if row else 0
                    
#                     if new_row_count != row_count:
#                         raise Exception(f"Data copy failed: expected {row_count} rows, got {new_row_count}")
#                     logger.info(f"Successfully copied {new_row_count} rows to new table")
                
#                 # Step 4: Drop old table and rename new table
#                 logger.info("Replacing old table with new table...")
#                 await db.execute("DROP TABLE document_store;")
#                 await db.execute("ALTER TABLE document_store_new RENAME TO document_store;")
                
#                 # Step 5: Re-enable foreign keys and check constraints
#                 await db.execute("PRAGMA foreign_keys = ON;")
                
#                 # Step 6: Verify foreign key constraints are working
#                 logger.info("Testing foreign key constraint...")
#                 try:
#                     # Try to insert a document with invalid job_id to test FK constraint
#                     await db.execute("""
#                         INSERT INTO document_store (
#                             document_id, document_name, document_timestamp, 
#                             document_job_id_reference
#                         ) VALUES ('test_fk', 'test', 1234567890, 'invalid_job_id');
#                     """)
#                     # If we get here, the FK constraint is not working
#                     await db.execute("DELETE FROM document_store WHERE document_id = 'test_fk';")
#                     raise Exception("Foreign key constraint is not working - invalid reference was allowed")
#                 except aiosqlite.IntegrityError as e:
#                     # This is expected - the FK constraint is working
#                     if "FOREIGN KEY constraint failed" in str(e):
#                         logger.info("Foreign key constraint is working correctly")
#                     else:
#                         raise Exception(f"Unexpected integrity error: {e}")
                
#                 # Step 7: Verify the migration
#                 logger.info("Verifying migration...")
#                 async with db.execute("PRAGMA table_info(document_store)") as cursor:
#                     columns = await cursor.fetchall()
#                     column_names = [col[1] for col in columns]
                    
#                     if "document_job_id_reference" not in column_names:
#                         raise Exception("Migration failed: document_job_id_reference column not found")
#                     if "document_job_type" not in column_names:
#                         raise Exception("Migration failed: document_job_type column not found")
                
#                 # Step 8: Check that foreign key is defined in schema
#                 async with db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='document_store'") as cursor:
#                     result = await cursor.fetchone()
#                     if result:
#                         table_sql = result[0]
#                         if "FOREIGN KEY" not in table_sql or "job_details" not in table_sql:
#                             raise Exception("Migration failed: foreign key constraint not found in table definition")
#                         logger.info("Foreign key constraint found in table definition")
                
#                 # Final row count check
#                 async with db.execute("SELECT COUNT(*) FROM document_store") as cursor:
#                     row = await cursor.fetchone()
#                     final_row_count = row[0] if row else 0
                
#                 if final_row_count != row_count:
#                     raise Exception(f"Migration verification failed: expected {row_count} rows, got {final_row_count}")
                
#                 # Commit the transaction
#                 await db.execute("COMMIT;")
#                 logger.info("Migration transaction committed successfully")
                
#                 # Display final schema
#                 logger.info("Final document_store schema:")
#                 async with db.execute("PRAGMA table_info(document_store)") as cursor:
#                     columns = await cursor.fetchall()
#                     for col in columns:
#                         logger.info(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'}")
                
#                 # Show the table creation SQL
#                 async with db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='document_store'") as cursor:
#                     result = await cursor.fetchone()
#                     if result:
#                         logger.info(f"Table definition: {result[0]}")
                
#                 logger.info("Migration completed successfully!")
#                 logger.info(f"Backup available at: {backup_file}")
                
#             except Exception as e:
#                 # Rollback transaction on error
#                 await db.execute("ROLLBACK;")
#                 raise e
            
#     except Exception as e:
#         logger.error(f"Migration failed: {e}")
#         logger.info(f"Database backup available for restoration: {backup_file}")
#         raise

# async def verify_migration():
#     """Verify that the migration was successful."""
#     async with aiosqlite.connect(DB_FILE, timeout=5) as db:
#         await db.execute("PRAGMA foreign_keys = ON;")
        
#         # Check table structure
#         async with db.execute("PRAGMA table_info(document_store)") as cursor:
#             columns = await cursor.fetchall()
#             column_names = [col[1] for col in columns]
            
#             required_columns = [
#                 "document_id",
#                 "document_name", 
#                 "document_timestamp",
#                 "document_markdown",
#                 "document_job_id_reference",
#                 "document_job_type"
#             ]
            
#             for col in required_columns:
#                 if col not in column_names:
#                     logger.error(f"Missing column: {col}")
#                     return False
        
#         # Check that foreign key is defined in the table schema
#         async with db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='document_store'") as cursor:
#             result = await cursor.fetchone()
#             if result:
#                 table_sql = result[0]
#                 if "FOREIGN KEY" not in table_sql or "job_details" not in table_sql:
#                     logger.error("Foreign key constraint not found in table definition")
#                     return False
#                 logger.info("Foreign key constraint found in table definition")
#             else:
#                 logger.error("Could not find table definition")
#                 return False
        
#         # Test foreign key constraint functionality
#         try:
#             # Try to insert a document with invalid job_id to test FK constraint
#             await db.execute("""
#                 INSERT INTO document_store (
#                     document_id, document_name, document_timestamp, 
#                     document_job_id_reference
#                 ) VALUES ('test_fk_verify', 'test', 1234567890, 'invalid_job_id_verify');
#             """)
#             # Clean up the test record if it was inserted (shouldn't happen)
#             await db.execute("DELETE FROM document_store WHERE document_id = 'test_fk_verify';")
#             await db.commit()
#             logger.error("Foreign key constraint is not working - invalid reference was allowed")
#             return False
#         except aiosqlite.IntegrityError as e:
#             # This is expected - the FK constraint is working
#             if "FOREIGN KEY constraint failed" in str(e):
#                 logger.info("Foreign key constraint is working correctly")
#             else:
#                 logger.error(f"Unexpected integrity error: {e}")
#                 return False
        
#         logger.info("Migration verification passed!")
#         return True

# def main():
#     """Main function to run the migration."""
#     print("Document Store Migration Script")
#     print("=" * 50)
#     print("This script will add the following columns to document_store:")
#     print("  - document_job_id_reference (TEXT)")
#     print("  - document_job_type (TEXT)")
#     print("  - FOREIGN KEY constraint on document_job_id_reference")
#     print()
    
#     if not os.path.exists(DB_FILE):
#         print(f"Error: Database file {DB_FILE} not found!")
#         return 1
    
#     response = input("Do you want to proceed? (y/N): ").strip().lower()
#     if response != 'y':
#         print("Migration cancelled.")
#         return 0
    
#     try:
#         asyncio.run(migrate_document_store())
#         print("\n" + "=" * 50)
#         print("Migration completed successfully!")
#         print("You can now use the new columns in your document_store table.")
        
#         # Run verification
#         print("\nRunning verification...")
#         if asyncio.run(verify_migration()):
#             print("✅ Migration verified successfully!")
#         else:
#             print("❌ Migration verification failed!")
#             return 1
            
#     except Exception as e:
#         print(f"\n❌ Migration failed: {e}")
#         return 1
    
#     return 0

# if __name__ == "__main__":
#     exit(main())