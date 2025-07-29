# job-search

## About the Project
The motivation to build this project is to help a job seeker (me) retain their sanity while searching for a job in 2025. Based on many horror stories including personal experiences where job seekers may have to apply to hundreds and even thousands of job postings to land an interview, this project aims to streamline the job search process by maximizing both the volume of leads and the quality of job applications, ultimately improving the conversion of job leads.

Project scope:
1. ✅ Build a lead generation system to find job postings.
2. ✅ Build a lead scoring and qualification system to filter job postings.
3. 🚧 Build a content generation system to generate cover letters and resumes.
4. 🚧 Build a dashboard to track job applications.

## Current Features

### 1. Lead Generation System (✅ Implemented)
- **Job Boards Site Job Crawler**: Automated scraping of Job Boards Site job postings using Playwright
- **Multi-page Scraping**: Configurable pagination support for bulk job collection
- **Structured Data Extraction**: Extracts job title, company, location, salary, and URLs
- **Duplicate Prevention**: Unique job ID generation to avoid duplicate entries

### 2. Lead Qualification System (✅ Implemented)
- **AI-Powered Job Assessment**: Uses Google Gemini AI to analyze job compatibility
- **Resume Matching**: Structured evaluation against candidate resume
- **Qualification Scoring**: Separates required vs. additional qualifications
- **Skills Analysis**: Detailed breakdown of matched and missing skills
- **Rating System**: Provides match ratings and detailed assessment reports

### 3. Data Management & Storage
- **SQLite Database**: Comprehensive data model with 11+ tables
- **Job Tracking**: Complete job lifecycle from discovery to application
- **Document Store**: Version-controlled storage for resumes and prompts
- **LLM Run Tracking**: Audit trail for all AI interactions
- **Data Export**: JSONL exports for analysis and backup

### 4. API & Integration
- **FastAPI Server**: RESTful API for all operations
- **Async Operations**: Non-blocking database and AI operations
- **Comprehensive Logging**: Structured logging with rotation
- **Error Handling**: Robust error handling and quarantine system

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
uv run playwright codegen --browser chromium --save-storage=./playwright/.auth/auth_1.json https://www.jobboardssite.com
```

#### Core Operations

**1. Run Job Search and Collection:**
```python
from backend.crawler import scrape_job_boards_multi_page
from backend.api_server import process_jobs

# Search and collect jobs
results = await scrape_job_boards_multi_page("data analyst", max_pages=5)
await process_jobs(results)
```

**2. Assess Jobs Against Resume:**
```python
from backend.llm import assess_jobs_bulk

# Run AI assessment on collected jobs
await assess_jobs_bulk(max_jobs=50)
```

**3. API Endpoints:**
- `GET /jobs` - List all collected jobs
- `GET /jobs/{job_id}` - Get specific job details
- `GET /assessments` - List job assessments
- `POST /jobs/assess` - Trigger job assessment
- `GET /stats` - Get collection and assessment statistics

## Project Structure

```
backend/
├── api_server.py          # FastAPI application and endpoints
├── crawler.py             # Job Boards Site job scraping logic
├── llm.py                 # AI-powered job assessment
├── db.py                  # Database operations and models
├── db_init.py             # Database initialization
├── utilities.py           # Logging and utility functions
├── sql/                   # Database schema definitions
├── llm_prompts/           # AI prompt templates
├── logs/                  # Application logs
└── db_exports/            # Data export files
```

## Database Schema

The system uses a comprehensive SQLite schema with the following key tables:
- `job_runs` - Search execution tracking
- `job_details` - Master job listings
- `job_assessment` - AI-generated job evaluations
- `job_skills` - Extracted skill requirements
- `document_store` - Resume and prompt versioning
- `llm_runs` - AI interaction audit trail
- `job_quarantine` - Failed processing tracking

## Roadmap

### Completed ✅
- [x] Job Boards Site job scraping system
- [x] SQLite database schema and operations
- [x] AI-powered job assessment using Google Gemini
- [x] RESTful API with FastAPI
- [x] Comprehensive logging and error handling
- [x] Data export and backup functionality

### In Progress 🚧
- [ ] Frontend dashboard for job tracking
- [ ] Cover letter generation system
- [ ] Resume customization based on job requirements
- [ ] Email notification system

### Planned 📋
- [ ] Support for additional job boards (Indeed, Glassdoor, etc.)
- [ ] Advanced filtering and search capabilities
- [ ] Application status tracking
- [ ] Interview preparation assistance
- [ ] Performance analytics and insights
- [ ] Mobile application

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

- **Rate Limiting**: Built-in delays to respect Job Boards Site's terms of service
- **Async Operations**: Non-blocking database and AI operations
- **Error Recovery**: Quarantine system for problematic jobs
- **Memory Management**: Efficient data processing for large job collections

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

* [Playwright](https://playwright.dev/) for excellent browser automation
* [Google Gemini AI](https://ai.google.dev/) for powerful language processing
* [FastAPI](https://fastapi.tiangolo.com/) for the fantastic web framework
* [uv](https://github.com/astral-sh/uv) for modern Python package management