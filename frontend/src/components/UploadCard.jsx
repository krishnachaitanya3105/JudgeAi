import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileCheck, Loader2, AlertCircle, Layers } from 'lucide-react';
import {
  uploadPdf,
  uploadBatchPdfs,
  extractActionsAsync,
  getExtractActionsStatus,
} from '../lib/api';
import toast from 'react-hot-toast';

export default function UploadCard({ onExtractionComplete }) {
  const [status, setStatus] = useState('idle');
  const [fileName, setFileName] = useState('');
  const [error, setError] = useState('');
  const [progress, setProgress] = useState('');
  const [progressPercent, setProgressPercent] = useState(0);

  const onDrop = useCallback(async (acceptedFiles) => {
    const list = [...acceptedFiles].filter(Boolean);
    if (!list.length) return;

    setError('');

    if (list.length > 1) {
      setFileName(`${list.length} PDF files`);
      setStatus('extracting');
      setProgress(`Queueing batch job (${list.length} files)…`);
      setProgressPercent(0);
      const tid = toast.loading('Upload batch…');

      try {
        const batch = await uploadBatchPdfs(list);
        toast.success(`Batch queued: ${batch.job_id}`, { id: tid });
        setStatus('done');
        setProgress('Batch extraction running on server');
        setProgressPercent(100);
        onExtractionComplete?.({
          batch: true,
          job_id: batch.job_id,
          files_enqueued: batch.files_enqueued,
        });
      } catch (err) {
        setStatus('error');
        const message = err?.response?.data?.detail || err.message || 'Batch failed';
        setError(message);
        toast.error(message, { id: tid });
      }
      return;
    }

    const file = list[0];
    setFileName(file.name);
    setStatus('uploading');
    setProgress('Uploading PDF to secure storage...');
    setProgressPercent(0);
    toast.loading('Uploading PDF...', { id: 'upload' });

    try {
      const uploadResult = await uploadPdf(file, 'system', (evt) => {
        const total = evt.total || file.size || 1;
        const uploaded = evt.loaded || 0;
        const value = Math.min(100, Math.round((uploaded / total) * 100));
        setProgressPercent(value);
      });

      setStatus('extracting');
      setProgress('AI extraction queued...');
      setProgressPercent(100);
      toast.loading('Extraction queued. Processing in background...', { id: 'upload' });

      const queued = await extractActionsAsync(uploadResult.pdf_url);
      const maxPolls = 180; // ~6 min at 2s interval
      let poll = 0;
      let extractResult = null;
      while (poll < maxPolls) {
        // eslint-disable-next-line no-await-in-loop
        await new Promise((resolve) => setTimeout(resolve, 2000));
        poll += 1;
        // eslint-disable-next-line no-await-in-loop
        const st = await getExtractActionsStatus(queued.job_id);
        if (st.status === 'completed') {
          extractResult = st.result;
          break;
        }
        if (st.status === 'failed') {
          throw new Error(st.error || 'Extraction job failed');
        }
        setProgress(`AI analyzing judgment... (${poll * 2}s)`);
      }

      if (!extractResult) {
        throw new Error('Extraction is taking longer than expected. Please check case list shortly.');
      }

      setStatus('done');
      setProgress('Extraction complete!');
      toast.success('PDF uploaded and extracted successfully', { id: 'upload' });
      onExtractionComplete?.(extractResult);
    } catch (err) {
      setStatus('error');
      const message = err?.response?.data?.detail || err.message || 'Something went wrong';
      setError(message);
      toast.error(message, { id: 'upload' });
    }
  }, [onExtractionComplete]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 12,
    disabled: status === 'uploading' || status === 'extracting',
  });

  const reset = () => {
    setStatus('idle');
    setFileName('');
    setError('');
    setProgress('');
    setProgressPercent(0);
  };

  const getDropzoneStyle = () => {
    let borderColor = 'var(--border-default)';
    let bg = 'transparent';

    if (isDragActive) {
      borderColor = 'var(--primary)';
      bg = 'var(--primary-muted)';
    } else if (status === 'done') {
      borderColor = 'var(--success)';
      bg = 'var(--success-muted)';
    } else if (status === 'error') {
      borderColor = 'var(--danger)';
      bg = 'var(--danger-muted)';
    }

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
    const iconContainerStyle = (bgColor) => ({
      width: 64,
      height: 64,
      borderRadius: 'var(--radius-lg)',
      background: bgColor,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      margin: '0 auto 20px',
    });

    if (status === 'uploading' || status === 'extracting') {
      return (
        <div style={iconContainerStyle('var(--primary-muted)')} className="animate-pulse-glow">
          <Loader2 size={28} style={{ color: 'var(--primary)', animation: 'spin 1s linear infinite' }} />
        </div>
      );
    }
    if (status === 'done') {
      return (
        <div style={iconContainerStyle('var(--success-muted)')}>
          <FileCheck size={28} style={{ color: 'var(--success)' }} />
        </div>
      );
    }
    if (status === 'error') {
      return (
        <div style={iconContainerStyle('var(--danger-muted)')}>
          <AlertCircle size={28} style={{ color: 'var(--danger)' }} />
        </div>
      );
    }
    return (
      <div style={iconContainerStyle('var(--primary-muted)')}>
        <Upload size={28} style={{ color: 'var(--primary)' }} />
      </div>
    );
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

      <div
        {...getRootProps()}
        style={getDropzoneStyle()}
        className="animate-fade-in-up"
      >
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
              fontSize: 11,
              color: 'var(--text-muted)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '6px 10px',
            }}
            >
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
                <div
                  style={{
                    height: 6,
                    borderRadius: 'var(--radius-full)',
                    background: 'var(--bg-card)',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      borderRadius: 'var(--radius-full)',
                      background: 'linear-gradient(90deg, var(--primary), var(--accent-violet))',
                      width: `${progressPercent}%`,
                      transition: 'width 0.3s ease',
                    }}
                  />
                </div>
                <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
                  {progressPercent}% uploaded
                </p>
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
            Upload Another
          </button>
        </div>
      )}
    </section>
  );
}
