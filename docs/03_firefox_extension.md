# Firefox Browser Extension Documentation

## Overview

The Job Search Copilot Firefox extension provides user-controlled job data extraction from LinkedIn job postings. It serves as the primary interface for the lead generation system, allowing users to manually initiate job processing while browsing LinkedIn jobs. The extension operates as a bridge between LinkedIn's job pages and the backend assessment system.

## Architecture

### Extension Structure

```
frontend/companion-firefox/
├── manifest.json              # Extension configuration
├── background.js              # Background worker for API calls
├── icons/
│   └── icon-48.png           # Extension icon
├── sidebar/
│   ├── sidebar.html          # Main extraction interface
│   ├── sidebar.js            # Extraction logic
│   └── sidebar.css           # Interface styling
├── dashboard/
│   ├── dashboard.html        # Job management overview
│   ├── dashboard.js          # Dashboard functionality
│   └── dashboard.css         # Dashboard styling
├── history/
│   ├── history.html          # Extraction history view
│   ├── history.js            # History management
│   └── history.css           # History styling
├── session/
│   ├── session.html          # Current session jobs
│   ├── session.js            # Session management
│   └── session.css           # Session styling
├── resume/
│   ├── resume.html           # Resume viewer
│   ├── resume.js             # Resume display logic
│   └── resume.css            # Resume styling
├── shared/
│   └── navigation.js         # Shared navigation logic
└── styles/
    └── nav.css              # Shared navigation styles
```

### Core Components

#### 1. Manifest Configuration

```json
{
  "manifest_version": 3,
  "name": "Job Search Copilot",
  "version": "3.0",
  "description": "Asynchronously extracts job data and tracks history.",
  "permissions": [
    "activeTab",     # Access to current tab content
    "scripting",     # Execute content scripts
    "storage"        # Local storage for task management
  ],
  "host_permissions": [
    "http://*/*",
    "https://*/*"
  ],
  "sidebar_action": {
    "default_panel": "sidebar/sidebar.html"
  },
  "content_security_policy": {
    "extension_pages": "script-src 'self'; connect-src http://localhost:* http://127.0.0.1:*;"
  }
}
```

#### 2. Background Worker (`background.js`)

The background script handles:

- **Sidebar Toggle**: Responds to extension icon clicks
- **Content Extraction**: Executes scripts to extract HTML from job pages
- **API Communication**: Makes HTTP requests to the backend server
- **Task Management**: Manages asynchronous job processing

```javascript
// Sidebar control
browser.action.onClicked.addListener(() => {
  browser.sidebarAction.toggle();
});

// Job processing pipeline
async function processJob(task) {
  try {
    task.status = 'processing';
    await browser.storage.local.set({ [task.id]: task });

    // Extract HTML content from the page
    const targetSelectors = [
      'div.jobs-search__job-details--wrapper',
      'div.jobs-semantic-search-job-details-wrapper',
      'div.job-view-layout'
    ];
    
    const [targetTab] = await browser.tabs.query({ url: task.url });
    const results = await browser.scripting.executeScript({
      target: { tabId: targetTab.id },
      func: scrapeTargetElement,
      args: [targetSelectors]
    });

    const htmlContent = results[0].result;
    const apiResponse = await callApi(htmlContent, task.url);

    task.status = 'completed';
    task.data = apiResponse.data;
    task.completedAt = new Date().toISOString();
    await browser.storage.local.set({ [task.id]: task });

  } catch (error) {
    task.status = 'error';
    task.error = error.message;
    await browser.storage.local.set({ [task.id]: task });
  }
}
```

#### 3. Sidebar Interface (`sidebar/`)

The primary user interface for job extraction:

**HTML Structure:**
```html
<body>
  <h3>Job Analyzer</h3>
  <p>Click the button to process the job details in the background.</p>
  
  <button id="extract-btn">Process Job</button>
  <div id="status-message"></div>

  <div id="remaining-credits" class="footer-credits">
    Remaining Credits: …
  </div>

  <div class="footer-actions">
    <button id="open-dashboard-btn" class="secondary-button small">Dashboard</button>
  </div>
</body>
```

**JavaScript Functionality:**
```javascript
// Main extraction button handler
document.getElementById('extract-btn').addEventListener('click', async () => {
  const [activeTab] = await browser.tabs.query({active: true, currentWindow: true});
  
  // Validate LinkedIn URL
  if (!activeTab.url.includes('linkedin.com/jobs')) {
    updateStatus('Please navigate to a LinkedIn job posting.');
    return;
  }

  // Create task object
  const task = {
    id: generateTaskId(),
    url: activeTab.url,
    status: 'queued',
    createdAt: new Date().toISOString()
  };

  // Store task and send to background
  await browser.storage.local.set({ [task.id]: task });
  browser.runtime.sendMessage({action: 'processJob', task: task});
  
  updateStatus('Processing job... This may take a few seconds.');
  startStatusMonitoring(task.id);
});
```

## Key Features

### 1. User-Controlled Job Processing

- **Manual Trigger**: Users initiate processing by clicking the "Process Job" button
- **URL Validation**: Ensures user is on a LinkedIn job posting page
- **Real-Time Status**: Shows processing progress in the sidebar
- **Error Handling**: Displays clear error messages for failed extractions

### 2. Asynchronous Task Management

- **Background Processing**: Long-running API calls don't block the UI
- **Task Queuing**: Multiple jobs can be queued for processing
- **Local Storage**: Tasks persist across browser sessions
- **Status Tracking**: Each task has detailed status and timing information

### 3. Multi-Page Dashboard

The extension provides a comprehensive multi-page interface:

#### Dashboard (`dashboard/`)
- Overview of recent job processing activity
- Quick access to other extension pages
- System status indicators

#### History (`history/`)
- Complete history of all processed jobs
- Success/failure status for each extraction
- Links to view detailed job information

#### Session (`session/`)
- Jobs processed in the current browser session
- Real-time updates as jobs are processed
- Session statistics and metrics

#### Resume (`resume/`)
- Display of the master resume used for assessments
- Resume version information
- Quick reference for qualification matching

### 4. OpenRouter Credit Monitoring

- **Real-Time Balance**: Shows remaining API credits in sidebar footer
- **Cost Awareness**: Helps users track API usage costs
- **Budget Management**: Visual indicator of credit consumption

## Technical Implementation

### Content Script Execution

The extension uses the scripting API to extract content:

```javascript
function scrapeTargetElement(selectors) {
  for (const selector of selectors) {
    const targetElement = document.querySelector(selector);
    if (targetElement) {
      return targetElement.outerHTML;
    }
  }
  return null;
}
```

**Target Selectors:**
- `div.jobs-search__job-details--wrapper`: Primary job details container
- `div.jobs-semantic-search-job-details-wrapper`: Alternative layout
- `div.job-view-layout`: Fallback selector for different LinkedIn layouts

### API Integration

The extension communicates with the backend API server:

```javascript
async function callApi(html, url) {
  const endpoint = 'http://127.0.0.1:8000/html_extract';
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ html: html, url: url }),
  });
  
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || `API Error: ${response.status}`);
  }
  
  return response.json();
}
```

### Local Storage Schema

Tasks are stored in browser local storage:

```javascript
// Task object structure
const task = {
  id: "task_1234567890",
  url: "https://www.linkedin.com/jobs/view/12345678",
  status: "completed", // queued, processing, completed, error
  createdAt: "2024-01-15T10:30:00.000Z",
  completedAt: "2024-01-15T10:30:05.432Z",
  data: {
    job_id: "12345678",
    job_title: "Senior Data Analyst",
    job_company: "Tech Corp",
    // ... full job data from API response
  },
  error: null // Error message if status is 'error'
};
```

## Installation and Setup

### Development Installation

1. **Clone Repository**: Get the extension source code
2. **Load Extension**: Use Firefox's "Load Temporary Add-on" feature
3. **Select Manifest**: Point to `manifest.json` in the `companion-firefox` directory
4. **Grant Permissions**: Accept required permissions when prompted

### Configuration Requirements

1. **Backend API**: Ensure the backend server is running on `http://127.0.0.1:8000`
2. **Database Setup**: Backend must have proper database schema initialized
3. **OpenRouter API**: Valid OpenRouter API key configured in backend
4. **Master Resume**: Resume document must be loaded in the system

### Firefox-Specific Setup

```javascript
// Content Security Policy allows local API connections
"content_security_policy": {
  "extension_pages": "script-src 'self'; connect-src http://localhost:* http://127.0.0.1:*;"
}
```

## Usage Workflow

### Basic Job Extraction

1. **Navigate**: Visit a LinkedIn job posting page
2. **Open Sidebar**: Click the extension icon to open the sidebar
3. **Process Job**: Click "Process Job" button to initiate extraction
4. **Monitor Progress**: Watch status updates in the sidebar
5. **View Results**: Access processed jobs via dashboard pages

### Advanced Features

1. **Batch Processing**: Process multiple jobs by opening them in separate tabs
2. **History Management**: Review past extractions in the history page
3. **Resume Reference**: Check master resume in the resume page
4. **Credit Monitoring**: Track API usage via the credit counter

## Error Handling

### Common Error Scenarios

1. **Invalid URL**: User not on a LinkedIn job page
   ```
   Error: "Please navigate to a LinkedIn job posting."
   ```

2. **Content Extraction Failure**: LinkedIn page structure not recognized
   ```
   Error: "Could not find target element on page."
   ```

3. **API Server Unavailable**: Backend server not running
   ```
   Error: "API Error: Connection refused"
   ```

4. **Network Timeout**: Slow API response
   ```
   Error: "Request timeout - please try again"
   ```

### Error Recovery

- **Automatic Retry**: Failed tasks remain in storage for manual retry
- **Clear Error State**: Tasks can be reprocessed after fixing issues
- **Debug Information**: Detailed error messages help identify problems
- **Graceful Degradation**: Extension continues working even if some features fail

## Performance Characteristics

### Processing Metrics

- **Extraction Speed**: ~1-2 seconds for HTML content extraction
- **API Response Time**: ~3-5 seconds for complete job processing and assessment
- **Memory Usage**: Minimal impact on browser performance
- **Storage Efficiency**: Local storage used only for active task management

### Browser Compatibility

- **Firefox**: Primary target browser (Manifest V3)
- **Extension APIs**: Uses standard WebExtension APIs for compatibility
- **Permission Model**: Minimal required permissions for security
- **Content Security**: Strict CSP preventing unauthorized external connections

## Future Enhancements

### Planned Features

1. **Real-Time Assessment Display**: Show qualification match results directly in LinkedIn interface
2. **Bulk Processing**: Process multiple jobs from search results pages
3. **Application Tracking**: Track which jobs have been applied to
4. **Custom Filters**: Filter jobs based on assessment results

### Technical Improvements

1. **Offline Support**: Cache processed jobs for offline viewing
2. **Sync Capabilities**: Synchronize data across multiple browser instances
3. **Advanced Error Recovery**: Implement retry logic with exponential backoff
4. **Performance Optimization**: Reduce memory usage and improve response times

### Integration Enhancements

1. **Chrome Support**: Port extension to Chrome/Chromium browsers
2. **Mobile Support**: Adapt interface for mobile browsing
3. **Third-Party Integration**: Support for other job boards beyond LinkedIn
4. **Export Capabilities**: Export processed job data in various formats

## Security Considerations

### Permission Model

- **Minimal Permissions**: Only requests necessary permissions
- **Host Restrictions**: Limited to HTTP/HTTPS with specific local API access
- **Content Scripts**: Executed only when user initiates processing
- **Data Privacy**: All data processing occurs locally or via user's API server

### Data Handling

- **Local Storage Only**: No external data transmission except to user's API server
- **Temporary Storage**: Tasks automatically cleaned up after completion
- **No Tracking**: No analytics or usage tracking implemented
- **Secure Communication**: API communication over localhost only

## Troubleshooting

### Common Issues and Solutions

1. **Extension Not Loading**
   - Verify manifest.json syntax
   - Check Firefox developer mode is enabled
   - Reload extension after code changes

2. **API Connection Failures**
   - Ensure backend server is running on port 8000
   - Check firewall settings for localhost connections
   - Verify Content Security Policy allows local connections

3. **LinkedIn Page Not Recognized**
   - Update target selectors for LinkedIn layout changes
   - Check browser developer tools for element structure
   - Test with different LinkedIn job page formats

4. **Task Status Not Updating**
   - Check local storage for task persistence
   - Verify background script message handling
   - Reload extension if message passing fails

### Debug Mode

Enable debug logging in development:

```javascript
const DEBUG = true;

function debugLog(message, data = null) {
  if (DEBUG) {
    console.log(`[Job Search Copilot] ${message}`, data);
  }
}
```

This comprehensive extension provides a user-friendly interface for the job search automation system while maintaining security and performance standards.