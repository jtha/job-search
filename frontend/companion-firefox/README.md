# page-extractor-firefox

Firefox extension to extract a job page, send it to a local API for assessment, and review results in History/Session views.

This extension provides:

- A sidebar with an Extract button to submit the current tab for processing
- A History page listing the most recently assessed jobs coming directly from the backend
- A Session page showing all tasks you have submitted (with status, details, and actions) stored locally


## How it works

- When you click Extract in the sidebar, the extension creates a task object and saves it to `browser.storage.local` with a unique `id`, the `url`, timestamps, and `status`.
- The background script (see `background.js`) handles the `processJob` message to process the page and eventually populate the task’s `data` with parsed job details and assessment information.
- The History page (`history/history.html` + `history.js`) fetches the latest assessed jobs directly from your local API and displays per-job match fractions and details on demand.
- The Session page (`session/session.html` + `session.js`) reads tasks from `browser.storage.local`, lets you expand each job for details, copy descriptions, re-run assessments, and toggle “applied” status.


## Prerequisites

- Firefox Browser
- Local API server running on `http://127.0.0.1:8000` that implements the endpoints used by the extension (see Endpoints below). The companion repo "job-search" contains such a server.


## Install (temporary, for development)

1. Open Firefox and go to `about:debugging#/runtime/this-firefox`.
2. Click “Load Temporary Add-on…”.
3. Select this folder (or choose `manifest.json`).
4. The extension will load for the current session; it will be removed when Firefox restarts.


## Using the sidebar

Open the extension sidebar and you’ll see:

- Extract: Queues the current active tab for processing.
	- Only works on regular HTTP(S) pages.
	- Creates a task: `{ id, url, status: 'queued', submittedAt, data: null }` and sends a message to the background.
- History: Opens the History page in a new tab.
- Session: Opens the Session page in a new tab.

Status messages appear in the sidebar to confirm submission or show errors (e.g., trying to run on a non-webpage).


## Session page

The Session view reads all tasks from `browser.storage.local` and shows a list sorted by submission time.

For each entry:

- Row header shows the job title, company, location, status dot, and match fractions.
	- Required fraction: matched/total required qualifications
	- Additional fraction: matched/total additional qualifications
	- Colored classes indicate quality: good/ok/bad/empty
- Clicking the row expands details:
	- A data table with Company, Title, Salary, Location, and a direct job link
	- Action bar with:
		- Regenerate Assessment: calls the backend to re-run the assessment for this `job_id`
		- Applied toggle: marks/unmarks the job as applied
	- Description with a Copy button
	- Three qualification sections (tables):
		- Required Qualifications (Requirement | Match | Match Reason)
		- Additional Qualifications (Requirement | Match | Match Reason)
		- Evaluated Qualifications (Requirement)

Visuals:

- Clicking Applied toggles CSS class `applied` on the row and persists the state back into the task object in storage.
- Status dot reflects `task.status` (e.g., `queued`, `processing`, `completed`).


## History page

The History view pulls data directly from the local API and shows the most recently assessed jobs.

Controls:

- Days Back: Set how many days to look back (defaults to 5). Input id: `days-back`.
- Refresh: Re-fetches recent jobs.

Per-row display:

- Title, company, location, last assessed timestamp
- Required and Additional match fractions with color classes
- Expand for details (same sections as History): data table, regenerate button, applied toggle, description copy, and qualification tables

Applied state:

- The History view seeds `applied` state from the API payload (`job_applied`), and locally toggling Applied updates both UI and backend via the endpoints below.


## Endpoints used (local API)

The extension expects these endpoints at `http://127.0.0.1:8000`:

- `GET /jobs_recent?days_back=<int>&limit=<int>` — list of recently assessed jobs
- `GET /job_skills` — all job skill rows; the History page caches and maps per job
- `POST /regenerate_job_assessment` with body `{ job_id }` — re-run assessment and return updated job data
- `POST /update_job_applied` with body `{ job_id }` — mark job as applied
- `POST /update_job_unapplied` with body `{ job_id }` — unmark job as applied

Returned job data is rendered into:

- Data table fields: `job_company`, `job_title`, `job_salary`, `job_location`, `job_url_direct`
- Description: `job_description`
- Qualification arrays:
	- Required: items with `requirement`, `match` (1|0|true|false), `match_reason`
	- Additional: same structure as required
	- Evaluated: items with `requirement` only


## UI behaviors and indicators

- Match fractions are computed as matched/total for Required and Additional sections and styled via classes: `fraction-good`, `fraction-ok`, `fraction-bad`, `fraction-empty`.
- Rows gain `expanded` when open and `applied` when marked applied.
- Copy buttons use the Clipboard API on extension pages to copy `job_description`.


## Storage model (History)

Tasks are stored under their unique `id` in `browser.storage.local`. Each task resembles:

```
{
	id: "task_1699999999999",
	url: "https://example.com/job/123",
	status: "queued" | "processing" | "completed" | "error",
	submittedAt: "2025-08-14T12:34:56.000Z",
	completedAt?: "2025-08-14T12:35:30.000Z",
	data: { /* job fields from backend, including job_id, qualifications, etc. */ },
	error: null | string
}
```

The History view listens to `browser.storage.onChanged` to auto-refresh when tasks update.


## Troubleshooting

- Recent shows “API Error” or empty state: Ensure your local API is running on `127.0.0.1:8000` and implements the endpoints above.
- Regenerate/Applied actions fail: Check backend logs and CORS/permissions on the local server. The request body must include the correct `job_id`.
- Extract disabled or errors: Make sure the active tab is an HTTP(S) page and try again.


## Development notes

- Core scripts documented here:
	- `sidebar/sidebar.js` — Sidebar UI, task creation, and navigation to History/Session
	- `session/session.js` — Renders stored tasks, details, actions, and live updates
	- `history/history.js` — Fetches from API, caches skills, renders rows and details
- Supporting assets: `styles/`, `icons/`, and HTML files under `history/`, `session/`, `sidebar/`.
- Background workflow is handled in `background.js`.

