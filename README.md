# job-search

## About the Project
This project automates job search tasks for job seekers who need to apply to multiple positions efficiently. The system addresses the challenge of managing high-volume job applications by automating lead generation, qualification, and application tracking.

Project scope:
1. ✅ Build a lead generation system to find job postings.
2. ✅ Build a lead scoring and qualification system to filter job postings.
3. 🚧 Build a content generation system to generate cover letters and resumes.
4. 🚧 Build a dashboard to track job applications.

## Current Features

### 1. Lead Generation System (✅ Implemented)
- **LinkedIn Job Crawler**: Automated scraping of LinkedIn job postings using Playwright
- **Multi-page Scraping**: Configurable pagination support for bulk job collection
- **Structured Data Extraction**: Extracts job title, company, location, salary, and URLs
- **Duplicate Prevention**: Unique job ID generation to avoid duplicate entries
- **Job Description Extraction**: Secondary scraping to collect detailed job descriptions

### 2. Lead Qualification System (✅ Implemented)
- **AI Assessment**: 4-step job analysis pipeline using Google Gemini AI
  - **Job Description Tagging**: Categorizes requirements as required vs. additional
  - **Atomic Decomposition**: Breaks down requirements into individual skill components
  - **Classification**: Categorizes skills as required, additional, or evaluated qualifications
  - **Resume Matching**: Individual assessment of each skill against candidate profile
- **Structured Data Generation**: JSON schema-based responses for consistent analysis
- **Skills Database**: Storage of job requirements and match results
- **Concurrent Processing**: Semaphore-controlled parallel assessment for scalability
- **Error Recovery**: Quarantine system with retry logic for failed assessments
- **Token Usage Tracking**: Monitoring of AI API consumption

### 3. Data Management & Storage
- **SQLite Database**: Data model with 12+ tables including:
  - **job_skills**: Atomic skill requirements and match assessments
  - **llm_runs_v2**: Audit trail of AI interactions
  - **job_quarantine**: Failed job processing management
  - **prompts**: Version-controlled AI prompt templates
- **Job Lifecycle Tracking**: Job journey from discovery to assessment
- **Document Store**: Version-controlled storage for resumes and prompts
- **Prompt Management**: Template-based system with versioning and model configuration
- **Data Export**: JSONL exports for analysis and backup

### 4. API & Integration
- **FastAPI Server**: RESTful API for all operations
- **Async Operations**: Non-blocking database and AI operations
- **Structured Logging**: Logging with rotation
- **Error Handling**: Error handling and quarantine system

### Built With

#### Backend
* [Python 3.12+](https://www.python.org/) - Core language
* [FastAPI](https://fastapi.tiangolo.com/) - Web framework
* [Playwright](https://playwright.dev/) - Browser automation for scraping
* [SQLite](https://www.sqlite.org/) - Database
* [Google Gemini AI](https://ai.google.dev/) - AI-powered job assessment
* [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) - HTML parsing
* [Pydantic](https://pydantic.dev/) - Data validation
* [aiosqlite](https://aiosqlite.omnilib.dev/) - Async SQLite operations

#### Development Tools
* [uv](https://github.com/astral-sh/uv) - Python package management
* [pytest-playwright](https://playwright.dev/python/docs/test-runners) - Testing framework

## Getting Started

### Prerequisites
- Python 3.12 or higher
- Google Gemini API key
- Chromium browser (installed via Playwright)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/jtha/job-search.git
cd job-search
```

2. Install dependencies using uv:
```bash
uv sync
```

3. Install Playwright browsers:
```bash
uv run playwright install chromium
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

5. Initialize the database:
```bash
uv run python -m backend.db_init
```

### Usage

#### Start the API Server
```bash
uv run uvicorn backend.api_server:app --reload
```

#### Browser Authentication Setup
Periodically log on to authenticate browser and save cookies to file:  
```bash
uv run playwright codegen --browser chromium --save-storage=./playwright/.auth/auth_1.json https://www.linkedin.com
```

#### Core Operations

**1. Run Job Search and Collection:**
```bash
# Use the API to scrape LinkedIn jobs
curl -X POST "http://localhost:8000/scrape_linkedin_multi_page" \
     -H "Content-Type: application/json" \
     -d '{"keywords": ["data analyst", "python developer"], "max_pages": 5}'
```

**2. Fill Missing Job Descriptions:**
```bash
# Extract detailed job descriptions for collected jobs
curl -X POST "http://localhost:8000/fill_missing_job_descriptions?min_length=200"
```

**3. Assess Jobs Against Resume:**
```bash
# Run AI assessment on collected jobs
curl -X POST "http://localhost:8000/generate_job_assessments?limit=50&days_back=14&semaphore_count=5"
```

**4. Retry Failed Assessments:**
```bash
# Process quarantined jobs that failed initial assessment
curl -X POST "http://localhost:8000/generate_failed_job_assessments?limit=50&days_back=14&semaphore_count=5"
```

**3. API Endpoints:**
- `GET /job_details` - List all collected jobs
- `GET /job_skills` - List job skill requirements and assessments
- `GET /llm_runs_v2` - List AI interaction history
- `POST /scrape_linkedin_multi_page` - Trigger LinkedIn job collection
- `POST /fill_missing_job_descriptions` - Extract detailed job descriptions
- `POST /generate_job_assessments` - Trigger job assessment pipeline
- `POST /generate_failed_job_assessments` - Retry failed assessments
- `GET /prompts` - List AI prompt configurations

## Project Structure

```
backend/
├── api_server.py          # FastAPI application and endpoints
├── crawler.py             # LinkedIn job scraping logic
├── llm.py                 # AI-powered job assessment with 4-step pipeline
├── db.py                  # Database operations and models
├── db_init.py             # Database initialization
├── utilities.py           # Logging and utility functions
├── sql/                   # Database schema definitions
├── llm_prompts/           # AI prompt templates with versioning
├── logs/                  # Application logs
└── db_exports/            # Data export files

docs/
├── 01_lead_generation_system.md    # LinkedIn scraping documentation
└── 02_lead_qualification_system.md # AI assessment pipeline documentation

manually_generated/        # Generated resumes and cover letters
notebooks/                 # Jupyter notebooks for analysis and testing
playwright/                # Browser automation and authentication
```

## Database Schema

The system uses a SQLite schema with the following key tables:
- `job_runs` - Search execution tracking
- `job_details` - Master job listings
- `job_skills` - Atomic skill requirements and match assessments
- `job_quarantine` - Failed processing tracking and retry management
- `document_store` - Resume and prompt versioning
- `llm_runs_v2` - AI interaction audit trail with token usage
- `prompts` - Version-controlled AI prompt templates with model configuration
- `run_findings` - Links job runs to discovered jobs

## Roadmap

### Completed ✅
- [x] LinkedIn job scraping system with authentication management
- [x] SQLite database schema with 12+ tables for data tracking
- [x] AI-powered job assessment using Google Gemini with structured generation
- [x] Atomic skill decomposition and requirement categorization system
- [x] RESTful API with FastAPI including job collection and assessment endpoints
- [x] Logging and error handling with quarantine/retry system
- [x] Prompt management system with versioning and model configuration
- [x] Token usage tracking and cost monitoring for AI operations
- [x] Concurrent processing with semaphore control for scalability
- [x] Data export and backup functionality

### In Progress 🚧
- [ ] Frontend dashboard for job tracking
- [ ] Cover letter generation system
- [ ] Resume customization based on job requirements

### Planned 📋
- [ ] Support for additional job boards (Indeed, Glassdoor, etc.)
- [ ] Advanced filtering and search capabilities for assessed jobs
- [ ] Application status tracking and follow-up automation
- [ ] Interview preparation assistance based on job skill gaps
- [ ] Performance analytics and insights with cost optimization reports
- [ ] Job recommendation engine based on skill match scores
- [ ] Automated job application submission for high-match positions

## Configuration

### Environment Variables
Create a `.env` file in the root directory:
```
GEMINI_API_KEY=your_google_gemini_api_key_here
```

### Logging Configuration
Logging is configured via `backend/logging.conf` with:
- Rotating file logs (5 files, 10MB each)
- Console output for development
- Separate loggers for different modules

## API Documentation

Once the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Performance Considerations

- **Rate Limiting**: Built-in delays to respect LinkedIn's terms of service
- **Async Operations**: Non-blocking database and AI operations with semaphore control
- **Error Recovery**: Quarantine system with retry logic for problematic jobs
- **Memory Management**: Efficient data processing for large job collections
- **Token Optimization**: Monitoring and optimization of AI API usage and costs

## Contributing

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contact

Project Link: [https://github.com/jtha/job-search](https://github.com/jtha/job-search)

## Acknowledgments

* [Playwright](https://playwright.dev/) for browser automation
* [Google Gemini AI](https://ai.google.dev/) for language processing
* [FastAPI](https://fastapi.tiangolo.com/) for the web framework
* [uv](https://github.com/astral-sh/uv) for Python package management