import { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  Check,
  X,
  Edit2,
  Search,
  FileText,
  Info,
  Keyboard,
} from 'lucide-react';
import { getCases, approveAction, rejectAction, editAction } from '../lib/api';
import toast from 'react-hot-toast';
import { useAuth } from '../context/useAuth';
import ConfidenceGauge from '../components/ui/ConfidenceGauge';
import ConfirmModal from '../components/ui/ConfirmModal';
import EmptyState from '../components/ui/EmptyState';
import { SkeletonCard } from '../components/ui/Skeleton';

export default function VerificationPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [editData, setEditData] = useState({});
  const [error, setError] = useState('');
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [showShortcuts, setShowShortcuts] = useState(false);

  useEffect(() => {
    const fetchCases = async () => {
      try {
        const data = await getCases(0, 50, 'pending');
        setCases(data.data || []);
      } catch (err) {
        const message = err.response?.data?.detail || err.message || 'Failed to load cases';
        setError(message);
        toast.error(message);
      } finally {
        setLoading(false);
      }
    };
    fetchCases();
  }, []);

  // Keyboard shortcuts
  const handleApprove = useCallback(async (caseItem) => {
    try {
      await approveAction(caseItem.id, user?.email || 'officer');
      toast.success('Case approved successfully ✓');
      setCases((prev) => prev.filter((c) => c.id !== caseItem.id));
      setSelectedCase(null);
    } catch {
      toast.error('Failed to approve case');
    }
  }, [user]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (editMode || rejectModalOpen) return;
      if (!selectedCase) return;
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

      if (e.key === 'a' || e.key === 'A') {
        e.preventDefault();
        handleApprove(selectedCase);
      }
      if (e.key === 'e' || e.key === 'E') {
        e.preventDefault();
        setEditMode(true);
      }
      if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        setRejectModalOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedCase, editMode, rejectModalOpen, handleApprove]);

  async function handleReject(reason) {
    if (!selectedCase) return;
    try {
      await rejectAction(selectedCase.id, reason || 'Rejected by officer', user?.email || 'officer');
      toast.success('Case rejected');
      setCases((prev) => prev.filter((c) => c.id !== selectedCase.id));
      setSelectedCase(null);
      setRejectModalOpen(false);
    } catch {
      toast.error('Failed to reject case');
    }
  }

  async function handleEdit(caseItem) {
    try {
      await editAction(caseItem.id, editData, user?.email || 'officer');
      toast.success('Case edited successfully');
      setCases((prev) => prev.filter((c) => c.id !== caseItem.id));
      setEditMode(false);
      setSelectedCase(null);
    } catch {
      toast.error('Failed to edit case');
    }
  }

  const filteredCases = searchTerm
    ? cases.filter((c) =>
        c.case_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.department?.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : cases;

  if (loading) {
    return (
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <div className="breadcrumb" style={{ marginBottom: 24 }}>
          <a href="/officer-dashboard">Dashboard</a>
          <span className="separator">/</span>
          <span className="current">Verification Queue</span>
        </div>
        <h1 className="text-page-title" style={{ marginBottom: 32 }}>Extraction Verification</h1>
        <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 24 }}>
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1280, margin: '0 auto' }} className="animate-fade-in">
      {/* Breadcrumb */}
      <div className="breadcrumb" style={{ marginBottom: 8 }}>
        <a href="/officer-dashboard">Dashboard</a>
        <span className="separator">/</span>
        <span className="current">Verification Queue</span>
        {selectedCase && (
          <>
            <span className="separator">/</span>
            <span className="current">{selectedCase.case_number}</span>
          </>
        )}
      </div>

      {/* Page Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 28,
          flexWrap: 'wrap',
          gap: 16,
        }}
      >
        <div>
          <h1 className="text-page-title" style={{ marginBottom: 4 }}>Extraction Verification</h1>
          <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>
            Review pending AI outputs and finalize case status
          </p>
        </div>
        <button
          className="btn btn-ghost"
          onClick={() => setShowShortcuts(!showShortcuts)}
          title="Keyboard shortcuts"
        >
          <Keyboard size={16} />
          Shortcuts
        </button>
      </div>

      {/* Shortcuts Help */}
      {showShortcuts && (
        <div
          className="card animate-scale-in"
          style={{
            marginBottom: 20,
            display: 'flex',
            gap: 24,
            alignItems: 'center',
            padding: '14px 20px',
            background: 'var(--primary-muted)',
            borderColor: 'var(--primary)',
          }}
        >
          <Info size={16} style={{ color: 'var(--primary)', flexShrink: 0 }} />
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', fontSize: 13 }}>
            <span>
              <kbd style={{ padding: '2px 8px', borderRadius: 4, background: 'var(--bg-card)', border: '1px solid var(--border-default)', fontSize: 12, fontWeight: 700, marginRight: 6 }}>A</kbd>
              Approve
            </span>
            <span>
              <kbd style={{ padding: '2px 8px', borderRadius: 4, background: 'var(--bg-card)', border: '1px solid var(--border-default)', fontSize: 12, fontWeight: 700, marginRight: 6 }}>E</kbd>
              Edit
            </span>
            <span>
              <kbd style={{ padding: '2px 8px', borderRadius: 4, background: 'var(--bg-card)', border: '1px solid var(--border-default)', fontSize: 12, fontWeight: 700, marginRight: 6 }}>R</kbd>
              Reject
            </span>
          </div>
        </div>
      )}

      {error && (
        <div
          className="card"
          style={{
            marginBottom: 20,
            display: 'flex',
            gap: 12,
            borderColor: 'var(--danger)',
            background: 'var(--danger-muted)',
            padding: '14px 20px',
          }}
        >
          <AlertCircle size={18} style={{ color: 'var(--danger)', flexShrink: 0 }} />
          <p style={{ fontSize: 13, color: 'var(--danger-text)' }}>{error}</p>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 24, alignItems: 'start' }}>
        {/* Cases List Panel */}
        <div className="card" style={{ position: 'sticky', top: 88 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <h2 className="text-card-title">Pending Cases</h2>
            <span
              style={{
                fontSize: 12,
                fontWeight: 700,
                color: 'var(--primary)',
                background: 'var(--primary-muted)',
                padding: '2px 10px',
                borderRadius: 'var(--radius-full)',
              }}
            >
              {filteredCases.length}
            </span>
          </div>

          {/* Search */}
          <div style={{ position: 'relative', marginBottom: 12 }}>
            <Search
              size={14}
              style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}
            />
            <input
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input"
              style={{ paddingLeft: 34, fontSize: 13, padding: '8px 12px 8px 34px' }}
              placeholder="Filter cases..."
            />
          </div>

          {/* Case List */}
          <div style={{ maxHeight: 500, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
            {filteredCases.length > 0 ? (
              filteredCases.map((caseItem) => {
                const active = selectedCase?.id === caseItem.id;
                const conf = caseItem.confidence_score || 0;
                return (
                  <button
                    key={caseItem.id}
                    onClick={() => {
                      setSelectedCase(caseItem);
                      setEditMode(false);
                      setEditData({});
                    }}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      padding: '12px 14px',
                      borderRadius: 'var(--radius-md)',
                      border: `1px solid ${active ? 'var(--primary)' : 'var(--border-subtle)'}`,
                      background: active ? 'var(--primary-muted)' : 'transparent',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <p
                        style={{
                          fontSize: 13,
                          fontWeight: 600,
                          color: active ? 'var(--primary)' : 'var(--text-primary)',
                          fontFamily: 'monospace',
                        }}
                      >
                        {caseItem.case_number}
                      </p>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 700,
                          color: conf > 0.7 ? 'var(--success-text)' : conf > 0.4 ? 'var(--warning-text)' : 'var(--danger-text)',
                        }}
                      >
                        {(conf * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                      {caseItem.department || 'Unassigned'}
                    </p>
                  </button>
                );
              })
            ) : (
              <EmptyState preset="no-cases" />
            )}
          </div>
        </div>

        {/* Case Details Panel */}
        <div>
          {selectedCase ? (
            <div className="animate-slide-in-right" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Case Header Card */}
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 20 }}>
                  {/* Left: Case Info */}
                  <div style={{ flex: 1, minWidth: 250 }}>
                    <h2 className="text-section-title" style={{ marginBottom: 20 }}>Case Details</h2>

                    {/* Metadata Fields */}
                    {!editMode ? (
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                        {[
                          { label: 'Case Number', value: selectedCase.case_number, mono: true },
                          { label: 'Judgment Date', value: selectedCase.judgment_date || 'N/A' },
                          { label: 'Department', value: selectedCase.department || 'N/A' },
                          { label: 'Deadline', value: selectedCase.deadline || 'N/A' },
                        ].map((field) => (
                          <div key={field.label}>
                            <p className="text-caption" style={{ marginBottom: 4 }}>{field.label}</p>
                            <p
                              style={{
                                fontSize: 14,
                                fontWeight: 600,
                                color: 'var(--text-primary)',
                                fontFamily: field.mono ? 'monospace' : 'inherit',
                              }}
                            >
                              {field.value}
                            </p>
                          </div>
                        ))}
                        <div style={{ gridColumn: '1 / -1' }}>
                          <p className="text-caption" style={{ marginBottom: 4 }}>Directive Summary</p>
                          <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                            {selectedCase.directive || 'N/A'}
                          </p>
                        </div>
                        <div style={{ gridColumn: '1 / -1' }}>
                          <p className="text-caption" style={{ marginBottom: 4 }}>Source Sentence</p>
                          <div
                            style={{
                              padding: '12px 16px',
                              borderRadius: 'var(--radius-sm)',
                              background: 'var(--bg-surface)',
                              border: '1px solid var(--border-subtle)',
                              borderLeft: '3px solid var(--primary)',
                              fontSize: 13,
                              fontStyle: 'italic',
                              color: 'var(--text-secondary)',
                              lineHeight: 1.6,
                            }}
                          >
                            {selectedCase.source_sentence || 'Not available'}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                        {[
                          { key: 'case_number', label: 'Case Number', type: 'text' },
                          { key: 'judgment_date', label: 'Judgment Date', type: 'date' },
                          { key: 'department', label: 'Department', type: 'text' },
                          { key: 'deadline', label: 'Deadline', type: 'date' },
                        ].map((field) => (
                          <div key={field.key}>
                            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                              {field.label}
                            </label>
                            <input
                              type={field.type}
                              value={editData[field.key] || selectedCase[field.key] || ''}
                              onChange={(e) => setEditData({ ...editData, [field.key]: e.target.value })}
                              className="input"
                            />
                          </div>
                        ))}
                        <div>
                          <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                            Directive
                          </label>
                          <textarea
                            value={editData.directive || selectedCase.directive || ''}
                            onChange={(e) => setEditData({ ...editData, directive: e.target.value })}
                            className="input"
                            style={{ minHeight: 80, resize: 'vertical' }}
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Right: Confidence Gauge */}
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                    <p className="text-caption" style={{ marginBottom: 4 }}>AI Confidence</p>
                    <ConfidenceGauge score={selectedCase.confidence_score || 0} size={140} />
                    <p
                      style={{
                        fontSize: 11,
                        color: 'var(--text-muted)',
                        maxWidth: 160,
                        textAlign: 'center',
                        lineHeight: 1.4,
                        marginTop: 4,
                      }}
                      title="Score represents model agreement with extracted directive consistency."
                    >
                      <Info size={10} style={{ display: 'inline', marginRight: 3, verticalAlign: 'middle' }} />
                      Model agreement with extracted directive consistency
                    </p>
                  </div>
                </div>
              </div>

              {/* Action Bar - Sticky Bottom */}
              <div
                className="card"
                style={{
                  position: 'sticky',
                  bottom: 0,
                  zIndex: 10,
                  display: 'flex',
                  gap: 12,
                  padding: '16px 24px',
                  flexWrap: 'wrap',
                  borderColor: 'var(--border-default)',
                  boxShadow: '0 -4px 20px rgba(0,0,0,0.2)',
                }}
              >
                {editMode ? (
                  <>
                    <button
                      onClick={() => handleEdit(selectedCase)}
                      className="btn btn-primary"
                      style={{ flex: 1, minWidth: 140 }}
                    >
                      <Check size={16} /> Save Changes
                    </button>
                    <button
                      onClick={() => setEditMode(false)}
                      className="btn btn-ghost"
                      style={{ flex: 1, minWidth: 140 }}
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => handleApprove(selectedCase)}
                      className="btn btn-success"
                      style={{ flex: 1, minWidth: 120 }}
                    >
                      <Check size={16} /> Approve
                      <kbd style={{ fontSize: 10, opacity: 0.7, marginLeft: 4, padding: '1px 4px', borderRadius: 3, border: '1px solid rgba(255,255,255,0.3)' }}>A</kbd>
                    </button>
                    <button
                      onClick={() => setEditMode(true)}
                      className="btn btn-primary"
                      style={{ flex: 1, minWidth: 120 }}
                    >
                      <Edit2 size={16} /> Edit Directive
                      <kbd style={{ fontSize: 10, opacity: 0.7, marginLeft: 4, padding: '1px 4px', borderRadius: 3, border: '1px solid rgba(255,255,255,0.3)' }}>E</kbd>
                    </button>
                    <button
                      onClick={() => setRejectModalOpen(true)}
                      className="btn btn-danger"
                      style={{ flex: 1, minWidth: 120 }}
                    >
                      <X size={16} /> Reject Case
                      <kbd style={{ fontSize: 10, opacity: 0.7, marginLeft: 4, padding: '1px 4px', borderRadius: 3, border: '1px solid rgba(255,255,255,0.3)' }}>R</kbd>
                    </button>
                  </>
                )}
              </div>
            </div>
          ) : (
            <div
              className="card"
              style={{ minHeight: 450 }}
            >
              <EmptyState
                icon={FileText}
                title="Select a case to review"
                text="Choose a case from the queue to view details, review AI extraction, and take action."
              />
            </div>
          )}
        </div>
      </div>

      {/* Reject Confirmation Modal */}
      <ConfirmModal
        open={rejectModalOpen}
        onClose={() => setRejectModalOpen(false)}
        onConfirm={(reason) => handleReject(reason)}
        title="Reject Case"
        message={`Are you sure you want to reject case ${selectedCase?.case_number || ''}? This action will mark the case as rejected and notify the system.`}
        confirmLabel="Reject Case"
        showReasonInput
      />

      {/* Responsive override for small screens */}
      <style>{`
        @media (max-width: 900px) {
          div[style*="grid-template-columns: 340px"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
}
