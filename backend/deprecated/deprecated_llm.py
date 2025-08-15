# async def generate_job_assessment(limit:int=100, days_back:int=14, semaphore_count:int=5):

#     resume_json = await get_document_master_resume_json()
#     resume = await get_document_master_resume()

#     if resume_json["document_markdown"] is None:
#         logger.error("Master resume not found.")
#         return {"error": "Master resume not found"}

#     if resume["document_markdown"] is None:
#         logger.error("Master resume not found.")
#         return {"error": "Master resume not found"}

#     prompt_configuration_2_1 = await get_latest_prompt("ja_2_1_assessment")
#     if prompt_configuration_2_1 is None:
#         logger.error("Prompt configuration for job description tagging not found.")
#         return {"error": "Prompt configuration for job description tagging not found"}
#     prompt_configuration_2_2 = await get_latest_prompt("ja_2_2_assessment")
#     if prompt_configuration_2_2 is None:
#         logger.error("Prompt configuration for job description atomizing not found.")
#         return {"error": "Prompt configuration for job description atomizing not found"}
#     prompt_configuration_2_3 = await get_latest_prompt("ja_2_3_assessment")
#     if prompt_configuration_2_3 is None:
#         logger.error("Prompt configuration for job description final processing not found.")
#         return {"error": "Prompt configuration for job description final processing not found"}
#     prompt_configuration_3_1 = await get_latest_prompt("ja_3_1_assessment")
#     if prompt_configuration_3_1 is None:
#         logger.error("Prompt configuration for job assessment not found.")
#         return {"error": "Prompt configuration for job assessment not found"}

#     job_details = await get_job_details_without_assessment(limit=limit, days_back=days_back)
#     if not job_details:
#         # logger.info(f"No job details found without assessment for the last {days_back}")
#         return {"total_processed": 0, "successful": 0, "failed": 0, "exceptions": 0, "message": "No jobs found without assessment"}
    
#     # logger.info(f"Found {len(job_details)} job details without assessment for the last {days_back} days.")

#     # Create semaphore for controlling concurrency
#     semaphore = asyncio.Semaphore(semaphore_count)
    
#     # Create tasks for concurrent processing
#     tasks = [
#         process_single_job_assessment(
#             job=job,
#             resume=resume,
#             resume_json=resume_json,
#             prompt_configuration_2_1=prompt_configuration_2_1,
#             prompt_configuration_2_2=prompt_configuration_2_2,
#             prompt_configuration_2_3=prompt_configuration_2_3,
#             prompt_configuration_3_1=prompt_configuration_3_1,
#             semaphore=semaphore
#         )
#         for job in job_details
#     ]
    
#     # Execute all tasks concurrently with semaphore control
#     # logger.info(f"Starting concurrent job assessment processing with {semaphore_count} concurrent tasks")
#     results = await asyncio.gather(*tasks, return_exceptions=True)
    
#     # Count successful vs failed jobs for logging
#     successful_count = sum(1 for result in results if isinstance(result, bool) and result)
#     failed_count = sum(1 for result in results if isinstance(result, bool) and not result)
#     exception_count = sum(1 for result in results if isinstance(result, Exception))
    
#     # logger.info(f"Completed processing {len(job_details)} jobs: {successful_count} succeeded, {failed_count} failed, {exception_count} had exceptions")
    
#     # Return summary of results
#     return {
#         "total_processed": len(job_details),
#         "successful": successful_count,
#         "failed": failed_count,
#         "exceptions": exception_count
#     }

# async def generate_failed_job_assessment(limit:int=100, days_back:int=14, semaphore_count:int=5):
#     """
#     Generates job assessments for quarantined jobs that failed previously.
#     Uses the same logic as generate_job_assessment but filters for quarantined jobs.
#     """
#     resume_json = await get_document_master_resume_json()
#     resume = await get_document_master_resume()

#     if resume_json["document_markdown"] is None:
#         logger.error("Master resume not found.")
#         return {"error": "Master resume not found"}

#     if resume["document_markdown"] is None:
#         logger.error("Master resume not found.")
#         return {"error": "Master resume not found"}

#     prompt_configuration_2_1 = await get_latest_prompt("ja_2_1_assessment")
#     if prompt_configuration_2_1 is None:
#         logger.error("Prompt configuration for job description tagging not found.")
#         return {"error": "Prompt configuration for job description tagging not found"}
#     prompt_configuration_2_2 = await get_latest_prompt("ja_2_2_assessment")
#     if prompt_configuration_2_2 is None:
#         logger.error("Prompt configuration for job description atomizing not found.")
#         return {"error": "Prompt configuration for job description atomizing not found"}
#     prompt_configuration_2_3 = await get_latest_prompt("ja_2_3_assessment")
#     if prompt_configuration_2_3 is None:
#         logger.error("Prompt configuration for job description final processing not found.")
#         return {"error": "Prompt configuration for job description final processing not found"}
#     prompt_configuration_3_1 = await get_latest_prompt("ja_3_1_assessment")
#     if prompt_configuration_3_1 is None:
#         logger.error("Prompt configuration for job assessment not found.")
#         return {"error": "Prompt configuration for job assessment not found"}

#     job_details = await get_quarantined_job_details_for_assessment(limit=limit, days_back=days_back)
#     if not job_details:
#         # logger.info(f"No quarantined job details found for assessment for the last {days_back} days")
#         return {"total_processed": 0, "successful": 0, "failed": 0, "exceptions": 0, "quarantine_removed": 0, "message": "No quarantined jobs found for assessment"}
    
#     # logger.info(f"Found {len(job_details)} quarantined job details for assessment for the last {days_back} days.")

#     # Create semaphore for controlling concurrency
#     semaphore = asyncio.Semaphore(semaphore_count)
    
#     # Create tasks for concurrent processing with job info
#     job_assessment_tasks = [
#         (job, process_single_job_assessment(
#             job=job,
#             resume=resume,
#             resume_json=resume_json,
#             prompt_configuration_2_1=prompt_configuration_2_1,
#             prompt_configuration_2_2=prompt_configuration_2_2,
#             prompt_configuration_2_3=prompt_configuration_2_3,
#             prompt_configuration_3_1=prompt_configuration_3_1,
#             semaphore=semaphore
#         ))
#         for job in job_details
#     ]
    
#     # Execute all tasks concurrently with semaphore control
#     # logger.info(f"Starting concurrent failed job assessment processing with {semaphore_count} concurrent tasks")
#     results = await asyncio.gather(*[task for _, task in job_assessment_tasks], return_exceptions=True)
    
#     # Process results and delete quarantine records for successful jobs
#     successful_jobs = []
#     failed_count = 0
#     exception_count = 0
    
#     for i, (job, result) in enumerate(zip([job for job, _ in job_assessment_tasks], results)):
#         if isinstance(result, bool) and result:  # Success
#             successful_jobs.append(job['job_id'])
#             await delete_job_quarantine(job['job_id'])
#         elif isinstance(result, bool) and not result:  # Failed
#             failed_count += 1
#         elif isinstance(result, Exception):
#             logger.exception(f"Task failed with exception for job {job['job_id']}: {result}")
#             exception_count += 1
    
#     if successful_jobs:
#         logger.info(f"Successfully processed and removed quarantine for {len(successful_jobs)} jobs: {successful_jobs}")
    
#     # logger.info(f"Completed processing {len(job_details)} quarantined jobs, {len(successful_jobs)} succeeded")
    
#     # Return summary of results
#     return {
#         "total_processed": len(job_details),
#         "successful": len(successful_jobs),
#         "failed": failed_count,
#         "exceptions": exception_count,
#         "quarantine_removed": len(successful_jobs)
#     }