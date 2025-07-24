# Lead Qualification System

## Overview
For the first version of the lead qualification system, We will not reinvent the wheel. We will take advantage of existing services to help us qualify leads, extract the logical rules, and implement them in our own system using LLMs. *(Redacted)* provides a decent AI-powered lead qualification system, so we will use that as a starting point.

## Methodology
We collected a total of 100 samples of job assessments (30 low match, 40 medium match and 30 high match) and used Gemini 2.5 Pro to deconstruct the logic for generating a job assessment. This model was used because it is a very strong reasoning model with long context capabilities. All 100 samples (including full text of job description and text of job assessment) amounted to ~150k tokens of input.

System Prompt:   
```Given the user's resume and 100 samples of job descriptions and job role assessment, thoroughly deconstruct the exact logic required to reproduce an assessment given a job description and a user resume```

Parameters:  
Temperature = 0.2  
Thinking mode enabled

After reviewing the logic, we created a system prompt to follow the precise logic and give a structured output including some details/components that make up the job assessment (e.g. list of skills required, list of skills matched) that may come in handy later.

## Logic for Job Assessment Generation

The process can be broken down into five distinct phases:

1.  **Deconstruction & Extraction:** Parsing the raw text of the resume and job description into structured data.
2.  **Resume Analysis & Fact Base Creation:** Analyzing the parsed resume data to create a comprehensive, searchable "fact base" about the candidate.
3.  **Job Description Qualification Analysis:** Analyzing the parsed job description to identify and categorize all qualifications.
4.  **Core Matching & Evaluation Logic:** Systematically comparing each qualification against the candidate's fact base to determine a match status.
5.  **Aggregation & Assessment Generation:** Compiling the results into the final, structured assessment report.

---

### Phase 1: Deconstruction & Extraction

This is the initial data processing step.

**1.1. Resume Parsing:**
The system reads the resume and extracts key information into a structured format.

*   **Contact:** Email, LinkedIn URL.
*   **Top Skills:** A list of explicitly stated skills (e.g., `["Data Visualization", "SQL", "Supply Chain Analytics"]`).
*   **Languages:** A list of languages and proficiency (e.g., `[{"Language": "English", "Proficiency": "Native or Bilingual"}, {"Language": "Indonesian", "Proficiency": "Native or Bilingual"}]`).
*   **Certifications:** A list of certifications (e.g., `["Mastering LLMs For Developers & Data Scientists"]`).
*   **Headline/Summary:** Keywords are extracted (e.g., `["Business Intelligence", "Analytics", "Supply Chains", "Demand Planning", "SQL", "BigQuery", "Metabase"]`).
*   **Education:** Degree, Major, University, Graduation Year (e.g., `{"Degree": "Bachelor of Applied Science", "Major": "Mining and Mineral Processing Engineering", "University": "The University of British Columbia", "Year": 2012}`).
*   **Experience:** For each role, extract:
    *   `Job Title`: e.g., "Senior Supply Chain & Analytics Manager"
    *   `Company`: e.g., "GoTo Logistics"
    *   `Start Date`: e.g., "September 2021"
    *   `End Date`: e.g., "July 2024"
    *   `Duration`: Calculated in years and months.
    *   `Responsibilities`: A list of bullet points. Each bullet point is treated as a source of keywords and achievements.

**1.2. Job Description Parsing:**
The system reads the job description and identifies distinct sections and qualifications.

*   **Identify Qualification Sections:** The text is scanned for keywords and headings like "Qualifications," "Required Skills," "Minimum Qualifications," "Must have," "Preferred Skills," "Nice To Have," "Bonus Points."
*   **Extract Individual Qualifications:** Each bullet point or line item under these sections is extracted as a separate qualification to be tested.
*   **Identify "Soft Skills":** Qualifications that are subjective and not easily verifiable from a resume are flagged. These include phrases like "Strong attention to detail," "Ability to adapt quickly," "Excellent communication skills," "Embrace change."

---

### Phase 2: Resume Analysis & Fact Base Creation

This phase transforms the extracted resume data into a searchable knowledge base.

**2.1. Calculate Total Experience:**
*   Sum the durations of all professional roles to get a total "Years of Experience." For Jati Harianto, this is from Feb 2013 to July 2024, which is ~11.5 years.
*   Calculate experience in specific domains by summing roles with relevant titles (e.g., "Analytics," "Business Intelligence," "Supply Chain"). For Jati, analytics-focused experience starts in April 2016, totaling over 8 years.
*   Calculate management experience by identifying roles with "Manager," "Leader," or explicit mentions of team management. For Jati, this is ~3 years at GoTo, plus roles at Berrybenka and Sorabel, totaling over 5 years.

**2.2. Create a Comprehensive Skill & Technology Lexicon:**
*   Combine "Top Skills," skills from the headline, and keywords from all job responsibility bullet points.
*   This creates a rich list of technologies, methodologies, and skills.
    *   **Technologies:** `SQL`, `BigQuery`, `Metabase`, `SAP`.
    *   **BI Tools:** `Metabase`. (Note: The system must recognize this as a BI/Data Visualization tool).
    *   **Methodologies:** `Demand Planning`, `Supply Planning`, `Predictive Inventory Models`, `SQL Query Optimization`, `Data Governance`, `KPI Tracking`, `Forecasting`, `Process Automation`, `Data Migration`, `ETL`, `Data Pipeline`.
    *   **Industries:** `Logistics`, `eCommerce`, `Retail`, `Mining`.

**2.3. Structure Education Data:**
*   The degree and major are stored. The system categorizes the major (e.g., "Mining and Mineral Processing Engineering" is categorized as `Engineering`, `Quantitative`, but not `Computer Science` or `Business Analytics`).

---

### Phase 3: Job Description Qualification Analysis

The system categorizes the extracted qualifications to structure the final report.

*   **Required Qualifications:** Items found under headings like "Required," "Minimum," or "Must have."
*   **Additional/Preferred Qualifications:** Items found under headings like "Preferred," "Nice to have," or "is a plus."
*   **Interview/Soft Skill Qualifications:** Subjective items that were flagged in Phase 1.2 are moved to a separate list for the "likely to be evaluated in the application or interview" section.

---

### Phase 4: Core Matching & Evaluation Logic

This is the most critical phase where each qualification is systematically checked against the candidate's fact base.

**For each qualification, the system performs a series of checks:**

**4.1. Years of Experience Check:**
*   **Logic:** Parses the number and the domain (e.g., "5+ years," "in BI development").
*   **Example:** JD requires "At least 4 years of experience programming in SQL."
    *   The system checks the candidate's fact base for "SQL." It's present.
    *   It calculates the duration of roles where SQL was used (GoTo, Berrybenka, Sorabel, Matahari: Apr 2016 - Jul 2024 = ~8 years).
    *   Since 8 > 4, the result is **Match (✓)**.

**4.2. Specific Skill/Technology Check:**
*   **Logic:** Parses for specific tool names, programming languages, or concepts. It handles "OR" conditions and "e.g." clauses.
*   **Example 1 (Specific Tool):** JD requires "experience developing Tableau dashboards."
    *   The system searches the fact base for "Tableau." It is not found.
    *   Result: **No Match (?)**. Reason: `(No mention of Tableau experience)`.
*   **Example 2 (List of Tools with "e.g."):** JD requires "experience designing business intelligence reports (e.g. Looker, PowerBI, Tableau, Qlik, etc.)."
    *   The system recognizes "e.g." and "etc.", meaning an equivalent tool is acceptable.
    *   It searches the fact base for *any* BI/visualization tool. It finds `Metabase`.
    *   Result: **Match (✓)**.
*   **Example 3 (Compound Skill):** JD requires "Strong understanding of SPARK and SQL."
    *   The system checks for "SPARK" (not found) and "SQL" (found).
    *   Result: **Partial Match (?)**. Reason: `(Partial Match, strong SQL skills but no SPARK)`.

**4.3. Education Check:**
*   **Logic:** Checks for degree level and major.
*   **Example 1 (Degree Level):** JD requires "Bachelor's degree, required."
    *   The system checks the fact base for a Bachelor's degree. It finds one.
    *   Result: **Match (✓)**.
*   **Example 2 (Degree Field):** JD requires "Bachelor's degree in Data Science, Business Analytics, Mathematics, Computer Science, or related field."
    *   The system finds the candidate's major is "Mining and Mineral Processing Engineering."
    *   It checks if this major is in the provided list. It is not.
    *   It then checks if it's a "related field." While quantitative, it's not a standard related field for this role type.
    *   Result: **No Match (?)**. Reason: `(Degree in unrelated field)`.

**4.4. Management Experience Check:**
*   **Logic:** Parses for phrases like "managing a team," "lead experience," and checks the candidate's fact base for managerial roles and explicit mentions of team size.
*   **Example:** JD requires "experience managing a team of at least 5 or more developers."
    *   The system finds the GoTo role: "Promoted to lead a team of 5 analysts."
    *   Result: **Match (✓)**.

---

### Phase 5: Aggregation & Assessment Generation

The final step is to assemble the results into the user-facing assessment.

**5.1. Calculate Match Score:**
*   The system counts the number of matches for "Required" and "Additional" qualifications separately.
*   An overall match score is determined primarily by the percentage of **required** qualifications met.
    *   **High Match:** >=75% of required qualifications met.
    *   **Medium Match:** 50% - 74% (inclusive) of required qualifications met.
    *   **Low Match:** <50% of required qualifications met.

**5.2. Select Template Text:**
*   Based on the High/Medium/Low score, the system selects a predefined introductory paragraph.
    *   **High:** "Your profile seems to match well with this job..."
    *   **Medium:** "Your profile matches several of the required qualifications... you may want to update your profile..."
    *   **Low:** "Your profile is missing some required qualifications... you may want to look at other jobs..."

**5.3. Assemble the Final Report:**
The system constructs the final output in the exact format seen in the samples:
1.  **Overall Rating:** `Job match is [High/Medium/Low]`
2.  **Job Title:** `For [Company] - [Job Title]`
3.  **Introductory Text:** The selected template paragraph.
4.  **Required Qualifications Summary:** `Matches [X] of the [Y] required qualifications:`
5.  **Bulleted List of Required Qualifications:** Each item is prefixed with `✓` or `?`, followed by the qualification text. For mismatches, a parenthetical reason is appended (e.g., `(No mention of Python or R)`).
6.  **Additional Qualifications Summary:** `Matches [X] of the [Y] additional qualifications:`
7.  **Bulleted List of Additional Qualifications:** Formatted the same as the required list.
8.  **Interview Qualifications Section:** `There are qualifications that will likely be evaluated in the application or interview:`
9.  **Bulleted List of Soft Skills:** The list of subjective skills identified in Phase 3.

## System Prompt for LLM to Generate Job Assessment

**You are a highly meticulous and analytical Job Matching AI Agent.** Your primary function is to analyze a user's resume against a specific job posting and generate a detailed job match assessment. You must follow the instructions below with extreme precision and without deviation.

**Inputs:**
1.  `<resume>`: The user's comprehensive resume.
2.  `<job_description>`: The job description for the role being assessed.

---

### **Phase 1: Deconstruction & Extraction**

**1.1. Analyze the Resume:**
Thoroughly parse the `<resume>` and create a structured `CandidateFactBase` in your memory. Extract and calculate the following:
*   **Total Experience:** Calculate the total years of professional experience from the earliest start date to the latest end date.
*   **Domain-Specific Experience:** Calculate the total years of experience for key domains mentioned in the resume (e.g., "Analytics," "Business Intelligence," "Supply Chain," "Management").
*   **Skill & Technology Lexicon:** Create a comprehensive list of all explicit skills, technologies, methodologies, and tools. This includes items from any "Skills" section, the professional summary, and keywords from every job responsibility bullet point (e.g., `SQL`, `BigQuery`, `Metabase`, `SAP`, `Demand Planning`, `Predictive Models`, `Data Governance`, `ETL`, `Data Pipeline`).
*   **Education:** Extract the `Degree Level` (e.g., Bachelor's, Master's) and `Field of Study` (e.g., "Mining and Mineral Processing Engineering"). Categorize the field (e.g., Engineering, Quantitative).
*   **Certifications:** List all formal certifications.

**1.2. Analyze the Job Description:**
Thoroughly parse the `<job_description>` and create three distinct lists of qualifications.
*   `list_required_qualifications`: Extract each individual requirement from sections labeled "Required," "Minimum Qualifications," "Must have," or similar.
*   `list_additional_qualifications`: Extract each individual requirement from sections labeled "Preferred," "Nice to have," "Bonus Points," or similar.
*   `list_evaluated_qualifications`: Identify and extract all subjective "soft skills" or logistical requirements that cannot be verified from a resume (e.g., "Strong attention to detail," "Ability to adapt quickly," "Excellent communication skills," "Must be qualified to work in the United States"). These will be listed separately in the final output.

---

### **Phase 2: Core Matching & Evaluation Logic**

For EACH qualification in `list_required_qualifications` and `list_additional_qualifications`, you must meticulously compare it against the `CandidateFactBase`. Your default stance is conservative; if a match is not explicit and directly supported by evidence, it is NOT a match.

**2.1. Assign a Status and a Reason:**

*   **`✓ Match`:** Assign this status ONLY if there is direct, undeniable evidence in the `CandidateFactBase`.
    *   **Years of Experience:** The JD requires "X+ years of experience in Y," and the candidate's calculated `Domain-Specific Experience` for Y meets or exceeds X.
    *   **Specific Skill/Tool:** The JD requires a specific tool (e.g., "Tableau," "Python"). The EXACT tool (or a direct equivalent like "Power BI" for "Microsoft Power BI") must be in the `Skill & Technology Lexicon`.
    *   **Conceptual Skill:** The JD requires a methodology (e.g., "Data Governance," "ETL"). The EXACT concept must be in the `Skill & Technology Lexicon`.
    *   **"e.g." or "similar" clauses:** If the JD says "experience with BI tools (e.g., Tableau, Power BI)," a match is valid if *any* BI tool from the candidate's lexicon (like `Metabase`) is found.
    *   **Education Level:** The JD requires a "Bachelor's degree," and the candidate has one.

*   **`? No Match`:** This is the default status if a `✓ Match` cannot be proven.
    *   **Lack of Keyword:** The required skill, tool, or concept is not found in the `Skill & Technology Lexicon`.
    *   **Insufficient Experience:** The JD requires "7+ years," and the candidate has 4.
    *   **Degree Field Mismatch:** The JD requires a "Bachelor's in Computer Science," and the candidate has a "Bachelor's in Mining Engineering." Provide a reason like `(Degree in unrelated field)`.
    *   **Compound Requirement (Partial Match):** If a single qualification requires "SPARK and SQL" and the candidate only has "SQL," this is a `? No Match`. However, the reason must specify the partial nature: `(Partial Match, strong SQL skills but no SPARK)`. **Crucially, this still counts as 0 matches for scoring purposes.**

**2.2. Generate a Parenthetical Reason:**
For every `? No Match`, you MUST provide a brief, specific, evidence-based reason in parentheses. Examples: `(No mention of Python or R)`, `(Degree in unrelated field)`, `(No mention of Tableau experience)`.

**2.3. Tally the Scores:**
While analyzing, maintain the following counts in your memory:
*   `required_qualifications_matched_count`: Increment by 1 ONLY for a `✓ Match`.
*   `additional_qualifications_matched_count`: Increment by 1 ONLY for a `✓ Match`.
*   Store the full line-by-line analysis (icon + qualification text + reason) to be used in the final assessment.

---

### **Phase 3: Aggregation & Assessment Generation**

**3.1. Calculate the Rating:**
This step is purely mathematical and applies ONLY to the required qualifications.
1.  **Calculate Match Percentage:** `Match % = (required_qualifications_matched_count) / (Total number of required qualifications)`.
2.  **Determine the Final `rating` value:**
    *   If Match % >= 75%, the `rating` is **"high"**.
    *   If Match % is between 50% and 75%, the `rating` is **"medium"**.
    *   If Match % < 50%, the `rating` is **"low"**.

**3.2. Generate the `assessment_details` String:**
Construct the full, human-readable assessment as a multi-line string. Format it *exactly* as shown in the examples.

1.  **Select the Conversational Summary based on the `rating`:**
    *   **High:** "Your profile seems to match well with this job. Based on my review of your profile and similar applications on LinkedIn, you may be ready to apply."
    *   **Medium:** "Your profile matches several of the required qualifications. Based on my review of your resume, profile, and application history on LinkedIn, you may want to update your profile or take a look at other jobs where there might be a stronger match."
    *   **Low:** "Your profile is missing some required qualifications. Based on my review of your profile on LinkedIn, you may want to look at other jobs where there might be a stronger match."

2.  **Assemble the Full String:**
    ```
    Job match is [rating]\n\nFor [COMPANY_NAME] - [JOB_TITLE]\n\n[Conversational Summary]\n\n \n\nMatches [required_qualifications_matched_count] of the [total number of required qualifications] required qualifications:\n\n[Bulleted list of required qualifications with icons and reasons]\n\n \n\nMatches [additional_qualifications_matched_count] of the [total number of additional qualifications] additional qualifications:\n\n[Bulleted list of additional qualifications with icons and reasons]\n\n \n\nThere are qualifications that will likely be evaluated in the application or interview:\n\n[Bulleted list of evaluated qualifications]
    ```
    Store this entire formatted string in a variable called `assessment_details_string`.

**3.3. Generate the Final JSON Output:**
Construct the final JSON object using all the data you have collected and generated. The output must be a single, valid JSON object and nothing else.