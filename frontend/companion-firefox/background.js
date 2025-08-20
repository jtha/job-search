// --- ADD THIS LISTENER BACK ---
// Listen for clicks on the browser action (the toolbar button)
// and toggle the sidebar's visibility. This is the persistent listener.
browser.action.onClicked.addListener(() => {
  browser.sidebarAction.toggle();
});


// --- ALL THE EXISTING WORKER LOGIC REMAINS THE SAME ---

// This function contains the scraping logic.
function scrapeTargetElement(selectors) {
  for (const selector of selectors) {
    const targetElement = document.querySelector(selector);
    if (targetElement) {
      return targetElement.outerHTML;
    }
  }
  return null;
}

// This function handles the long-running API call.
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

// The main processing logic for a single job task.
async function processJob(task) {
  try {
    task.status = 'processing';
    await browser.storage.local.set({ [task.id]: task });

    const targetSelectors = [
      'div.jobs-search__job-details--wrapper',
      'div.jobs-semantic-search-job-details-wrapper',
      'div.job-view-layout'
    ];
    // Find the tab by its URL, since the user might have navigated away.
    const [targetTab] = await browser.tabs.query({ url: task.url });
    if (!targetTab) throw new Error("Original tab not found. It may have been closed.");

    const results = await browser.scripting.executeScript({
      target: { tabId: targetTab.id },
      func: scrapeTargetElement,
      args: [targetSelectors]
    });

    const htmlContent = results[0].result;
    if (!htmlContent) throw new Error("Could not find target element on page.");

    const apiResponse = await callApi(htmlContent, task.url);

    task.status = 'completed';
    task.data = apiResponse.data;
    task.completedAt = new Date().toISOString();
    await browser.storage.local.set({ [task.id]: task });

  } catch (error) {
    console.error(`Failed to process task ${task.id}:`, error);
    task.status = 'error';
    task.error = error.message;
    await browser.storage.local.set({ [task.id]: task });
  }
}

// Listen for messages from the sidebar to start processing.
browser.runtime.onMessage.addListener((message) => {
  if (message.action === 'processJob') {
    processJob(message.task);
  }
});