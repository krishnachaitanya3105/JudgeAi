import { X, AlertTriangle } from 'lucide-react';
import { useEffect, useRef } from 'react';

/**
 * Confirmation modal for destructive actions.
 * @param {{ open: boolean, onClose: () => void, onConfirm: (reason?: string) => void, title?: string, message?: string, confirmLabel?: string, showReasonInput?: boolean }} props
 */
export default function ConfirmModal({
  open,
  onClose,
  onConfirm,
  title = 'Confirm Action',
  message = 'Are you sure you want to proceed?',
  confirmLabel = 'Confirm',
  showReasonInput = false,
}) {
  const reasonRef = useRef(null);

  useEffect(() => {
    if (open) {
      const handleEsc = (e) => {
        if (e.key === 'Escape') onClose();
      };
      window.addEventListener('keydown', handleEsc);
      return () => window.removeEventListener('keydown', handleEsc);
    }
  }, [open, onClose]);

  useEffect(() => {
    if (open && showReasonInput && reasonRef.current) {
      reasonRef.current.focus();
    }
  }, [open, showReasonInput]);

  if (!open) return null;

  const handleConfirm = () => {
    const reason = reasonRef.current?.value || '';
    onConfirm(reason);
  };

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-label={title}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 'var(--radius-md)',
                background: 'var(--danger-muted)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <AlertTriangle size={20} style={{ color: 'var(--danger)' }} />
            </div>
            <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>{title}</h3>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: 4,
            }}
            aria-label="Close modal"
          >
            <X size={20} />
          </button>
        </div>

        <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 20, lineHeight: 1.6 }}>
          {message}
        </p>

        {showReasonInput && (
          <textarea
            ref={reasonRef}
            placeholder="Enter reason for rejection..."
            className="input"
            style={{ minHeight: 80, marginBottom: 20, resize: 'vertical' }}
          />
        )}

        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
          <button className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-danger" onClick={handleConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
