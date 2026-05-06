function joinUrl(base, path) {
  const b = String(base || '').replace(/\/+$/, '');
  const p = String(path || '');
  return `${b}${p.startsWith('/') ? '' : '/'}${p}`;
}

function normalizeErrorMessage(payload) {
  if (!payload) return 'Request failed';
  if (typeof payload === 'string') return payload;
  if (typeof payload?.detail === 'string') return payload.detail;
  if (typeof payload?.message === 'string') return payload.message;
  return 'Request failed';
}

async function request(path, options = {}) {
  const base = import.meta.env.VITE_API_BASE_URL;
  if (!base) {
    throw new Error('Missing VITE_API_BASE_URL. Set it in your Vercel environment variables.');
  }

  const url = joinUrl(base, path);
  const init = { ...options };

  const headers = new Headers(init.headers || {});
  // Allow callers to override content-type (e.g., FormData upload).
  if (!headers.has('Accept')) headers.set('Accept', 'application/json');

  init.headers = headers;

  const res = await fetch(url, init);
  const contentType = res.headers.get('content-type') || '';

  let data = null;
  if (contentType.includes('application/json')) {
    try {
      data = await res.json();
    } catch {
      data = null;
    }
  } else {
    try {
      data = await res.text();
    } catch {
      data = null;
    }
  }

  if (!res.ok) {
    const msg = normalizeErrorMessage(data);
    const err = new Error(msg);
    err.status = res.status;
    err.payload = data;
    throw err;
  }

  return data;
}

function jsonRequest(path, { method = 'GET', body, headers, ...rest } = {}) {
  const h = new Headers(headers || {});
  h.set('Content-Type', 'application/json');
  return request(path, {
    method,
    headers: h,
    body: body === undefined ? undefined : JSON.stringify(body),
    ...rest,
  });
}

// ─────────────────────────────────────────────────────────
// Upload & extraction
// ─────────────────────────────────────────────────────────

export async function uploadPdf(file, uploadedBy = 'system') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('uploaded_by', uploadedBy);

  return request('/upload-pdf', {
    method: 'POST',
    body: formData,
  });
}

export async function uploadBatchPdfs(files, uploadedBy = 'system') {
  const formData = new FormData();
  (files || []).forEach((f) => formData.append('files', f));
  formData.append('uploaded_by', uploadedBy);

  return request('/upload-batch', {
    method: 'POST',
    body: formData,
  });
}

export async function extractActions(pdfUrl) {
  return jsonRequest('/extract-actions', {
    method: 'POST',
    body: { pdf_url: pdfUrl },
  });
}

export async function extractActionsAsync(pdfUrl) {
  return jsonRequest('/extract-actions-async', {
    method: 'POST',
    body: { pdf_url: pdfUrl },
  });
}

export async function getExtractActionsStatus(jobId) {
  return request(`/extract-actions-status/${encodeURIComponent(jobId)}`);
}

export async function getBatchStatus(jobId) {
  return request(`/batch-status/${encodeURIComponent(jobId)}`);
}

export async function demoProcessPdf(pdfUrl) {
  return jsonRequest('/demo-process', {
    method: 'POST',
    body: { pdf_url: pdfUrl },
  });
}

export async function semanticSearch(q, limit = 10) {
  const params = new URLSearchParams();
  if (q != null) params.set('q', String(q));
  if (limit != null) params.set('limit', String(limit));
  return request(`/search-semantic?${params.toString()}`);
}

// ─────────────────────────────────────────────────────────
// Verification & approval
// ─────────────────────────────────────────────────────────

export async function approveAction(actionId, approvedBy = 'system') {
  return jsonRequest(`/approve-action/${encodeURIComponent(actionId)}`, {
    method: 'POST',
    body: { approved_by: approvedBy },
  });
}

export async function editAction(actionId, updates, editedBy = 'system') {
  return jsonRequest(`/edit-action/${encodeURIComponent(actionId)}`, {
    method: 'POST',
    body: { ...(updates || {}), edited_by: editedBy },
  });
}

export async function rejectAction(actionId, reason, rejectedBy = 'system') {
  return jsonRequest(`/reject-action/${encodeURIComponent(actionId)}`, {
    method: 'POST',
    body: { rejection_reason: reason, rejected_by: rejectedBy },
  });
}

// ─────────────────────────────────────────────────────────
// Dashboards & cases
// ─────────────────────────────────────────────────────────

export async function getOfficerDashboard(department = null) {
  const params = new URLSearchParams();
  if (department) params.set('department', String(department));
  const qs = params.toString();
  return request(`/officer-dashboard${qs ? `?${qs}` : ''}`);
}

export async function getAdminDashboard() {
  return request('/admin-dashboard');
}

export async function getCases(
  skip = 0,
  limit = 20,
  status = null,
  department = null,
  caseNumber = null,
  extraParams = {},
) {
  const params = new URLSearchParams();
  params.set('skip', String(skip));
  params.set('limit', String(limit));
  if (status) params.set('status', String(status));
  if (department) params.set('department', String(department));
  if (caseNumber) params.set('case_number', String(caseNumber));

  Object.entries(extraParams || {}).forEach(([k, v]) => {
    if (v === null || v === undefined || v === '') return;
    params.set(String(k), String(v));
  });

  return request(`/cases?${params.toString()}`);
}

export async function getCaseDetails(actionId) {
  return request(`/cases/${encodeURIComponent(actionId)}`);
}

export async function getCaseAnalytics(actionId) {
  return request(`/cases/${encodeURIComponent(actionId)}/analytics`);
}

export function getErrorMessage(error) {
  if (!error) return 'An unexpected error occurred';
  if (typeof error?.message === 'string' && error.message) return error.message;
  if (typeof error?.payload?.detail === 'string') return error.payload.detail;
  return 'An unexpected error occurred';
}
