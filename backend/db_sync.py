import time
from google.cloud import bigquery
from google.cloud.bigquery_storage_v1 import BigQueryWriteClient, types
from google.protobuf import descriptor_pool
from google.protobuf.descriptor import FieldDescriptor
import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

from utilities import setup_logging, get_logger
from db_schemas_pb2 import (
    JobRuns, # type: ignore
    JobDetails, # type: ignore
    DocumentStore, # type: ignore
    RunFindings, # type: ignore
    LlmModels, # type: ignore
    JobQuarantine, # type: ignore
    JobSkills, # type: ignore
    Prompt, # type: ignore
    LlmRunsV2 # type: ignore
)

load_dotenv()
setup_logging()
logger = get_logger(__name__)

PROJECT_ID = os.getenv("BIGQUERY_PROJECT_ID")
DATASET_ID = os.getenv("BIGQUERY_DATASET_ID")
DB_FILE = os.getenv("DB_FILE", "job_tracker.db")

def proto_schema_to_bq_schema(
    proto_message: type,
    target_table_schema: list[bigquery.SchemaField]
) -> list[bigquery.SchemaField]:
    """
    Generates a BQ schema using a hybrid approach:
    - Data types are determined by the proto message and our naming conventions.
    - Nullability (mode) is determined by the existing target table's schema.
    """
    # Create a lookup map for the target schema's mode (REQUIRED/NULLABLE)
    target_schema_map = {field.name: field.mode for field in target_table_schema}

    type_mapping = {
        FieldDescriptor.CPPTYPE_INT32: "INT64",
        FieldDescriptor.CPPTYPE_INT64: "INT64",
        FieldDescriptor.CPPTYPE_DOUBLE: "FLOAT64",
        FieldDescriptor.CPPTYPE_FLOAT: "FLOAT64",
        FieldDescriptor.CPPTYPE_BOOL: "BOOLEAN",
        FieldDescriptor.CPPTYPE_STRING: "STRING",
    }
    bq_schema = []
    logger.info(f"--- Generating BQ Schema for {proto_message.DESCRIPTOR.name} ---")
    for field in proto_message.DESCRIPTOR.fields:
        field_name = field.name
        field_type = type_mapping.get(field.cpp_type, "STRING")
        is_timestamp_by_name = field_name.endswith(('_timestamp', '_at', '_start', '_end'))
        is_numeric_in_proto = field.cpp_type in [FieldDescriptor.CPPTYPE_INT32, FieldDescriptor.CPPTYPE_INT64, FieldDescriptor.CPPTYPE_DOUBLE, FieldDescriptor.CPPTYPE_FLOAT]
        if is_timestamp_by_name and is_numeric_in_proto:
            field_type = "TIMESTAMP"
        field_mode = target_schema_map.get(field_name, "NULLABLE")
        bq_schema.append(bigquery.SchemaField(field_name, field_type, field_mode))

    logger.info(f"Final Generated BQ Schema: {[f'{f.name}:{f.field_type}({f.mode})' for f in bq_schema]}")
    return bq_schema

def sync_sqlite_to_bigquery_storage(
    project_id: str,
    dataset_id: str,
    table_id: str,
    sqlite_db_path: str,
    sqlite_table_name: str,
    proto_message: type,
):
    """
    (Helper Function) Syncs data by batching rows to stay under API request size limits.
    
    This corrected version handles NULL values from SQLite by providing safe defaults,
    preventing the BigQuery Write API from silently rejecting rows with missing REQUIRED fields.
    """
    write_client = BigQueryWriteClient()
    parent = write_client.table_path(project_id, dataset_id, table_id)
    write_stream = types.WriteStream(type_=types.WriteStream.Type.COMMITTED)
    write_stream = write_client.create_write_stream(parent=parent, write_stream=write_stream)
    stream_name = write_stream.name

    engine = create_engine(f"sqlite:///{sqlite_db_path}")
    fields_map = {field.name: field for field in proto_message.DESCRIPTOR.fields}

    # The COALESCE in the SQL query handles NULLs for numeric types at the source.
    select_clauses = []
    for field_name, field_descriptor in fields_map.items():
        if field_descriptor.cpp_type in [FieldDescriptor.CPPTYPE_INT32, FieldDescriptor.CPPTYPE_INT64, FieldDescriptor.CPPTYPE_DOUBLE, FieldDescriptor.CPPTYPE_FLOAT]:
            select_clauses.append(f"COALESCE({field_name}, 0) AS {field_name}")
        else:
            select_clauses.append(field_name)

    sql_query = f"SELECT {', '.join(select_clauses)} FROM {sqlite_table_name};"
    df = pd.read_sql_query(sql_query, engine)

    if df.empty:
        logger.info(f"No data to sync from SQLite table: {sqlite_table_name}.")
        write_client.finalize_write_stream(name=stream_name)
        return

    batch_size = 500
    total_rows = len(df)
    
    pool = descriptor_pool.Default()
    file_descriptor = pool.FindFileByName(proto_message.DESCRIPTOR.file.name)
    message_descriptor = file_descriptor.message_types_by_name[proto_message.DESCRIPTOR.name]
    proto_schema = types.ProtoSchema()
    message_descriptor.CopyToProto(proto_schema.proto_descriptor)

    try:
        for i in range(0, total_rows, batch_size):
            batch_df = df[i:i + batch_size]
            
            logger.info(f"Processing batch {i // batch_size + 1}: rows {i} to {i + len(batch_df) - 1}")

            proto_rows = types.ProtoRows()
            for _, row in batch_df.iterrows():
                proto_message_instance = proto_message()
                for col, value in row.items():
                    field_descriptor = fields_map.get(str(col))
                    if not field_descriptor:
                        continue

                    cpp_type = field_descriptor.cpp_type
                    converted_value = value

                    if pd.isna(converted_value):
                        if cpp_type == FieldDescriptor.CPPTYPE_STRING:
                            converted_value = ""
                        elif cpp_type in [FieldDescriptor.CPPTYPE_INT64, FieldDescriptor.CPPTYPE_INT32, FieldDescriptor.CPPTYPE_DOUBLE, FieldDescriptor.CPPTYPE_FLOAT]:
                            converted_value = 0
                        elif cpp_type == FieldDescriptor.CPPTYPE_BOOL:
                            converted_value = False
                        else:
                            continue

                    # Now, perform the final type conversion on the (potentially defaulted) value.
                    if cpp_type == FieldDescriptor.CPPTYPE_STRING:
                        converted_value = str(converted_value)
                    elif cpp_type in [FieldDescriptor.CPPTYPE_INT64, FieldDescriptor.CPPTYPE_INT32]:
                        converted_value = int(converted_value)
                    elif cpp_type == FieldDescriptor.CPPTYPE_BOOL:
                        converted_value = bool(converted_value)
                    elif cpp_type in [FieldDescriptor.CPPTYPE_DOUBLE, FieldDescriptor.CPPTYPE_FLOAT]:
                        converted_value = float(converted_value)

                    setattr(proto_message_instance, str(col), converted_value)
                
                proto_rows.serialized_rows.append(proto_message_instance.SerializeToString())
            
            # Create a request for the current batch.
            if proto_rows.serialized_rows:
                proto_data = types.AppendRowsRequest.ProtoData()
                proto_data.writer_schema = proto_schema
                proto_data.rows = proto_rows
                request = types.AppendRowsRequest(write_stream=stream_name, proto_rows=proto_data)
                
                # Append the current batch.
                write_client.append_rows(iter([request]))

        logger.info(f"INFO: Successfully sent {total_rows} rows in { (total_rows + batch_size - 1) // batch_size } batches to be streamed to staging table: {table_id}")

    except Exception as e:
        logger.exception(f"ERROR: Error appending rows during batch processing: {e}")
        raise
    finally:
        write_client.finalize_write_stream(name=stream_name)

def sync_and_merge_sqlite_to_bigquery(
    project_id: str,
    dataset_id: str,
    target_table_id: str,
    sqlite_db_path: str,
    sqlite_table_name: str,
    primary_key_columns: list[str],
    proto_message: type,
):
    """
    Orchestrates a full sync using a hybrid schema generation approach for
    maximum compatibility and robustness.
    """
    bq_client = bigquery.Client(project=project_id)
    staging_table_id = f"{target_table_id}_staging_{int(time.time())}"
    staging_table_ref = bigquery.TableReference.from_string(
        f"{project_id}.{dataset_id}.{staging_table_id}"
    )

    try:
        logger.info(f"Fetching schema from target table: {target_table_id}")
        target_table_obj = bq_client.get_table(f"{project_id}.{dataset_id}.{target_table_id}")
        staging_schema = proto_schema_to_bq_schema(proto_message, target_table_obj.schema)
        staging_table = bigquery.Table(staging_table_ref, schema=staging_schema)
        staging_table.expires = pd.Timestamp.now(tz="UTC") + pd.Timedelta(hours=1)
        logger.info(f"Creating temporary staging table: {staging_table_id}...")
        bq_client.create_table(staging_table, exists_ok=False)
        logger.info("Staging table created.")

        sync_sqlite_to_bigquery_storage(
            project_id, dataset_id, staging_table_id,
            sqlite_db_path, sqlite_table_name, proto_message,
        )

        logger.info(f"Running MERGE from {staging_table_id} to {target_table_id}...")
        on_clause = " AND ".join([f"CAST(T.{col} AS STRING) = CAST(S.{col} AS STRING)" for col in primary_key_columns])
        all_columns = [field.name for field in proto_message.DESCRIPTOR.fields]
        update_clause = ", ".join([f"T.{col} = S.{col}" for col in all_columns])
        insert_columns = ", ".join(all_columns)
        source_columns = ", ".join([f"S.{col}" for col in all_columns])

        merge_sql = f"""
        MERGE `{project_id}.{dataset_id}.{target_table_id}` T
        USING `{staging_table_ref}` S
        ON {on_clause}
        WHEN MATCHED THEN
          UPDATE SET {update_clause}
        WHEN NOT MATCHED BY TARGET THEN
          INSERT ({insert_columns}) VALUES ({source_columns})
        """

        merge_job = bq_client.query(merge_sql)
        merge_job.result()

        logger.info(f"MERGE completed successfully. "
                     f"{merge_job.num_dml_affected_rows} rows affected in {target_table_id}.")

    finally:
        logger.info(f"Cleaning up: Deleting staging table {staging_table_id}...")
        bq_client.delete_table(staging_table_ref, not_found_ok=True)
        logger.info("Cleanup complete. Synchronization finished.")

def main():
    if not PROJECT_ID or not DATASET_ID:
        logger.error("Environment variables BIGQUERY_PROJECT_ID and BIGQUERY_DATASET_ID must be set.")
        return
    
    logger.info(f"Project ID: {PROJECT_ID}, Dataset ID: {DATASET_ID}")
    logger.info(f"Using SQLite DB file: {DB_FILE}")


    sqlite_db_path = DB_FILE

    # Sync job_runs
    sync_and_merge_sqlite_to_bigquery(
        PROJECT_ID, DATASET_ID, "job_runs",
        sqlite_db_path, "job_runs", ["job_run_id"], JobRuns,
    )

    # Sync job_details
    sync_and_merge_sqlite_to_bigquery(
        PROJECT_ID, DATASET_ID, "job_details",
        sqlite_db_path, "job_details", ["job_id"], JobDetails,
    )

    # Sync document_store
    sync_and_merge_sqlite_to_bigquery(
        PROJECT_ID, DATASET_ID, "document_store",
        sqlite_db_path, "document_store", ["document_id"], DocumentStore,
    )

    # Sync run_findings (composite primary key)
    sync_and_merge_sqlite_to_bigquery(
        PROJECT_ID, DATASET_ID, "run_findings",
        sqlite_db_path, "run_findings", ["job_run_id", "job_id"], RunFindings,
    )

    # Sync llm_models
    sync_and_merge_sqlite_to_bigquery(
        PROJECT_ID, DATASET_ID, "llm_models",
        sqlite_db_path, "llm_models", ["model_id"], LlmModels,
    )

    # Sync job_quarantine
    sync_and_merge_sqlite_to_bigquery(
        PROJECT_ID, DATASET_ID, "job_quarantine",
        sqlite_db_path, "job_quarantine", ["job_quarantine_id"], JobQuarantine,
    )

    # Sync job_skills
    sync_and_merge_sqlite_to_bigquery(
        PROJECT_ID, DATASET_ID, "job_skills",
        sqlite_db_path, "job_skills", ["job_skill_id"], JobSkills,
    )

    # Sync prompt
    sync_and_merge_sqlite_to_bigquery(
        PROJECT_ID, DATASET_ID, "prompt",
        sqlite_db_path, "prompt", ["prompt_id"], Prompt,
    )

    # Sync llm_runs_v2
    sync_and_merge_sqlite_to_bigquery(
        PROJECT_ID, DATASET_ID, "llm_runs_v2",
        sqlite_db_path, "llm_runs_v2", ["llm_run_id"], LlmRunsV2,
    )

if __name__ == "__main__":
    main()