import { useState, useCallback, useRef, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileCheck, Loader2, AlertCircle, Layers, RefreshCw } from 'lucide-react';
import {
  uploadPdf,
  uploadBatchPdfs,
  extractActionsAsync,
  getExtractActionsStatus,
} from '../lib/api';
import toast from 'react-hot-toast';

// ── Stage → human-readable label ─────────────────────────────
const STAGE_LABELS = {
  queued:        'Waiting in queue…',
  pdf_extraction:'Extracting PDF text…',
  llm_extraction:'AI analysing judgment…',
  db_persist:    'Saving to database…',
  completed:     'Extraction complete!',
};

function stageLabel(stage, elapsedSec) {
  const base = STAGE_LABELS[stage] || 'Processing…';
  return elapsedSec > 0 ? `${base} (${elapsedSec}s)` : base;
}

const POLL_INTERVAL_MS   = 3000;  // 3 s between polls
const MAX_POLLS          = 120;   // 6 min max
const MAX_POLL_ERRORS    = 4;     // stop after 4 consecutive network errors

export default function UploadCard({ onExtractionComplete }) {
  const [status,          setStatus]          = useState('idle');
  const [fileName,        setFileName]        = useState('');
  const [error,           setError]           = useState('');
  const [progress,        setProgress]        = useState('');
  const [progressPercent, setProgressPercent] = useState(0);

  // Ref so polling loop can be cancelled when component unmounts
  const abortRef = useRef(null);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  // ── Upload + async extraction flow ────────────────────────
  const onDrop = useCallback(async (acceptedFiles) => {
    const list = [...acceptedFiles].filter(Boolean);
    if (!list.length) return;

    // Cancel any previous in-flight operation
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    const signal = abortRef.current.signal;

    setError('');

    // ── Batch upload ─────────────────────────────────────────
    if (list.length > 1) {
      setFileName(`${list.length} PDF files`);
      setStatus('extracting');
      setProgress(`Queueing batch job (${list.length} files)…`);
      setProgressPercent(0);
      const tid = toast.loading('Uploading batch…');

      try {
        const batch = await uploadBatchPdfs(list);
        toast.success(`Batch queued: ${batch.job_id}`, { id: tid });
        setStatus('done');
        setProgress('Batch extraction running on server');
        setProgressPercent(100);
        onExtractionComplete?.({ batch: true, job_id: batch.job_id, files_enqueued: batch.files_enqueued });
      } catch (err) {
        if (signal.aborted) return;
        setStatus('error');
        const message = _extractError(err, 'Batch upload failed');
        setError(message);
        toast.error(message, { id: tid });
      }
      return;
    }

    // ── Single file upload ────────────────────────────────────
    const file = list[0];
    setFileName(file.name);
    setStatus('uploading');
    setProgress('Uploading PDF to secure storage…');
    setProgressPercent(0);
    toast.loading('Uploading PDF…', { id: 'upload' });

    try {
      // Step 1: upload to storage
      const uploadResult = await uploadPdf(file, 'system');
      if (signal.aborted) return;

      setStatus('extracting');
      setProgress('Queuing AI extraction…');
      setProgressPercent(10);
      toast.loading('Extraction queued. Processing in background…', { id: 'upload' });

      // Step 2: queue async extraction
      const queued = await extractActionsAsync(uploadResult.pdf_url);
      if (signal.aborted) return;

      // Step 3: poll for completion
      const extractResult = await _pollUntilDone(queued.job_id, signal, setProgress);
      if (signal.aborted) return;

      setStatus('done');
      setProgress('Extraction complete!');
      setProgressPercent(100);
      toast.success('PDF uploaded and extracted successfully', { id: 'upload' });
      onExtractionComplete?.(extractResult);

    } catch (err) {
      if (signal.aborted) return;
      setStatus('error');
      const message = _extractError(err, 'Something went wrong');
      setError(message);
      toast.error(message, { id: 'upload' });
    }
  }, [onExtractionComplete]);

  // ── Dropzone ──────────────────────────────────────────────
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 12,
    disabled: status === 'uploading' || status === 'extracting',
  });

  const reset = () => {
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    setStatus('idle');
    setFileName('');
    setError('');
    setProgress('');
    setProgressPercent(0);
  };

  // ── Styles ────────────────────────────────────────────────
  const getDropzoneStyle = () => {
    let borderColor = 'var(--border-default)';
    let bg = 'transparent';
    if (isDragActive)         { borderColor = 'var(--primary)';  bg = 'var(--primary-muted)'; }
    else if (status === 'done')  { borderColor = 'var(--success)';  bg = 'var(--success-muted)'; }
    else if (status === 'error') { borderColor = 'var(--danger)';   bg = 'var(--danger-muted)'; }
    return {
      borderRadius: 'var(--radius-xl)',
      border: `2px dashed ${borderColor}`,
      padding: '48px 32px',
      textAlign: 'center',
      cursor: status === 'uploading' || status === 'extracting' ? 'wait' : 'pointer',
      transition: 'all 0.3s ease',
      background: bg,
      transform: isDragActive ? 'scale(1.01)' : 'scale(1)',
    };
  };

  const renderIcon = () => {
    const box = (bgColor) => ({
      width: 64, height: 64, borderRadius: 'var(--radius-lg)',
      background: bgColor, display: 'flex', alignItems: 'center',
      justifyContent: 'center', margin: '0 auto 20px',
    });
    if (status === 'uploading' || status === 'extracting')
      return <div style={box('var(--primary-muted)')} className="animate-pulse-glow">
        <Loader2 size={28} style={{ color: 'var(--primary)', animation: 'spin 1s linear infinite' }} />
      </div>;
    if (status === 'done')
      return <div style={box('var(--success-muted)')}><FileCheck size={28} style={{ color: 'var(--success)' }} /></div>;
    if (status === 'error')
      return <div style={box('var(--danger-muted)')}><AlertCircle size={28} style={{ color: 'var(--danger)' }} /></div>;
    return <div style={box('var(--primary-muted)')}><Upload size={28} style={{ color: 'var(--primary)' }} /></div>;
  };

  return (
    <section id="upload" style={{ maxWidth: 640, margin: '0 auto', padding: '48px 24px' }}>
      <div className="animate-fade-in-up" style={{ textAlign: 'center', marginBottom: 32 }}>
        <h2 className="text-section-title" style={{ marginBottom: 8, color: 'var(--text-primary)' }}>
          Upload Judgment
        </h2>
        <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>
          Drop one judgment for instant extraction — or multi-select PDFs for batch processing
        </p>
      </div>

      <div {...getRootProps()} style={getDropzoneStyle()} className="animate-fade-in-up">
        <input {...getInputProps()} />
        {renderIcon()}

        {status === 'idle' && (
          <>
            <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>
              {isDragActive ? 'Drop your PDFs here' : 'Drag & drop PDF(s)'}
            </p>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>
              or click to browse • single file runs full pipeline preview
            </p>
            <p style={{
              fontSize: 11, color: 'var(--text-muted)', display: 'inline-flex',
              alignItems: 'center', gap: 8, border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)', padding: '6px 10px',
            }}>
              <Layers size={14} aria-hidden /> Multi-upload uses <code>/api/upload-batch</code>
            </p>
          </>
        )}

        {(status === 'uploading' || status === 'extracting') && (
          <>
            <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--primary)', marginBottom: 8 }}>{progress}</p>
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>{fileName}</p>
            {status === 'uploading' && (
              <div style={{ maxWidth: 300, margin: '16px auto 0' }}>
                <div style={{ height: 6, borderRadius: 'var(--radius-full)', background: 'var(--bg-card)', overflow: 'hidden' }}>
                  <div style={{
                    height: '100%', borderRadius: 'var(--radius-full)',
                    background: 'linear-gradient(90deg, var(--primary), var(--accent-violet))',
                    width: `${progressPercent}%`, transition: 'width 0.3s ease',
                  }} />
                </div>
                <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>{progressPercent}% uploaded</p>
              </div>
            )}
          </>
        )}

        {status === 'done' && (
          <>
            <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--success)', marginBottom: 8 }}>✓ {progress}</p>
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>{fileName}</p>
          </>
        )}

        {status === 'error' && (
          <>
            <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--danger)', marginBottom: 8 }}>Upload Failed</p>
            <p style={{ fontSize: 13, color: 'var(--danger-text)', marginBottom: 4 }}>{error}</p>
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>{fileName}</p>
          </>
        )}
      </div>

      {(status === 'done' || status === 'error') && (
        <div className="animate-fade-in-up" style={{ textAlign: 'center', marginTop: 24 }}>
          <button type="button" onClick={reset} className="btn btn-ghost">
            <RefreshCw size={14} style={{ marginRight: 6 }} />
            Upload Another
          </button>
        </div>
      )}
    </section>
  );
}

// ── Polling helper ────────────────────────────────────────────

async function _pollUntilDone(jobId, signal, setProgress) {
  let poll = 0;
  let consecutiveErrors = 0;
  const start = Date.now();

  while (poll < MAX_POLLS) {
    if (signal.aborted) return null;

    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
    if (signal.aborted) return null;

    poll++;
    const elapsedSec = Math.round((Date.now() - start) / 1000);

    let st;
    try {
      st = await getExtractActionsStatus(jobId);
      consecutiveErrors = 0;
    } catch (pollErr) {
      consecutiveErrors++;

      // 410 Gone = backend restarted; in-memory job store was wiped
      if (pollErr?.status === 410) {
        const detail = pollErr?.payload?.detail || {};
        throw new Error(
          typeof detail === 'string'
            ? detail
            : (detail.error || 'Backend restarted during extraction. Check the case list — your document may still have been processed.')
        );
      }

      // Other network errors — allow a few retries before giving up
      if (consecutiveErrors >= MAX_POLL_ERRORS) {
        throw new Error(
          `Lost connection to server after ${elapsedSec}s. ` +
          'Check the case list — your document may still be processing.'
        );
      }

      // Transient error — update UI and retry next cycle
      setProgress(`Retrying status check… (${elapsedSec}s)`);
      continue;
    }

    // Update progress label using stage from server
    setProgress(stageLabel(st.stage || st.status, elapsedSec));

    if (st.status === 'completed') {
      return st.result;
    }

    if (st.status === 'failed') {
      const stage  = st.error_stage ? ` [stage: ${st.error_stage}]` : '';
      const reason = st.error || 'Extraction job failed';
      throw new Error(`${reason}${stage}`);
    }
  }

  // Timeout
  throw new Error(
    'Extraction is taking longer than expected. ' +
    'Check the case list — your document may still be processing in the background.'
  );
}

// ── Error normalisation ───────────────────────────────────────
function _extractError(err, fallback) {
  if (!err) return fallback;
  // Detail from structured JSON payload
  const detail = err?.payload?.detail;
  if (typeof detail === 'string') return detail;
  if (typeof detail?.error === 'string') return detail.error;
  if (typeof err.message === 'string' && err.message) return err.message;
  return fallback;
}
