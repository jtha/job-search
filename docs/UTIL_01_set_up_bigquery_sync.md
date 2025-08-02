# BigQuery Sync Documentation

This document provides comprehensive documentation for syncing SQLite data to BigQuery using the `db_sync.py` module. This is only relevant if you're using the BigQuery APIs to sync local SQLite data to Google Cloud BigQuery for analytics, reporting, or data warehousing purposes.

## Overview

The BigQuery sync system provides a robust, automated way to synchronize data from a local SQLite database to Google Cloud BigQuery. It uses a hybrid approach combining Protocol Buffers (protobuf) for data serialization and BigQuery's Storage Write API for efficient bulk data transfer.

### Key Features

- **Efficient Bulk Transfer**: Uses BigQuery Storage Write API for high-performance data streaming
- **Schema Compatibility**: Hybrid schema generation ensures compatibility between SQLite and BigQuery
- **UPSERT Operations**: Performs MERGE operations to handle both inserts and updates
- **Type Safety**: Uses Protocol Buffers for type-safe data serialization
- **Automatic Cleanup**: Creates temporary staging tables that auto-expire
- **Error Handling**: Comprehensive logging and error recovery

### Architecture

The sync process works as follows:

1. **Data Extraction**: Reads data from SQLite using SQLAlchemy
2. **Type Conversion**: Converts SQLite data types to protobuf-compatible formats
3. **Serialization**: Serializes data using Protocol Buffers
4. **Staging**: Creates temporary BigQuery staging tables
5. **Streaming**: Uses BigQuery Storage Write API to stream data in batches
6. **Merging**: Performs MERGE operations to upsert data into target tables
7. **Cleanup**: Removes temporary staging tables

## Prerequisites

### 1. Google Cloud Setup

1. **Google Cloud Project**: Ensure you have a Google Cloud project with BigQuery enabled
2. **Service Account**: Create a service account with the following permissions:
   - BigQuery Data Editor
   - BigQuery Job User
   - BigQuery User
3. **Authentication**: Set up authentication using one of:
   - Service account key file (set `GOOGLE_APPLICATION_CREDENTIALS` environment variable)
   - Application Default Credentials (ADC)
   - Workload Identity (for GKE)

### 2. Environment Configuration

Create a `.env` file in the project root with the following variables:

```bash
BIGQUERY_PROJECT_ID=your-gcp-project-id
BIGQUERY_DATASET_ID=your-dataset-name
DB_FILE=backend/job_tracker.db  # Path to your SQLite database
```

### 3. Python Dependencies

The following packages are required (already included in `pyproject.toml`):

```python
google-cloud-bigquery>=3.35.1
google-cloud-bigquery-storage>=2.32.0
pandas>=2.3.1
sqlalchemy>=2.0.42
```

### 4. Protocol Buffers Setup

Install protobuf compiler:

```bash
sudo apt update
sudo apt install protobuf-compiler
```

## Table Schema Management

### Current Synced Tables

The system currently syncs the following tables:

1. **job_runs** - Job crawler execution records
2. **job_details** - Master list of discovered jobs
3. **document_store** - Raw documents (resumes, cover letters)
4. **run_findings** - Many-to-many linking table for job runs and jobs
5. **llm_models** - LLM model configurations and costs
6. **job_quarantine** - Jobs to skip during processing
7. **job_skills** - Job skills and qualification results
8. **prompt** - LLM prompt configurations
9. **llm_runs_v2** - LLM execution runs with metrics

### Schema Definition Files

Each table has corresponding schema files:

- **SQLite Schema**: `backend/sql/XX_create_tablename.sql`
- **Protobuf Schema**: `backend/db_schemas.proto`
- **Generated Python**: `backend/db_schemas_pb2.py` (auto-generated)

## How the Sync Process Works

### 1. Schema Generation (`proto_schema_to_bq_schema`)

The system uses a hybrid approach for schema generation:

- **Data Types**: Determined from protobuf message definitions with special handling for timestamps
- **Nullability**: Inherited from existing BigQuery table schema to maintain compatibility
- **Type Mapping**:
  - `CPPTYPE_INT32/INT64` → `INT64`
  - `CPPTYPE_DOUBLE/FLOAT` → `FLOAT64`
  - `CPPTYPE_BOOL` → `BOOLEAN`
  - `CPPTYPE_STRING` → `STRING`
  - Fields ending with `_timestamp`, `_at`, `_start`, `_end` → `TIMESTAMP`

### 2. Data Extraction and Conversion

```python
# SQLite data is extracted using carefully crafted SQL queries
select_clauses = []
for field_name, field_descriptor in fields_map.items():
    if field_descriptor.cpp_type in [NUMERIC_TYPES]:
        # Handle NULL values by converting to 0 for numeric fields
        select_clauses.append(f"COALESCE({field_name}, 0) AS {field_name}")
    else:
        select_clauses.append(field_name)
```

### 3. Batch Processing (`sync_sqlite_to_bigquery_storage`)

Data is processed in configurable batches (default: 500 rows) to:
- Stay under API request size limits
- Provide progress feedback
- Enable recovery from partial failures

### 4. MERGE Operations (`sync_and_merge_sqlite_to_bigquery`)

The system performs UPSERT operations using BigQuery MERGE statements:

```sql
MERGE target_table T
USING staging_table S
ON T.primary_key = S.primary_key
WHEN MATCHED THEN
  UPDATE SET [all_columns]
WHEN NOT MATCHED BY TARGET THEN
  INSERT [all_columns]
```

## Usage

### Running the Sync

To sync all tables:

```bash
cd backend
python db_sync.py
```

The sync will process all configured tables sequentially and provide detailed logging output.

### Adding New Tables

To add a new table to the sync process:

1. **Create SQLite schema**: Add `XX_create_newtable.sql` in `backend/sql/`
2. **Update protobuf schema**: Add message definition to `backend/db_schemas.proto`
3. **Regenerate protobuf**: Run `protoc --python_out=. db_schemas.proto`
4. **Update sync code**: Add sync call in `main()` function of `db_sync.py`

Example addition to `main()`:

```python
# Sync new_table
sync_and_merge_sqlite_to_bigquery(
    PROJECT_ID, DATASET_ID, "new_table",
    sqlite_db_path, "new_table", ["primary_key_column"], NewTableMessage,
)
```

### Modifying Existing Schemas

When updating table schemas:

1. **Update SQLite schema**: Modify the corresponding SQL file in `backend/sql/`
2. **Update protobuf schema**: Modify the message definition in `backend/db_schemas.proto`
3. **Regenerate protobuf**: Run `protoc --python_out=. db_schemas.proto`
4. **Test sync**: Run the sync to ensure compatibility

## Monitoring and Troubleshooting

### Logging

The system provides comprehensive logging at multiple levels:

- **INFO**: Normal operation progress and batch processing
- **WARNING**: Non-fatal issues like missing optional fields
- **ERROR**: Sync failures and critical issues
- **DEBUG**: Detailed schema generation and data conversion info

### Common Issues

1. **Authentication Errors**:
   - Verify Google Cloud credentials are properly configured
   - Check service account permissions

2. **Schema Mismatches**:
   - Ensure protobuf schema matches SQLite schema
   - Check for data type compatibility issues

3. **API Quota Limits**:
   - Reduce batch size if hitting rate limits
   - Implement exponential backoff for retries

4. **Data Type Conversion Errors**:
   - Check for NULL values in required fields
   - Verify timestamp field formatting

### Performance Optimization

- **Batch Size**: Adjust batch size based on row size and API limits
- **Parallel Processing**: Consider parallel table syncing for large datasets
- **Incremental Sync**: Implement timestamp-based incremental syncing for large tables

## Security Considerations

- Store service account keys securely
- Use least-privilege IAM roles
- Enable BigQuery audit logging
- Consider data encryption at rest and in transit
- Implement proper access controls on BigQuery datasets
