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
    const totalMatches = qualificationsArray.filter(item => item.match === 1 || item.match === true).length;
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
      const isMatch = item.match === 1 || item.match === true;
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

// Helpers to format timestamps coming from different sources (seconds, ms, ISO strings)
function parseFlexibleTimestamp(v) {
  if (v == null) return null;
  // numbers may be seconds or milliseconds
  if (typeof v === 'number') {
    // If it's clearly milliseconds (large), use directly
    if (v > 1e12) return new Date(v);
    // If it looks like a unix seconds timestamp (e.g. ~1e9), convert to ms
    if (v > 1e9) return new Date(v * 1000);
    // small numbers: treat as ms by default
    return new Date(v);
  }
  // strings: try ISO parse first, then numeric
  if (typeof v === 'string') {
    const n = Date.parse(v);
    if (!isNaN(n)) return new Date(n);
    const asNum = Number(v);
    if (!isNaN(asNum)) return parseFlexibleTimestamp(asNum);
    return null;
  }
  if (v instanceof Date) return v;
  return null;
}

function formatTimeForTask(task) {
  // Prefer last_assessed_at from task.data (like history.js), then fall back to completedAt/submittedAt
  const lastAssessed = task?.data?.last_assessed_at;
  if (lastAssessed) {
    const ts = parseFlexibleTimestamp(lastAssessed * (lastAssessed > 1e12 ? 1 : 1000));
    if (ts) return ts.toLocaleString();
  }
  // Fallbacks
  const possibleCompleted = task.completedAt || task?.data?.completed_at || task?.data?.completedAt;
  const completedDate = parseFlexibleTimestamp(possibleCompleted);
  if (completedDate) return completedDate.toLocaleString();
  const possibleSubmitted = task.submittedAt || task?.data?.submitted_at || task?.data?.submittedAt;
  const submittedDate = parseFlexibleTimestamp(possibleSubmitted);
  if (submittedDate) return submittedDate.toLocaleString();
  return '';
}

function renderJob(task) {
  const jobRow = document.createElement('div');
  jobRow.className = 'job-row';
  jobRow.id = task.id;

  const staleQuarantine = task?.data?.stale_quarantine === true;
  const isFailed = (task?.data?.failed === true || task.status === 'error') && !staleQuarantine;
  if (isFailed) {
    jobRow.classList.add('job-failed');
  }

  const title = task.data?.job_title || (task.status === 'completed' ? 'Untitled' : 'Processing...');
  const company = task.data?.job_company || '';
  const location = task.data?.job_location || '';
  const displayTitle = company ? `${title} at ${company}` : title;

  const isAnalyzing = task?.data?.assessed === false && !isFailed; // don't show analyzing if failed
  const showFractions = task?.data?.assessed === true && !isFailed; // hide fractions if failed
  const analyzingTagHtml = isAnalyzing
    ? '<span class="analyzing-tag" title="Assessment in progress" style="margin-right:8px; padding:2px 6px; border-radius:10px; background:#f5f5f5; color:#666; font-size:12px;">Analyzing…</span>'
    : '';
    const failedReason = task?.data?.quarantine_reason || task?.data?.failed_reason || 'Assessment failed';
    const failedTagHtml = isFailed
      ? `<span class="failed-tag" data-failed-reason="${encodeURIComponent(failedReason)}" style="margin-right:8px; padding:2px 6px; border-radius:10px; background:#ffe5e5; color:#b30000; font-size:12px; cursor:pointer;">Failed</span>`
      : '';

  const fr = computeFractionsFromTaskData(task.data || {});
  const reqClass = getFractionClass(fr.req.matched, fr.req.total);
  const addClass = getFractionClass(fr.add.matched, fr.add.total);
  const fractionsHtml = showFractions
    ? `
        <div class="row-fractions">
          <span class="fraction fraction-req ${reqClass}" title="Required matched/total">Req: (${fr.req.matched}/${fr.req.total})</span>
          <span class="fraction fraction-add ${addClass}" title="Additional matched/total">Add: (${fr.add.matched}/${fr.add.total})</span>
        </div>
      `
    : '';

  const whenText = formatTimeForTask(task);
  jobRow.innerHTML = `
    <div class="row-header">
      <div class="row-title">${displayTitle}</div>
      <div class="row-right">
        ${fractionsHtml}
        ${analyzingTagHtml}
        ${failedTagHtml}
        <span class="status-dot status-${task.status}" title="${task.status}"></span>
        <div class="row-location">${location || 'N/A'}</div>
      </div>
    </div>
    <div class="row-submeta">${whenText}</div>
    <div class="details-container"></div>
  `;

  // Attach popup for failed reason
  if (isFailed || staleQuarantine) {
    const failedEl = jobRow.querySelector('.failed-tag');
    if (failedEl) {
  const popupId = `${jobRow.id}-failed-popup`;
  let existing = document.getElementById(popupId);
  if (existing) existing.remove();
  const popup = document.createElement('div');
  popup.id = popupId;
  popup.className = 'failed-popup';
  popup.style.display = 'none';
  popup.style.position = 'absolute';
  popup.style.zIndex = '9999';
  popup.style.maxWidth = '360px';
  popup.style.background = '#fff';
  popup.style.border = '1px solid #e0b4b4';
  popup.style.boxShadow = '0 4px 14px rgba(0,0,0,0.2)';
  popup.style.padding = '12px 14px';
  popup.style.fontSize = '12px';
  popup.style.lineHeight = '1.4';
  popup.style.borderRadius = '6px';
  popup.style.pointerEvents = 'auto';
  popup.style.transition = 'opacity 0.12s ease';
      const reasonDecoded = decodeURIComponent(failedEl.getAttribute('data-failed-reason'));
  const headingColor = isFailed ? '#b30000' : '#036';
  const headingText = isFailed ? 'Failure Reason' : 'Previous Failure';
  popup.innerHTML = `<strong style="color:#b30000;">Failure Reason</strong><br>${reasonDecoded}<div style="margin-top:8px; text-align:right;"><button class="retry-btn" style="background:#b30000; color:#fff; padding:4px 8px; border:none; border-radius:4px; cursor:pointer;">Retry</button></div>`;
      document.body.appendChild(popup);

      function positionPopup() {
        const rect = failedEl.getBoundingClientRect();
        const scrollY = window.scrollY || document.documentElement.scrollTop;
        const scrollX = window.scrollX || document.documentElement.scrollLeft;
        const top = rect.top + scrollY + rect.height + 6; // below badge
        let left = rect.left + scrollX;
        // If going off right edge, shift left
        const popupWidth = Math.min(360, window.innerWidth - 20);
        popup.style.width = popupWidth + 'px';
        if (left + popupWidth > scrollX + window.innerWidth - 10) {
          left = scrollX + window.innerWidth - popupWidth - 10;
        }
        // If near bottom viewport, show above
        if (top + 200 > scrollY + window.innerHeight) {
          popup.style.top = (rect.top + scrollY - 10 - 180) + 'px';
        } else {
          popup.style.top = top + 'px';
        }
        popup.style.left = left + 'px';
      }

      failedEl.addEventListener('click', (e) => {
        e.stopPropagation();
        if (popup.style.display === 'none') {
          positionPopup();
          popup.style.opacity = '0';
          popup.style.display = 'block';
          requestAnimationFrame(() => { popup.style.opacity = '1'; });
        } else {
          popup.style.display = 'none';
        }
      });
      window.addEventListener('resize', () => { if (popup.style.display === 'block') positionPopup(); });
      window.addEventListener('scroll', () => { if (popup.style.display === 'block') positionPopup(); }, true);
      document.addEventListener('click', (e) => {
        if (!popup.contains(e.target) && e.target !== failedEl) {
          popup.style.display = 'none';
        }
      });
  const retryBtn = popup.querySelector('.retry-btn');
  if (retryBtn && task?.data?.job_id && isFailed) {
        retryBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          retryBtn.disabled = true;
          retryBtn.textContent = 'Retrying...';
          try {
            const resp = await regenerateAssessment(task.data.job_id);
            if (resp.status === 'success') {
              // Reset failed state locally to resume polling
              task.status = 'pending';
              task.data.failed = false;
              task.data.failed_reason = null;
              task.data.assessed = false;
              await browser.storage.local.set({ [task.id]: task });
              popup.style.display = 'none';
            } else {
              retryBtn.textContent = 'Failed';
            }
          } catch (err) {
            console.error('Retry failed', err);
            retryBtn.textContent = 'Error';
            setTimeout(() => { retryBtn.textContent = 'Retry'; retryBtn.disabled = false; }, 3000);
          } finally {
            retryBtn.disabled = false;
          }
        });
      }
    }
  }

  if (isAnalyzing) {
    jobRow.style.opacity = '0.6';
  } else if (isFailed) {
    jobRow.style.opacity = '0.8';
  }

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
              if (resp.status === 'success') {
                // Poll until assessed
                const start = Date.now();
                const timeoutMs = 120000; // 2 minutes
                const sleep = (ms) => new Promise(r => setTimeout(r, ms));
                let snapshot = null;
                while (Date.now() - start < timeoutMs) {
                  snapshot = await getJobSnapshot(task.data.job_id);
                  if (snapshot && snapshot.assessed) break;
                  await sleep(3000);
                }
                if (snapshot) {
                  task.data = { ...task.data, ...snapshot };
                }
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

// --- Background polling to resolve stuck "Processing..." ---
let pollTimer = null;
const POLL_INTERVAL_MS = 15000; // 15s
const MAX_PARALLEL_POLLS = 5;

async function getJobSnapshot(jobId) {
  try {
    const resp = await fetch(`http://127.0.0.1:8000/job/${encodeURIComponent(jobId)}`);
    if (!resp.ok) return null;
    const body = await resp.json();
    if (body?.status !== 'success' || !body.data) return null;
    // If backend says failed, return snapshot that marks error state to stop further polling
    if (body.data.failed === true) {
      return { ...body.data, assessed: false, failed: true };
    }
    return body.data;
  } catch (e) {
    console.warn('getJobSnapshot failed for', jobId, e);
    return null;
  }
}

async function pollIncompleteTasks() {
  const all = await browser.storage.local.get(null);
  const tasks = Object.values(all);
  const pending = tasks.filter(t => {
    if (!t || !t?.data?.job_id) return false;
    if (t?.data?.failed === true || t.status === 'error') return false;
    const assessed = t?.data?.assessed === true;
    return t.status !== 'completed' || !assessed;
  });
  if (pending.length === 0) return;

  let index = 0;
  const workers = Array.from({ length: Math.min(MAX_PARALLEL_POLLS, pending.length) }, async () => {
    while (index < pending.length) {
      const i = index++;
      const task = pending[i];
      const jobId = task.data.job_id;
      const snap = await getJobSnapshot(jobId);
      if (!snap) continue;

      const updated = { ...task, data: { ...task.data, ...snap } };
      if (snap.failed === true) {
        updated.status = 'error';
        updated.error = 'Assessment failed';
        await browser.storage.local.set({ [updated.id]: updated });
        continue; // do not mark completed, and skip further processing
      }

      if (snap.assessed === true) {
        updated.status = 'completed';
        updated.completedAt = new Date().toISOString();
      }
      await browser.storage.local.set({ [updated.id]: updated });
    }
  });
  await Promise.all(workers);
}

function startPolling() {
  if (pollTimer) return; // already running
  // Initial quick poll, then interval
  pollIncompleteTasks().catch(() => {});
  pollTimer = setInterval(() => {
    pollIncompleteTasks().catch(() => {});
  }, POLL_INTERVAL_MS);
}

// Kick off polling when the page script loads
startPolling();

// Optionally expose a manual function to mark failure and persist
async function markTaskFailed(taskId, reason='Assessment failed') {
  const all = await browser.storage.local.get(taskId);
  const task = all[taskId];
  if (!task) return;
  const updated = { ...task, status: 'error', data: { ...task.data, failed: true, failed_reason: reason, quarantine_reason: reason } };
  await browser.storage.local.set({ [taskId]: updated });
}
