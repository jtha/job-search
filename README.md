# job-search

## About the Project
This project automates job search tasks for job seekers who need to apply to multiple positions efficiently. The system addresses the challenge of managing high-volume job applications by providing user-controlled job extraction, AI-powered qualification analysis, and application tracking.

Project scope:
1. ✅ Build a lead generation system to extract job postings from LinkedIn.
2. ✅ Build a lead scoring and qualification system to filter job postings.
3. 🚧 Build a content generation system to generate cover letters and resumes.
4. 🚧 Build a dashboard to track job applications.

## Current Features

### 1. Lead Generation System (✅ Implemented)
- **Firefox Browser Extension**: User-controlled job data extraction from LinkedIn job postings
- **HTML Content Processing**: Manual extraction and parsing of LinkedIn job page content
- **Background Task Management**: Asynchronous processing with task queuing and status tracking
- **Multi-page Dashboard**: Comprehensive interface for job management, history, and resume viewing
- **Structured Data Extraction**: Extracts job title, company, location, salary, and full descriptions
- **Automatic Assessment Integration**: Seamlessly triggers AI analysis after successful extraction
- **OpenRouter Credit Monitoring**: Real-time API usage tracking and cost awareness

### 2. Lead Qualification System (✅ Implemented)
- **AI Assessment**: 4-step job analysis pipeline using OpenRouter's reasoning-capable models
  - **Job Description Tagging**: Categorizes requirements as required vs. additional
  - **Atomic Decomposition**: Breaks down requirements into individual skill components
  - **Classification**: Categorizes skills as required, additional, or evaluated qualifications
  - **Resume Matching**: Individual assessment of each skill against candidate profile
- **Pydantic Schema Validation**: Type-safe structured responses for consistent analysis
- **Conservative Matching Logic**: Evidence-based matching with detailed reasoning for each decision
- **Skills Database**: Comprehensive storage of job requirements and match assessments
- **Concurrent Processing**: Semaphore-controlled parallel assessment for scalability
- **Error Recovery**: Quarantine system with retry logic for failed assessments
- **Token Usage Tracking**: Detailed monitoring of AI API consumption with cost optimization

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

### 4. Frontend & User Interface
- **Firefox Browser Extension**: Complete job extraction and management interface
  - **Sidebar Interface**: Primary job processing controls and status monitoring
  - **Dashboard Pages**: Multi-page interface for job overview, history, session tracking, and resume viewing
  - **Task Management**: Local storage-based task queuing with status tracking
  - **Real-time Updates**: Live status updates during job processing
- **Extension Security**: Minimal permissions with secure localhost API communication
- **Cross-session Persistence**: Task and job data persistence across browser sessions

### 5. API & Integration
- **FastAPI Server**: RESTful API for all operations
- **Async Operations**: Non-blocking database and AI operations
- **Structured Logging**: Logging with rotation
- **Error Handling**: Error handling and quarantine system

### Built With

#### Backend
* [Python 3.12+](https://www.python.org/) - Core language
* [FastAPI](https://fastapi.tiangolo.com/) - Web framework
* [SQLite](https://www.sqlite.org/) - Database
* [OpenRouter](https://openrouter.ai/) - AI-powered job assessment with reasoning models
* [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) - HTML parsing
* [Pydantic](https://pydantic.dev/) - Data validation and structured responses
* [aiosqlite](https://aiosqlite.omnilib.dev/) - Async SQLite operations
* [Jinja2](https://jinja.palletsprojects.com/) - Template rendering for AI prompts
* [Markdownify](https://github.com/matthewwithanm/python-markdownify) - HTML to Markdown conversion

#### Frontend
* [Firefox WebExtension API](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions) - Browser extension framework
* [Manifest V3](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/manifest_version) - Extension architecture
* Vanilla JavaScript - Extension logic and UI interactions
* HTML5 & CSS3 - Extension interface and styling

#### Development Tools
* [uv](https://github.com/astral-sh/uv) - Python package management

## Getting Started

### Prerequisites
- Python 3.12 or higher
- OpenRouter API key
- Firefox browser
- Backend API server running locally

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

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

4. Initialize the database:
```bash
uv run python -m backend.db_init
```

5. Start the API server (initial prompts will auto-seed on first run):
```bash
uv run uvicorn backend.api_server:app --reload
```
The server's startup process now performs an "insert-if-missing" seed of the required LLM prompt templates used by the assessment pipeline. This is idempotent—only absent `llm_run_type` prompts are inserted; existing ones are never modified. To disable automatic seeding set `INITIAL_PROMPT_SEED=0` in your environment.

Optional manual re-run (does the same insert-if-missing logic):
```bash
uv run python -m backend.llm_prompts
```

6. Load the Firefox extension:
   - Open Firefox and navigate to `about:debugging`
   - Click "This Firefox" > "Load Temporary Add-on"
   - Navigate to `frontend/companion-firefox/` and select `manifest.json`
   - Grant required permissions when prompted

### Usage

#### Start the API Server
```bash
uv run uvicorn backend.api_server:app --reload
```

#### Prompt Templates
On first startup the API automatically inserts any missing required prompt templates. If you add new initial run types to `backend/prompt_catalog_initial.py`, restart the server or run:
```bash
uv run python -m backend.llm_prompts
```
This only inserts prompts that are missing; existing rows are preserved for future management by a separate module.

#### Using the Firefox Extension

**1. Navigate to LinkedIn Job:**
- Visit any LinkedIn job posting page
- Click the extension icon to open the sidebar

**2. Process Job:**
- Click "Process Job" button in the sidebar
- Monitor processing status in real-time
- Job will be automatically extracted and assessed

**3. View Results:**
- Access processed jobs via the extension dashboard
- View detailed qualification analysis and match reasoning
- Track processing history and session statistics

#### API Operations

**1. Manual HTML Extraction:**
```bash
# Process job HTML content directly
curl -X POST "http://localhost:8000/html_extract" \
     -H "Content-Type: application/json" \
     -d '{"html": "<html>...</html>", "url": "https://www.linkedin.com/jobs/view/12345678"}'
```

**2. Regenerate Job Assessment:**
```bash
# Reprocess a specific job with updated prompts
curl -X POST "http://localhost:8000/regenerate_job_assessment" \
     -H "Content-Type: application/json" \
     -d '{"job_id": "12345678"}'
```

**3. Manage Application Status:**
```bash
# Mark job as applied
curl -X POST "http://localhost:8000/update_job_applied" \
     -H "Content-Type: application/json" \
     -d '{"job_id": "12345678"}'

# Revert application status  
curl -X POST "http://localhost:8000/update_job_unapplied" \
     -H "Content-Type: application/json" \
     -d '{"job_id": "12345678"}'
```

**4. API Endpoints:**
- `GET /job_details` - List all collected jobs
- `GET /jobs_recent?days_back=5&limit=300` - Recent assessed jobs  
- `GET /job_skills_recent?days_back=5&limit=300` - Recent job skills analysis
- `GET /openrouter_credits` - Check API credit balance
- `GET /master_resume` - Get master resume document
- `POST /html_extract` - Process job HTML content
- `POST /regenerate_job_assessment` - Regenerate job assessment
- `POST /update_job_applied` - Mark job as applied
- `POST /update_job_unapplied` - Revert application status

## Project Structure

```
backend/
├── api_server.py          # FastAPI application and endpoints  
├── crawler.py             # LinkedIn HTML parsing and job data extraction
├── llm.py                 # OpenRouter AI-powered job assessment pipeline
├── db.py                  # Database operations and models
├── db_init.py             # Database initialization
├── utilities.py           # Logging and utility functions
├── sql/                   # Database schema definitions
├── llm_prompts/           # AI prompt templates with versioning
├── logs/                  # Application logs
└── db_exports/            # Data export files

frontend/
└── companion-firefox/     # Firefox browser extension
    ├── manifest.json      # Extension configuration
    ├── background.js      # Background worker for API calls
    ├── sidebar/           # Main extraction interface
    ├── dashboard/         # Job management overview
    ├── history/           # Processing history view  
    ├── session/           # Current session tracking
    ├── resume/            # Resume viewer
    ├── shared/            # Shared navigation components
    └── styles/            # Extension styling

docs/
├── 01_lead_generation_system.md       # Firefox extension & HTML extraction documentation
├── 02_lead_qualification_system.md    # AI assessment pipeline documentation
└── 03_firefox_extension.md           # Complete browser extension documentation
```

## Database Schema

The system uses a SQLite schema with the following key tables:
- `job_details` - Master job listings with extraction metadata
- `job_skills` - Atomic skill requirements and detailed match assessments
- `job_quarantine` - Failed processing tracking and retry management
- `document_store` - Resume and prompt versioning with job references
- `llm_runs_v2` - Complete AI interaction audit trail with token usage tracking
- `prompts` - Version-controlled AI prompt templates with model configurations
- `llm_models` - Model definitions with cost per token for usage monitoring

## Roadmap

### Completed ✅
- [x] Firefox browser extension for user-controlled job extraction from LinkedIn
- [x] Multi-page extension interface with dashboard, history, session, and resume views
- [x] HTML content processing system with LinkedIn job page parsing
- [x] SQLite database schema with comprehensive job and assessment tracking
- [x] OpenRouter AI-powered job assessment using reasoning-capable models
- [x] 4-step atomic skill decomposition and requirement categorization system
- [x] Pydantic-based structured response validation for consistent AI outputs
- [x] RESTful API with FastAPI for job processing and assessment management
- [x] Comprehensive logging and error handling with quarantine/retry system
- [x] Database-driven prompt management with versioning and model configuration
- [x] Detailed token usage tracking and cost monitoring for AI operations
- [x] Conservative matching logic with evidence-based assessment reasoning
- [x] Real-time job processing status updates and task management

### In Progress 🚧
- [ ] Enhanced frontend dashboard for comprehensive job tracking and analytics
- [ ] AI-powered cover letter generation system tailored to job requirements
- [ ] Dynamic resume customization based on job skill gap analysis
- [ ] Application status tracking with automated follow-up scheduling

### Planned 📋
- [ ] Chrome/Chromium browser extension support for cross-browser compatibility
- [ ] Support for additional job boards (Indeed, Glassdoor, etc.)
- [ ] Advanced filtering and search capabilities for assessed jobs with skill-based sorting
- [ ] Interview preparation assistance based on identified job skill gaps
- [ ] Performance analytics dashboard with cost optimization insights and trends
- [ ] Job recommendation engine using machine learning on historical match patterns

## Configuration

### Environment Variables
Create a `.env` file in the root directory:
```
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### Extension Configuration
The Firefox extension is configured via `manifest.json` with:
- Minimal required permissions (activeTab, scripting, storage)
- Content Security Policy allowing localhost API connections
- Sidebar interface as the primary interaction method

### API Configuration
- **Backend Server**: Must run on `http://127.0.0.1:8000` for extension compatibility
- **Database**: SQLite database with automatic schema initialization
- **Master Resume**: Must be loaded as a document in the system for assessments

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

- **User-Controlled Processing**: Manual job extraction eliminates rate limiting concerns
- **Background Task Management**: Non-blocking API calls with real-time status updates
- **Conservative AI Assessment**: Evidence-based matching minimizes false positives
- **Async Operations**: Non-blocking database and AI operations with semaphore control
- **Error Recovery**: Comprehensive quarantine system with retry logic for problematic jobs
- **Memory Efficiency**: Minimal browser extension footprint with efficient data processing
- **Token Optimization**: Intelligent prompt engineering and model selection for cost control
- **Local Storage**: Task persistence across browser sessions without external dependencies

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

* [OpenRouter](https://openrouter.ai/) for cost-effective AI model access with reasoning capabilities
* [FastAPI](https://fastapi.tiangolo.com/) for the high-performance web framework
* [Firefox WebExtension API](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions) for browser extension support
* [Pydantic](https://pydantic.dev/) for data validation and structured AI responses
* [uv](https://github.com/astral-sh/uv) for efficient Python package management