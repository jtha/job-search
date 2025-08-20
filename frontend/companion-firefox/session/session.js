// Session page script (migrated from History)
const jobListContainer = document.getElementById('job-list-container');
let clearSessionBtn = document.getElementById('clear-session-btn');

// Ensure both buttons are in a flex container for alignment
let actionBtnContainer = document.getElementById('action-btn-container');
if (!actionBtnContainer) {
  actionBtnContainer = document.createElement('div');
  actionBtnContainer.id = 'action-btn-container';
  actionBtnContainer.style.display = 'flex';
  actionBtnContainer.style.gap = '12px';
  actionBtnContainer.style.marginLeft = 'auto';
  // Insert into header
  const header = document.querySelector('header');
  if (header) {
    header.appendChild(actionBtnContainer);
  }
}

// Move clearSessionBtn into container if not already
if (clearSessionBtn && clearSessionBtn.parentNode !== actionBtnContainer) {
  clearSessionBtn.classList.add('action-btn');
  actionBtnContainer.appendChild(clearSessionBtn);
}

// Add Hide Applied button to the right of clearSessionBtn
let hideAppliedBtn = document.getElementById('hide-applied-btn');
if (!hideAppliedBtn) {
  hideAppliedBtn = document.createElement('button');
  hideAppliedBtn.id = 'hide-applied-btn';
  hideAppliedBtn.className = 'action-btn';
  hideAppliedBtn.textContent = 'Hide Applied';
  actionBtnContainer.appendChild(hideAppliedBtn);
}

// Add Decent Only button to the right of Hide Applied
let decentOnlyBtn = document.getElementById('decent-only-btn');
if (!decentOnlyBtn) {
  decentOnlyBtn = document.createElement('button');
  decentOnlyBtn.id = 'decent-only-btn';
  decentOnlyBtn.className = 'action-btn';
  decentOnlyBtn.textContent = 'Show Good Leads';
  actionBtnContainer.appendChild(decentOnlyBtn);
}

const state = {
  hideApplied: false,
  decentOnly: false,
};

if (hideAppliedBtn) {
  hideAppliedBtn.addEventListener('click', () => {
    state.hideApplied = !state.hideApplied;
    hideAppliedBtn.textContent = state.hideApplied ? 'Show Applied' : 'Hide Applied';
    renderAllJobs();
  });
}

if (decentOnlyBtn) {
  decentOnlyBtn.addEventListener('click', () => {
    state.decentOnly = !state.decentOnly;
    decentOnlyBtn.textContent = state.decentOnly ? 'Show All Leads' : 'Show Good Leads';
    renderAllJobs();
  });
}

function createQualificationTable(title, qualificationsArray, headers) {
  if (!qualificationsArray || qualificationsArray.length === 0) return '';
  let matchFraction = '';
  if (headers.length === 3) {
    const totalMatches = qualificationsArray.filter(item => item.match === 1).length;
    const totalRequirements = qualificationsArray.length;
    matchFraction = `<span class="match-fraction">(${totalMatches}/${totalRequirements})</span>`;
  }
  let tableHtml = `<h4><span>${title}</span>${matchFraction}</h4>`;
  tableHtml += `<table class="qualification-table" data-columns="${headers.length}"><thead><tr>`;
  headers.forEach(header => { tableHtml += `<th>${header}</th>`; });
  tableHtml += '</tr></thead><tbody>';
  for (const item of qualificationsArray) {
    tableHtml += '<tr>';
    if (headers.includes('Requirement')) tableHtml += `<td>${item.requirement || 'N/A'}</td>`;
    if (headers.includes('Match')) {
      const isMatch = item.match === 1;
      const matchText = isMatch ? 'Yes' : 'No';
      const matchClass = isMatch ? 'match-yes' : 'match-no';
      tableHtml += `<td class="${matchClass}">${matchText}</td>`;
    }
    if (headers.includes('Match Reason')) tableHtml += `<td>${item.match_reason || 'N/A'}</td>`;
    tableHtml += '</tr>';
  }
  tableHtml += '</tbody></table>';
  return tableHtml;
}

async function syncAppliedStatusFromAPI(tasks) {
  // Check if any tasks are missing the job_applied field and sync from API if needed
  const tasksNeedingSync = tasks.filter(task => 
    task?.data?.job_id && 
    task?.data?.job_applied === undefined
  );
  
  if (tasksNeedingSync.length === 0) return;
  
  console.log(`Syncing applied status for ${tasksNeedingSync.length} tasks...`);
  
  for (const task of tasksNeedingSync) {
    try {
      // Fetch recent job data that includes applied status
      const response = await fetch(`http://127.0.0.1:8000/jobs_recent?days_back=30&limit=300`);
      if (!response.ok) continue;
      
      const recentJobs = await response.json();
      const matchingJob = recentJobs.find(job => job.job_id === task.data.job_id);
      
      if (matchingJob) {
        task.data.job_applied = matchingJob.job_applied || 0;
        await browser.storage.local.set({ [task.id]: task });
        console.log(`Synced applied status for job ${task.data.job_id}: ${task.data.job_applied}`);
      } else {
        // Default to not applied if not found in recent jobs
        task.data.job_applied = 0;
        await browser.storage.local.set({ [task.id]: task });
      }
    } catch (err) {
      console.error(`Failed to sync applied status for job ${task.data.job_id}:`, err);
      // Default to not applied on error
      task.data.job_applied = 0;
      await browser.storage.local.set({ [task.id]: task });
    }
  }
}

async function regenerateAssessment(jobId) {
  const endpoint = 'http://127.0.0.1:8000/regenerate_job_assessment';
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_id: jobId })
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `API Error: ${response.status}`);
  }
  return response.json();
}

async function markApplied(jobId) {
  const endpoint = 'http://127.0.0.1:8000/update_job_applied';
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_id: jobId })
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `API Error: ${response.status}`);
  }
  return response.json();
}

async function unmarkApplied(jobId) {
  const endpoint = 'http://127.0.0.1:8000/update_job_unapplied';
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_id: jobId })
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `API Error: ${response.status}`);
  }
  return response.json();
}

function renderJobDetails(data) {
  if (!data) return '<p>No details available.</p>';
  const uniquePrefix = `details-${data.task_id}-${data.job_id || 'no-job-id'}`;
  const descriptionId = `${uniquePrefix}-desc`;
  const copyBtnId = `${uniquePrefix}-copy-btn`;
  const regenBtnId = `${uniquePrefix}-regen-btn`;
  const regenStatusId = `${uniquePrefix}-regen-status`;
  const appliedBtnId = `${uniquePrefix}-applied-btn`;
  let description = data.job_description || 'Not found.';
  const keyMappings = { job_company: 'Company', job_title: 'Title', job_salary: 'Salary', job_location: 'Location', job_url_direct: 'Direct Link' };
  let detailsHtml = '<table class="job-data-table">';
  for (const key in keyMappings) {
    if (Object.prototype.hasOwnProperty.call(data, key)) {
      let value = data[key] || 'N/A';
      if (key === 'job_url_direct' && value !== 'N/A') {
        const jobId = data.job_id || '';
        const linkText = `View Job ${jobId}`.trim();
        value = `<a href="${value}" target="_blank">${linkText}</a>`;
      }
      detailsHtml += `<tr><td>${keyMappings[key]}</td><td>${value}</td></tr>`;
    }
  }
  detailsHtml += '</table>';
  const isApplied = data.job_applied === 1 || data.job_applied === true;
  detailsHtml += `
    <div class="details-action-bar">
      <button id="${regenBtnId}" class="regen-button" title="Regenerate assessment">Regenerate Assessment</button>
      <span id="${regenStatusId}" class="regen-status"></span>
      <button id="${appliedBtnId}" class="regen-button applied-button" style="margin-left:auto" title="Toggle applied status">${isApplied ? 'Unmark Applied' : 'Applied to Job'}</button>
    </div>
    <h4 class="description-header"><span>Description</span><button id="${copyBtnId}" class="copy-button" title="Copy description">Copy</button></h4>
    <pre id="${descriptionId}" class="job-description">${description}</pre>
  `;
  const threeColumn = ['Requirement', 'Match', 'Match Reason'];
  const oneColumn = ['Requirement'];
  detailsHtml += createQualificationTable('Required Qualifications', data.required_qualifications, threeColumn);
  detailsHtml += createQualificationTable('Additional Qualifications', data.additional_qualifications, threeColumn);
  detailsHtml += createQualificationTable('Evaluated Qualifications', data.evaluated_qualifications, oneColumn);
  return detailsHtml;
}

function computeFractionsFromTaskData(data) {
  const reqArr = Array.isArray(data?.required_qualifications) ? data.required_qualifications : [];
  const addArr = Array.isArray(data?.additional_qualifications) ? data.additional_qualifications : [];
  const reqMatched = reqArr.filter(i => i.match === 1 || i.match === true).length;
  const addMatched = addArr.filter(i => i.match === 1 || i.match === true).length;
  return {
    req: { matched: reqMatched, total: reqArr.length },
    add: { matched: addMatched, total: addArr.length }
  };
}

function isDecentLeadTask(task) {
  const fr = computeFractionsFromTaskData(task?.data || {});
  if (!fr.req.total || (fr.req.matched / fr.req.total) < 0.5) return false;
  if (fr.add.total > 0 && (fr.add.matched / fr.add.total) < 0.5) return false;
  return true;
}

function getFractionClass(matched, total) {
  if (!total || total <= 0) return 'fraction-empty';
  const r = matched / total;
  if (r >= 0.75) return 'fraction-good';
  if (r >= 0.5) return 'fraction-ok';
  return 'fraction-bad';
}

function updateFractionEl(el, label, matched, total) {
  if (!el) return;
  el.textContent = `${label}: (${matched}/${total})`;
  el.classList.remove('fraction-good','fraction-ok','fraction-bad','fraction-empty');
  el.classList.add(getFractionClass(matched, total));
}

function renderJob(task) {
  const jobRow = document.createElement('div');
  jobRow.className = 'job-row';
  jobRow.id = task.id;

  const title = task.data?.job_title || (task.status === 'completed' ? 'Untitled' : 'Processing...');
  const company = task.data?.job_company || '';
  const location = task.data?.job_location || '';
  const displayTitle = company ? `${title} at ${company}` : title;

  const when = task.completedAt || task.submittedAt || '';
  const whenText = when ? new Date(when).toLocaleString() : '';

  const fr = computeFractionsFromTaskData(task.data || {});
  const reqClass = getFractionClass(fr.req.matched, fr.req.total);
  const addClass = getFractionClass(fr.add.matched, fr.add.total);

  jobRow.innerHTML = `
    <div class="row-header">
      <div class="row-title">${displayTitle}</div>
      <div class="row-right">
        <div class="row-fractions">
          <span class="fraction fraction-req ${reqClass}" title="Required matched/total">Req: (${fr.req.matched}/${fr.req.total})</span>
          <span class="fraction fraction-add ${addClass}" title="Additional matched/total">Add: (${fr.add.matched}/${fr.add.total})</span>
        </div>
  <span class="status-dot status-${task.status}" title="${task.status}"></span>
        <div class="row-location">${location || 'N/A'}</div>
      </div>
    </div>
    <div class="row-submeta">${whenText}</div>
    <div class="details-container"></div>
  `;

  const header = jobRow.querySelector('.row-header');
  const detailsContainer = jobRow.querySelector('.details-container');

  if (task?.data?.job_applied === 1 || task?.data?.job_applied === true) {
    jobRow.classList.add('applied');
  }

  if (task.status === 'completed') {
    jobRow.addEventListener('click', (e) => {
      // Don't expand if clicking on interactive elements
      if (e.target.tagName === 'BUTTON' || e.target.tagName === 'A' || e.target.closest('button') || e.target.closest('a')) {
        return;
      }
      
      const isVisible = detailsContainer.style.display === 'block';
      
      // If the row is expanded, only allow collapse when clicking on header area
      if (isVisible) {
        // Check if the click was on the header or its children
        const clickedHeader = e.target === header || header.contains(e.target);
        if (!clickedHeader) {
          return; // Don't collapse if clicked outside header area
        }
        
        detailsContainer.style.display = 'none';
        jobRow.classList.remove('expanded');
        return;
      }
      
      // If not expanded, clicking anywhere in the row expands it
      if (!detailsContainer.innerHTML) {
        task.data.task_id = task.id;
        detailsContainer.innerHTML = renderJobDetails(task.data);
        const uniquePrefix = `details-${task.id}-${task.data.job_id || 'no-job-id'}`;
        const copyBtn = document.getElementById(`${uniquePrefix}-copy-btn`);
        const descriptionEl = document.getElementById(`${uniquePrefix}-desc`);
        const regenBtn = document.getElementById(`${uniquePrefix}-regen-btn`);
        const regenStatusEl = document.getElementById(`${uniquePrefix}-regen-status`);
        const appliedBtn = document.getElementById(`${uniquePrefix}-applied-btn`);

        if (copyBtn && descriptionEl) {
          copyBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            navigator.clipboard.writeText(descriptionEl.textContent).then(() => {
              copyBtn.textContent = 'Copied!';
              setTimeout(() => { copyBtn.textContent = 'Copy'; }, 2000);
            }).catch(err => {
              console.error('Failed to copy text: ', err);
              copyBtn.textContent = 'Error!';
            });
          });
        }

        if (regenBtn && task.data?.job_id) {
          regenBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            if (regenBtn.disabled) return;
            regenBtn.disabled = true;
            const originalText = regenBtn.textContent;
            regenBtn.textContent = 'Regenerating...';
            regenStatusEl.textContent = '';
            try {
              const resp = await regenerateAssessment(task.data.job_id);
              if (resp.status === 'success' && resp.data) {
                task.data = resp.data;
                task.data.task_id = task.id;
                await browser.storage.local.set({ [task.id]: task });
                detailsContainer.innerHTML = renderJobDetails(task.data);
                const newCopyBtn = document.getElementById(`${uniquePrefix}-copy-btn`);
                const newDescriptionEl = document.getElementById(`${uniquePrefix}-desc`);
                const newRegenBtn = document.getElementById(`${uniquePrefix}-regen-btn`);
                const newRegenStatusEl = document.getElementById(`${uniquePrefix}-regen-status`);
                const newAppliedBtn = document.getElementById(`${uniquePrefix}-applied-btn`);
                if (newCopyBtn && newDescriptionEl) {
                  newCopyBtn.addEventListener('click', (e2) => {
                    e2.stopPropagation();
                    navigator.clipboard.writeText(newDescriptionEl.textContent).then(() => {
                      newCopyBtn.textContent = 'Copied!';
                      setTimeout(() => { newCopyBtn.textContent = 'Copy'; }, 2000);
                    }).catch(err => {
                      console.error('Failed to copy text: ', err);
                      newCopyBtn.textContent = 'Error!';
                    });
                  });
                }
                if (newRegenBtn) {
                  newRegenBtn.addEventListener('click', (e3) => {
                    e3.stopPropagation();
                  });
                }
                if (newAppliedBtn && task.data?.job_id) {
                  newAppliedBtn.addEventListener('click', async (e4) => {
                    e4.stopPropagation();
                    if (newAppliedBtn.disabled) return;
                    const originalText2 = newAppliedBtn.textContent;
                    const currentlyApplied = task.data.job_applied === 1 || task.data.job_applied === true;
                    newAppliedBtn.disabled = true;
                    newAppliedBtn.textContent = currentlyApplied ? 'Unmarking...' : 'Marking...';
                    try {
                      if (currentlyApplied) {
                        await unmarkApplied(task.data.job_id);
                        task.data.job_applied = 0;
                        newAppliedBtn.textContent = 'Applied to Job';
                        jobRow.classList.remove('applied');
                      } else {
                        await markApplied(task.data.job_id);
                        task.data.job_applied = 1;
                        newAppliedBtn.textContent = 'Unmark Applied';
                        jobRow.classList.add('applied');
                      }
                      await browser.storage.local.set({ [task.id]: task });
                    } catch (err) {
                      console.error('Toggle applied failed', err);
                      newAppliedBtn.textContent = 'Error';
                      setTimeout(() => { newAppliedBtn.textContent = originalText2; newAppliedBtn.disabled = false; }, 3000);
                    } finally {
                      newAppliedBtn.disabled = false;
                    }
                  });
                }
                const updatedFr = computeFractionsFromTaskData(task.data);
                const reqEl = jobRow.querySelector('.fraction-req');
                const addEl = jobRow.querySelector('.fraction-add');
                updateFractionEl(reqEl, 'Req', updatedFr.req.matched, updatedFr.req.total);
                updateFractionEl(addEl, 'Add', updatedFr.add.matched, updatedFr.add.total);
                regenStatusEl.textContent = 'Updated';
              } else {
                regenStatusEl.textContent = 'Failed';
              }
            } catch (err) {
              console.error('Regenerate failed', err);
              regenStatusEl.textContent = 'Error';
            } finally {
              regenBtn.disabled = false;
              regenBtn.textContent = originalText;
              setTimeout(() => { regenStatusEl.textContent = ''; }, 4000);
            }
          });
        }

        if (appliedBtn && task.data?.job_id) {
          appliedBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            if (appliedBtn.disabled) return;
            const originalText = appliedBtn.textContent;
            const currentlyApplied = task.data.job_applied === 1 || task.data.job_applied === true;
            appliedBtn.disabled = true;
            appliedBtn.textContent = currentlyApplied ? 'Unmarking...' : 'Marking...';
            try {
              if (currentlyApplied) {
                await unmarkApplied(task.data.job_id);
                task.data.job_applied = 0;
                appliedBtn.textContent = 'Applied to Job';
                jobRow.classList.remove('applied');
              } else {
                await markApplied(task.data.job_id);
                task.data.job_applied = 1;
                appliedBtn.textContent = 'Unmark Applied';
                jobRow.classList.add('applied');
              }
              await browser.storage.local.set({ [task.id]: task });
            } catch (err) {
              console.error('Toggle applied failed', err);
              appliedBtn.textContent = 'Error';
              setTimeout(() => { appliedBtn.textContent = originalText; appliedBtn.disabled = false; }, 3000);
            } finally {
              appliedBtn.disabled = false;
            }
          });
        }
      }
      detailsContainer.style.display = 'block';
      jobRow.classList.add('expanded');
    });
  }

  return jobRow;
}

async function renderAllJobs() {
  const allTasks = await browser.storage.local.get(null);
  jobListContainer.innerHTML = '';

  let sortedTasks = Object.values(allTasks).sort((a, b) => new Date(b.submittedAt) - new Date(a.submittedAt));
  
  // For backwards compatibility: check if tasks have job_applied field and sync with API if needed
  await syncAppliedStatusFromAPI(sortedTasks);
  if (state.hideApplied) {
    sortedTasks = sortedTasks.filter(task => !(task?.data?.job_applied === 1 || task?.data?.job_applied === true));
  }
  if (state.decentOnly) {
    sortedTasks = sortedTasks.filter(task => isDecentLeadTask(task));
  }

  if (sortedTasks.length === 0) {
    jobListContainer.innerHTML = '<p>No jobs have been processed yet.</p>';
    return;
  }

  for (const task of sortedTasks) {
    const jobElement = renderJob(task);
    jobListContainer.appendChild(jobElement);
  }
}

browser.storage.onChanged.addListener((changes, area) => {
  if (area === 'local') {
    renderAllJobs();
  }
});

clearSessionBtn.addEventListener('click', async () => {
  if (confirm('Are you sure you want to delete all session job data? This cannot be undone.')) {
    await browser.storage.local.clear();
    renderAllJobs();
  }
});

document.addEventListener('DOMContentLoaded', renderAllJobs);
