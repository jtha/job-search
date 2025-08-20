// Dashboard page functionality

// Get DOM elements
const daysBackInput = document.getElementById('days-back');
const refreshBtn = document.getElementById('refresh-btn');
const totalAssessedEl = document.getElementById('total-assessed');
const totalFeasibleEl = document.getElementById('total-feasible');
const totalAppliedEl = document.getElementById('total-applied');
const totalFeasibleNotAppliedEl = document.getElementById('total-feasible-not-applied');
const loadingEl = document.getElementById('loading-state');
const errorEl = document.getElementById('error-state');

// API functions
async function fetchHistory(daysBack = 5, limit = 1000) {
  const endpoint = `http://127.0.0.1:8000/jobs_recent?days_back=${encodeURIComponent(daysBack)}&limit=${encodeURIComponent(limit)}`;
  const response = await fetch(endpoint, { method: 'GET' });
  if (!response.ok) {
    let msg = `API Error: ${response.status}`;
    try { 
      const d = await response.json(); 
      if (d?.detail) msg += ` - ${d.detail}`;
    } catch {}
    throw new Error(msg);
  }
  return response.json();
}

async function fetchJobSkills(daysBack = 5, limit = 1000) {
  const endpoint = `http://127.0.0.1:8000/job_skills_recent?days_back=${encodeURIComponent(daysBack)}&limit=${encodeURIComponent(limit)}`;
  const response = await fetch(endpoint, { method: 'GET' });
  if (!response.ok) {
    let msg = `API Error: ${response.status}`;
    try { 
      const d = await response.json(); 
      if (d?.detail) msg += ` - ${d.detail}`;
    } catch {}
    throw new Error(msg);
  }
  const rows = await response.json();
  // Convert to Map like in history.js
  const map = new Map();
  for (const r of rows || []) {
    const list = map.get(r.job_id) || [];
    list.push(r);
    map.set(r.job_id, list);
  }
  return map;
}

// Helper functions from history.js
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

// Metric calculation and display
function updateMetrics(totalAssessed, totalFeasible, totalApplied, totalFeasibleNotApplied) {
  totalAssessedEl.textContent = totalAssessed.toLocaleString();
  totalFeasibleEl.textContent = totalFeasible.toLocaleString();
  totalAppliedEl.textContent = totalApplied.toLocaleString();
  totalFeasibleNotAppliedEl.textContent = totalFeasibleNotApplied.toLocaleString();
}

function showLoading() {
  loadingEl.style.display = 'block';
  errorEl.style.display = 'none';
  refreshBtn.disabled = true;
  refreshBtn.textContent = 'Loading...';
}

function hideLoading() {
  loadingEl.style.display = 'none';
  refreshBtn.disabled = false;
  refreshBtn.textContent = 'Refresh';
}

function showError(message) {
  errorEl.textContent = message;
  errorEl.style.display = 'block';
  hideLoading();
}

// Main dashboard loading function
async function loadDashboard() {
  const daysBack = Math.max(1, parseInt(daysBackInput.value || '5', 10));
  
  try {
    showLoading();
    
    const [jobsData, skillsMap] = await Promise.all([
      fetchHistory(daysBack, 1000),
      fetchJobSkills(daysBack, 1000)
    ]);
    
    if (!Array.isArray(jobsData)) {
      throw new Error('Invalid jobs data received from API');
    }
    
    // Calculate metrics
    const totalAssessed = jobsData.length;
    
    const feasibleJobs = jobsData.filter(job => 
      isDecentLead(job.job_id, skillsMap)
    );
    const totalFeasible = feasibleJobs.length;
    
    const appliedJobs = jobsData.filter(job => 
      job.job_applied === 1 || job.job_applied === true
    );
    const totalApplied = appliedJobs.length;
    
    const feasibleNotAppliedJobs = feasibleJobs.filter(job => 
      !(job.job_applied === 1 || job.job_applied === true)
    );
    const totalFeasibleNotApplied = feasibleNotAppliedJobs.length;
    
    // Update the display
    updateMetrics(totalAssessed, totalFeasible, totalApplied, totalFeasibleNotApplied);
    hideLoading();
    
  } catch (error) {
    console.error('Failed to load dashboard metrics:', error);
    showError(`Failed to load metrics: ${error.message}`);
  }
}

// Click handlers for metric cards
function setupClickHandlers() {
  // Total jobs assessed - history page with just days filter
  document.getElementById('card-assessed').addEventListener('click', () => {
    const daysBack = parseInt(daysBackInput.value || '5', 10);
    window.location.href = `../history/history.html?days=${daysBack}`;
  });
  
  // Total jobs feasible - history page with decent only filter
  document.getElementById('card-feasible').addEventListener('click', () => {
    const daysBack = parseInt(daysBackInput.value || '5', 10);
    window.location.href = `../history/history.html?days=${daysBack}&decentOnly=true`;
  });
  
  // Total jobs applied - history page with hide applied OFF (show applied)
  document.getElementById('card-applied').addEventListener('click', () => {
    const daysBack = parseInt(daysBackInput.value || '5', 10);
    window.location.href = `../history/history.html?days=${daysBack}&showApplied=true`;
  });
  
  // Feasible jobs not applied - history page with decent only AND hide applied
  document.getElementById('card-feasible-not-applied').addEventListener('click', () => {
    const daysBack = parseInt(daysBackInput.value || '5', 10);
    window.location.href = `../history/history.html?days=${daysBack}&decentOnly=true&hideApplied=true`;
  });
}

// Event listeners
refreshBtn.addEventListener('click', loadDashboard);

// Allow Enter key to refresh
daysBackInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    loadDashboard();
  }
});

// Load dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
  console.log('Dashboard page loaded');
  setupClickHandlers();
  loadDashboard();
});