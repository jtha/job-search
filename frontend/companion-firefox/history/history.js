// History page script (migrated from Recent)

const container = document.getElementById('history-list-container');

const refreshBtn = document.getElementById('refresh-btn');
const daysBackInput = document.getElementById('days-back');

// Ensure controls container exists and contains the refresh button, hideAppliedBtn, and daysBackInput
let controls = document.querySelector('.controls');
if (!controls) {
  controls = document.createElement('div');
  controls.className = 'controls';
  // insert header's right side: find header and append controls
  const header = document.querySelector('header');
  if (header) header.appendChild(controls);
}

// Move refreshBtn and daysBackInput into controls if not already
if (refreshBtn && refreshBtn.parentNode !== controls) {
  refreshBtn.classList.add('action-btn');
  controls.appendChild(refreshBtn);
}

// daysBackInput may be an input element; ensure it has a wrapper or move it
if (daysBackInput && daysBackInput.parentNode !== controls) {
  controls.appendChild(daysBackInput);
}

// Ensure both buttons have .action-btn for consistent sizing
refreshBtn.classList.add('action-btn');

// Add toggle button for hiding applied jobs
let hideAppliedBtn = document.getElementById('hide-applied-btn');
if (!hideAppliedBtn) {
  hideAppliedBtn = document.createElement('button');
  hideAppliedBtn.id = 'hide-applied-btn';
  hideAppliedBtn.className = 'action-btn';
  hideAppliedBtn.textContent = 'Hide Applied';
  // Insert hideAppliedBtn after refreshBtn inside controls
  controls.insertBefore(hideAppliedBtn, refreshBtn.nextSibling || null);
}

// Add toggle button for filtering decent leads only
let decentOnlyBtn = document.getElementById('decent-only-btn');
if (!decentOnlyBtn) {
  decentOnlyBtn = document.createElement('button');
  decentOnlyBtn.id = 'decent-only-btn';
  decentOnlyBtn.className = 'action-btn';
  decentOnlyBtn.textContent = 'Show Good Leads';
  // Place after Hide Applied if present, else at end of controls
  if (hideAppliedBtn && hideAppliedBtn.parentNode === controls) {
    controls.insertBefore(decentOnlyBtn, hideAppliedBtn.nextSibling || null);
  } else {
    controls.appendChild(decentOnlyBtn);
  }
}

const state = {
  skillsByJob: null,
  appliedByJob: new Map(),
  // cache skills per daysBack to avoid refetching when unchanged
  skillsCacheByDays: new Map(),
  hideApplied: false,
  decentOnly: false,
};

if (hideAppliedBtn) {
  hideAppliedBtn.addEventListener('click', () => {
    state.hideApplied = !state.hideApplied;
    hideAppliedBtn.textContent = state.hideApplied ? 'Show Applied' : 'Hide Applied';
    loadHistory();
  });
}

if (decentOnlyBtn) {
  decentOnlyBtn.addEventListener('click', () => {
    state.decentOnly = !state.decentOnly;
    decentOnlyBtn.textContent = state.decentOnly ? 'Show All Leads' : 'Show Good Leads';
    loadHistory();
  });
}

async function fetchHistory(daysBack = 3, limit = 200) {
  const endpoint = `http://127.0.0.1:8000/jobs_recent?days_back=${encodeURIComponent(daysBack)}&limit=${encodeURIComponent(limit)}`;
  const response = await fetch(endpoint, { method: 'GET' });
  if (!response.ok) {
    let msg = `API Error: ${response.status}`;
    try { const d = await response.json(); if (d?.detail) msg = d.detail; } catch {}
    throw new Error(msg);
  }
  return response.json();
}

async function fetchAllSkillsOnce(daysBack = 5, limit = 300) {
  // cache by daysBack so changing the filter refetches
  const cacheKey = `${daysBack}:${limit}`;
  if (state.skillsCacheByDays.has(cacheKey)) {
    const cached = state.skillsCacheByDays.get(cacheKey);
    state.skillsByJob = cached; // keep compatibility
    return cached;
  }
  const endpoint = `http://127.0.0.1:8000/job_skills_recent?days_back=${encodeURIComponent(daysBack)}&limit=${encodeURIComponent(limit)}`;
  const response = await fetch(endpoint, { method: 'GET' });
  if (!response.ok) {
    let msg = `API Error: ${response.status}`;
    try { const d = await response.json(); if (d?.detail) msg = d.detail; } catch {}
    throw new Error(msg);
  }
  const rows = await response.json();
  const map = new Map();
  for (const r of rows || []) {
    const list = map.get(r.job_id) || [];
    list.push(r);
    map.set(r.job_id, list);
  }
  state.skillsByJob = map;
  state.skillsCacheByDays.set(cacheKey, map);
  return map;
}

function mapSkillsToSections(skills) {
  const required = [];
  const additional = [];
  const evaluated = [];
  for (const i of skills || []) {
    const entry = {
      requirement: i.job_skills_atomic_string,
      match: i.job_skills_match,
      match_reason: i.job_skills_match_reasoning,
    };
    if (i.job_skills_type === 'required_qualification') required.push(entry);
    else if (i.job_skills_type === 'additional_qualification') additional.push(entry);
    else if (i.job_skills_type === 'evaluated_qualification') evaluated.push({ requirement: i.job_skills_atomic_string });
  }
  return { required, additional, evaluated };
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
  const uniquePrefix = `details-${data.job_id}-${Date.now()}`;
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
  const isApplied = state.appliedByJob.get(data.job_id) === true;
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
  return { html: detailsHtml, ids: { copyBtnId, descriptionId, regenBtnId, regenStatusId, appliedBtnId } };
}

function computeFractions(jobSkills) {
  const req = jobSkills.filter(s => s.job_skills_type === 'required_qualification');
  const add = jobSkills.filter(s => s.job_skills_type === 'additional_qualification');
  const reqMatched = req.filter(s => s.job_skills_match === 1 || s.job_skills_match === true).length;
  const addMatched = add.filter(s => s.job_skills_match === 1 || s.job_skills_match === true).length;
  return {
    req: { matched: reqMatched, total: req.length },
    add: { matched: addMatched, total: add.length },
  };
}

function isDecentLead(jobId, skillsMap) {
  const jobSkills = (skillsMap && skillsMap.get(jobId)) || [];
  const fr = computeFractions(jobSkills);
  // Required fraction must be >= 0.5 and must exist
  if (!fr.req.total || (fr.req.matched / fr.req.total) < 0.5) return false;
  // Additional fraction must be >= 0.5 only if there are additional quals
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

function renderJobRow(job, skillsMap) {
  const row = document.createElement('div');
  row.className = 'job-row';
  const title = job.job_title || 'Untitled';
  const company = job.job_company || '';
  const location = job.job_location || 'N/A';
  const displayTitle = company ? `${title} at ${company}` : title;

  const lastAssessedAt = job.last_assessed_at ? new Date(job.last_assessed_at * 1000) : null;
  const lastAssessedText = lastAssessedAt ? lastAssessedAt.toLocaleString() : '';

  const jobSkills = (skillsMap && skillsMap.get(job.job_id)) || [];
  const fr = computeFractions(jobSkills);

    const reqClass = getFractionClass(fr.req.matched, fr.req.total);
    const addClass = getFractionClass(fr.add.matched, fr.add.total);

    row.innerHTML = `
    <div class="row-header">
      <div class="row-title">${displayTitle}</div>
      <div class="row-right">
          <div class="row-fractions">
            <span class="fraction fraction-req ${reqClass}" title="Required matched/total">Req: (${fr.req.matched}/${fr.req.total})</span>
            <span class="fraction fraction-add ${addClass}" title="Additional matched/total">Add: (${fr.add.matched}/${fr.add.total})</span>
        </div>
        <div class="row-location">${location}</div>
      </div>
    </div>
    <div class="row-submeta">${lastAssessedText}</div>
    <div class="details-container"></div>
  `;

  const header = row.querySelector('.row-header');
  const detailsContainer = row.querySelector('.details-container');

  if (state.appliedByJob.get(job.job_id) === true) {
    row.classList.add('applied');
  }

  row.addEventListener('click', async (e) => {
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
      row.classList.remove('expanded');
      return;
    }
    
    // If not expanded, clicking anywhere in the row expands it
    if (!detailsContainer.innerHTML) {
      const currentDaysBack = Math.max(1, parseInt(daysBackInput.value || '5', 10));
      const skillsMap = await fetchAllSkillsOnce(currentDaysBack, 300);
      const jobSkills = skillsMap.get(job.job_id) || [];
        const sections = mapSkillsToSections(jobSkills);
        const data = {
          job_id: job.job_id,
          job_title: job.job_title,
          job_company: job.job_company,
          job_location: job.job_location,
          job_salary: job.job_salary,
          job_url: job.job_url,
          job_url_direct: job.job_url_direct,
          job_description: job.job_description,
          required_qualifications: sections.required,
          additional_qualifications: sections.additional,
          evaluated_qualifications: sections.evaluated,
        };
        const rendered = renderJobDetails(data);
        detailsContainer.innerHTML = rendered.html;

        const copyBtn = document.getElementById(rendered.ids.copyBtnId);
        const descriptionEl = document.getElementById(rendered.ids.descriptionId);
        const regenBtn = document.getElementById(rendered.ids.regenBtnId);
        const regenStatusEl = document.getElementById(rendered.ids.regenStatusId);
        const appliedBtn = document.getElementById(rendered.ids.appliedBtnId);

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

        if (regenBtn) {
          regenBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            if (regenBtn.disabled) return;
            const originalText = regenBtn.textContent;
            regenBtn.disabled = true;
            regenBtn.textContent = 'Regenerating...';
            regenStatusEl.textContent = '';
            try {
              const resp = await regenerateAssessment(job.job_id);
              if (resp.status === 'success' && resp.data) {
                // Invalidate cache and refetch recent skills
                state.skillsByJob = null;
                state.skillsCacheByDays.clear();
                const currentDaysBack2 = Math.max(1, parseInt(daysBackInput.value || '5', 10));
                await fetchAllSkillsOnce(currentDaysBack2, 300);
                const updatedSkills = state.skillsByJob.get(job.job_id) || [];
                const updatedSections = mapSkillsToSections(updatedSkills);
                const updatedData = {
                  ...resp.data,
                  required_qualifications: updatedSections.required,
                  additional_qualifications: updatedSections.additional,
                  evaluated_qualifications: updatedSections.evaluated,
                };
                const rerendered = renderJobDetails(updatedData);
                detailsContainer.innerHTML = rerendered.html;
                const copyBtn2 = document.getElementById(rerendered.ids.copyBtnId);
                const descriptionEl2 = document.getElementById(rerendered.ids.descriptionId);
                const regenBtn2 = document.getElementById(rerendered.ids.regenBtnId);
                const regenStatusEl2 = document.getElementById(rerendered.ids.regenStatusId);
                if (copyBtn2 && descriptionEl2) {
                  copyBtn2.addEventListener('click', (evt) => {
                    evt.stopPropagation();
                    navigator.clipboard.writeText(descriptionEl2.textContent).then(() => {
                      copyBtn2.textContent = 'Copied!';
                      setTimeout(() => { copyBtn2.textContent = 'Copy'; }, 2000);
                    });
                  });
                }
                if (regenBtn2) {
                  regenBtn2.addEventListener('click', (evt) => evt.stopPropagation());
                }

              const newFr = computeFractions(updatedSkills);
              const reqEl = row.querySelector('.fraction-req');
              const addEl = row.querySelector('.fraction-add');
              updateFractionEl(reqEl, 'Req', newFr.req.matched, newFr.req.total);
              updateFractionEl(addEl, 'Add', newFr.add.matched, newFr.add.total);
              } else {
                regenStatusEl.textContent = 'Error';
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

    if (appliedBtn) {
          appliedBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            if (appliedBtn.disabled) return;
    const originalText = appliedBtn.textContent;
    const currentlyApplied = state.appliedByJob.get(job.job_id) === true;
            appliedBtn.disabled = true;
            appliedBtn.textContent = currentlyApplied ? 'Unmarking...' : 'Marking...';
            try {
              if (currentlyApplied) {
                await unmarkApplied(job.job_id);
                state.appliedByJob.set(job.job_id, false);
                appliedBtn.textContent = 'Applied to Job';
        row.classList.remove('applied');
              } else {
                await markApplied(job.job_id);
                state.appliedByJob.set(job.job_id, true);
                appliedBtn.textContent = 'Unmark Applied';
        row.classList.add('applied');
              }
            } catch (err) {
              console.error('Toggle applied failed', err);
              appliedBtn.textContent = 'Error';
              setTimeout(() => { appliedBtn.textContent = originalText; }, 3000);
            } finally {
              appliedBtn.disabled = false;
            }
          });
        }
      }
      detailsContainer.style.display = 'block';
      row.classList.add('expanded');
  });

  return row;
}

async function loadHistory() {
  const daysBack = Math.max(1, parseInt(daysBackInput.value || '5', 10));
  try {
    container.innerHTML = '<p class="empty">Loading…</p>';
    const [data, skillsMap] = await Promise.all([
      fetchHistory(daysBack, 200),
      fetchAllSkillsOnce(daysBack, 300)
    ]);
    if (!Array.isArray(data) || data.length === 0) {
      container.innerHTML = '<p class="empty">No history found.</p>';
      return;
    }
    state.appliedByJob = new Map();
    for (const job of data) {
      if (job && job.job_id != null) {
        state.appliedByJob.set(job.job_id, job.job_applied === 1 || job.job_applied === true);
      }
    }
    container.innerHTML = '';
    let jobsToRender = data;
    if (state.hideApplied) {
      jobsToRender = jobsToRender.filter(job => !(job.job_applied === 1 || job.job_applied === true));
    }
    if (state.decentOnly) {
      jobsToRender = jobsToRender.filter(job => isDecentLead(job.job_id, skillsMap));
    }
    for (const job of jobsToRender) {
      container.appendChild(renderJobRow(job, skillsMap));
    }
  } catch (err) {
    console.error('Failed to load history', err);
    container.innerHTML = `<p class="empty">${err.message || 'Failed to load history.'}</p>`;
  }
}

refreshBtn.addEventListener('click', loadHistory);

document.addEventListener('DOMContentLoaded', loadHistory);