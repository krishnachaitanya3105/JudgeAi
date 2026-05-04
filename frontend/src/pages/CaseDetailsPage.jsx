import { useParams, Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import {
  Download,
  Calendar,
  Building2,
  Clock,
  FileText,
  Activity,
  Hash,
  Scale,
  TrendingUp,
  MessageCircleQuestion,
} from 'lucide-react';
import { getCaseDetails } from '../lib/api';
import toast from 'react-hot-toast';
import ConfidenceGauge from '../components/ui/ConfidenceGauge';
import JudgmentPdfPanel from '../components/JudgmentPdfPanel';
import StatusChip from '../components/ui/StatusChip';
import { SkeletonCard } from '../components/ui/Skeleton';
import EmptyState from '../components/ui/EmptyState';

function coerceFusedActionPlanScore(reasoning, ap, rowLevelConfidence) {
  const r = reasoning?.final_action_plan_confidence;
  if (typeof r === 'number' && !Number.isNaN(r)) return Math.min(1, Math.max(0, r));
  if (r != null && r !== '') {
    const n = Number(r);
    if (!Number.isNaN(n)) return Math.min(1, Math.max(0, n));
  }
  const ac = ap?.confidence_score;
  if (ac != null && ac !== '') {
    const n = typeof ac === 'number' ? ac : Number(ac);
    if (!Number.isNaN(n)) return Math.min(1, Math.max(0, n));
  }
  const row = rowLevelConfidence;
  if (row != null && row !== '') {
    const n = typeof row === 'number' ? row : Number(row);
    if (!Number.isNaN(n)) return Math.min(1, Math.max(0, n));
  }
  return 0;
}

export default function CaseDetailsPage() {
  const { id } = useParams();
  const [loading, setLoading] = useState(true);
  const [caseData, setCaseData] = useState(null);
  const [auditLog, setAuditLog] = useState([]);
  const [pdfHighlights, setPdfHighlights] = useState([]);

  useEffect(() => {
    const fetchDetails = async () => {
      setLoading(true);
      try {
        const data = await getCaseDetails(id);
        setCaseData(data.action);
        setAuditLog(data.audit_logs || []);
        setPdfHighlights(Array.isArray(data.pdf_highlights) ? data.pdf_highlights : []);
      } catch (err) {
        toast.error(err.response?.data?.detail || 'Failed to load case details');
      } finally {
        setLoading(false);
      }
    };
    fetchDetails();
  }, [id]);

  if (loading) {
    return (
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <div className="breadcrumb" style={{ marginBottom: 24 }}>
          <a href="/officer-dashboard">Dashboard</a>
          <span className="separator">/</span>
          <span className="current">Case Details</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24 }}>
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <EmptyState
          icon={FileText}
          title="Case details unavailable"
          text="The requested case could not be found or loaded."
          action={
            <Link to="/officer-dashboard" className="btn btn-primary">
              Back to Dashboard
            </Link>
          }
        />
      </div>
    );
  }

  const ap = caseData.action_plan || {};
  const reasoning = caseData.action_plan_reasoning || {};
  const fusedScore = coerceFusedActionPlanScore(reasoning, ap, caseData.confidence_score);

  const fusionRows = [
    {
      key: 'llm',
      label: 'LLM extraction',
      rawKey: 'llm_confidence_raw',
      wKey: 'llm',
      contribKey: 'llm_weighted',
    },
    {
      key: 'timeline',
      label: 'Timeline parser',
      rawKey: 'timeline_confidence_raw',
      wKey: 'timeline',
      contribKey: 'timeline_weighted',
    },
    {
      key: 'department',
      label: 'Department classifier',
      rawKey: 'department_classifier_confidence_raw',
      wKey: 'department',
      contribKey: 'department_weighted',
    },
    {
      key: 'appeal',
      label: 'Appeal recommender',
      rawKey: 'appeal_classifier_confidence_raw',
      wKey: 'appeal',
      contribKey: 'appeal_weighted',
    },
  ];
  const effMap = reasoning.fusion_inputs_effective_clamped01 || {};
  const wMap = reasoning.weights || {};
  const contribMap = reasoning.weighted_contribution || {};
  const impMap = reasoning.subsystem_imputed_default || {};
  const hasFusionLedger = Boolean(
    reasoning.fusion_formula ||
      Object.keys(effMap).length > 0 ||
      Object.keys(contribMap).length > 0 ||
      reasoning.final_action_plan_confidence != null,
  );

  const metadataFields = [
    { icon: Hash, label: 'Case Number', value: caseData.case_number, mono: true },
    { icon: Calendar, label: 'Judgment Date', value: caseData.judgment_date || 'N/A' },
    { icon: Building2, label: 'Department', value: caseData.department || 'N/A' },
    { icon: Clock, label: 'Deadline', value: caseData.deadline || 'N/A' },
    ...(ap.action_type
      ? [{ icon: Scale, label: 'Action type', value: ap.action_type }]
      : []),
    ...(ap.priority_level
      ? [{ icon: TrendingUp, label: 'Priority', value: ap.priority_level }]
      : []),
  ];

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }} className="animate-fade-in">
      {/* Breadcrumb */}
      <div className="breadcrumb" style={{ marginBottom: 8 }}>
        <Link to="/officer-dashboard">Dashboard</Link>
        <span className="separator">/</span>
        <Link to="/verification">Verification Queue</Link>
        <span className="separator">/</span>
        <span className="current">{caseData.case_number}</span>
      </div>

      {/* Page Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 32,
          flexWrap: 'wrap',
          gap: 16,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <h1 className="text-page-title">{caseData.case_number}</h1>
          <StatusChip status={caseData.status} size="md" />
        </div>
        {caseData.pdf_url && (
          <a
            href={caseData.pdf_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary"
            style={{ textDecoration: 'none' }}
          >
            <Download size={16} />
            View PDF
          </a>
        )}
      </div>

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 24, alignItems: 'start' }}>
        {/* Left Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Confidence + Metadata Card */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 24, flexWrap: 'wrap' }}>
              {/* Metadata Grid */}
              <div style={{ flex: 1, minWidth: 280 }}>
                <h2 className="text-section-title" style={{ marginBottom: 20 }}>Case Information</h2>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                  {metadataFields.map((field) => {
                    const Icon = field.icon;
                    return (
                      <div key={field.label} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                        <div
                          style={{
                            width: 32,
                            height: 32,
                            borderRadius: 'var(--radius-sm)',
                            background: 'var(--primary-muted)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0,
                          }}
                        >
                          <Icon size={14} style={{ color: 'var(--primary)' }} />
                        </div>
                        <div>
                          <p className="text-caption" style={{ marginBottom: 2 }}>{field.label}</p>
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
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Final confidence (weighted fusion — not LLM-only) */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <ConfidenceGauge
                  score={fusedScore}
                  size={130}
                  gaugeSubtitle="Final Confidence Score"
                  percentFractionDigits={4}
                />
              </div>
            </div>
            <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--border-subtle)' }}>
              <p className="text-caption" style={{ marginBottom: 10, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
                Fusion transparency
              </p>
              {!hasFusionLedger ? (
                <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.55 }}>
                  No fusion ledger on this row yet. Re-run extraction with the current pipeline to store subsystem weights and effective signals in{' '}
                  <code style={{ fontSize: 11 }}>action_plan_reasoning</code>.
                </p>
              ) : (
                <>
                  {reasoning.fusion_formula ? (
                    <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12, lineHeight: 1.55 }}>
                      {reasoning.fusion_formula}
                    </p>
                  ) : null}
                  <div className="table-container" style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', fontSize: 12 }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: 'left', padding: '8px 6px' }}>Subsystem</th>
                        <th style={{ textAlign: 'right', padding: '8px 6px' }}>Raw signal</th>
                        <th style={{ textAlign: 'right', padding: '8px 6px' }}>Effective (0–1)</th>
                        <th style={{ textAlign: 'right', padding: '8px 6px' }}>Weight</th>
                        <th style={{ textAlign: 'right', padding: '8px 6px' }}>Weighted term</th>
                        <th style={{ textAlign: 'center', padding: '8px 6px' }}>Imputed?</th>
                      </tr>
                    </thead>
                    <tbody>
                      {fusionRows.map((row) => {
                        const raw = reasoning[row.rawKey];
                        const eff = effMap[row.key];
                        const wt = wMap[row.wKey];
                        const cn = contribMap[row.contribKey];
                        const fmtExact = (v, places) => {
                          if (v === null || v === undefined || v === '') return '—';
                          const n = typeof v === 'number' ? v : Number(v);
                          return Number.isNaN(n) ? String(v) : n.toFixed(places);
                        };
                        return (
                          <tr key={row.key}>
                            <td style={{ padding: '8px 6px', color: 'var(--text-primary)', fontWeight: 600 }}>{row.label}</td>
                            <td style={{ padding: '8px 6px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{fmtExact(raw, 6)}</td>
                            <td style={{ padding: '8px 6px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{fmtExact(eff, 6)}</td>
                            <td style={{ padding: '8px 6px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{fmtExact(wt, 4)}</td>
                            <td style={{ padding: '8px 6px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{fmtExact(cn, 10)}</td>
                            <td style={{ padding: '8px 6px', textAlign: 'center', color: impMap[row.key] ? 'var(--warning-text)' : 'var(--text-muted)' }}>
                              {impMap[row.key] ? 'Yes' : 'No'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 10, lineHeight: 1.5 }}>
                  Final score = sum of weighted terms (each effective input clamped to [0,1]; missing subsystem → neutral {reasoning.neutral_imputation_value != null ? `≈ ${Number(reasoning.neutral_imputation_value).toFixed(6)}` : 'imputation'}).
                  {reasoning.weighted_sum_precheck != null ? (
                    <>
                      {' '}
                      Weighted sum (pre-cap):{' '}
                      <span style={{ fontFamily: 'monospace' }}>{Number(reasoning.weighted_sum_precheck).toFixed(6)}</span>
                      {' → final '}
                      <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>
                        {(reasoning.final_action_plan_confidence != null ? Number(reasoning.final_action_plan_confidence) : fusedScore).toFixed(6)}
                      </span>
                      .
                    </>
                  ) : null}
                </p>
                </>
              )}
            </div>
          </div>

          {/* PDF Viewer */}
          {caseData.pdf_url && (
            <div className="card">
              <h2 className="text-section-title" style={{ marginBottom: 16 }}>Original Judgment PDF</h2>
              <JudgmentPdfPanel url={caseData.pdf_url} highlights={pdfHighlights} height={480} />
            </div>
          )}

          {Object.keys(ap).length > 0 && (
            <div className="card">
              <h2 className="text-section-title" style={{ marginBottom: 12 }}>Government action plan</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
                {[
                  ['Department', ap.department],
                  ['Compliance deadline', ap.compliance_deadline || '—'],
                  ['Appeal recommended', ap.appeal_recommended || '—'],
                  ['Appeal window ends', ap.appeal_deadline || '—'],
                  ['Responsible role', ap.responsible_officer_role || '—'],
                ].map(([k, v]) => (
                  <div key={k} style={{ padding: '10px 12px', borderRadius: 'var(--radius-md)', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
                    <p className="text-caption" style={{ marginBottom: 4 }}>{k}</p>
                    <p style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>{v || '—'}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <MessageCircleQuestion size={18} style={{ color: 'var(--primary)' }} />
              <h2 className="text-section-title" style={{ margin: 0 }}>AI explainability</h2>
            </div>
            <p className="text-caption" style={{ marginBottom: 14, color: 'var(--text-muted)', lineHeight: 1.55 }}>
              Grounds for key government-facing outputs, derived from <code style={{ fontSize: 11 }}>action_plan_reasoning</code> (audit trail).
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {[
                {
                  key: 'why_appeal_recommended',
                  heading: 'Why appeal recommended',
                  fallback:
                    'No stored narrative. Check appeal recommender output after re-running extraction, or open appeal_detail in the database row.',
                },
                {
                  key: 'why_department_selected',
                  heading: 'Why department selected',
                  fallback:
                    'No stored narrative. Re-run extraction to populate department classifier reasoning, or inspect department_detail on the action record.',
                },
                {
                  key: 'why_deadline_inferred',
                  heading: 'Why deadline inferred',
                  fallback:
                    'No stored narrative. Timeline parser may not have matched a structured offset; compliance date may come from LLM extraction only.',
                },
              ].map(({ key, heading, fallback }) => {
                const txt = reasoning[key];
                const body = txt && String(txt).trim() ? txt : fallback;
                return (
                  <div
                    key={key}
                    style={{
                      padding: '12px 14px',
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--bg-surface)',
                      borderLeft: '3px solid var(--primary)',
                      fontSize: 13,
                      color: 'var(--text-secondary)',
                      lineHeight: 1.65,
                    }}
                  >
                    <strong
                      style={{
                        color: 'var(--text-primary)',
                        display: 'block',
                        marginBottom: 6,
                        fontSize: 12,
                        letterSpacing: '0.04em',
                      }}
                    >
                      {heading}
                    </strong>
                    {body}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Directive Card */}
          <div className="card">
            <h2 className="text-section-title" style={{ marginBottom: 12 }}>Directive</h2>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
              {caseData.directive || 'No directive extracted'}
            </p>
          </div>

          {/* Human Verified Values */}
          <div className="card">
            <h2 className="text-section-title" style={{ marginBottom: 12 }}>Human Verified Values</h2>
            {caseData.human_verified_values ? (
              <pre
                style={{
                  padding: '16px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-subtle)',
                  fontSize: 12,
                  color: 'var(--text-secondary)',
                  overflowX: 'auto',
                  lineHeight: 1.6,
                }}
              >
                {JSON.stringify(caseData.human_verified_values, null, 2)}
              </pre>
            ) : (
              <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>No human edits recorded.</p>
            )}
          </div>

          {/* Source Sentence */}
          <div className="card">
            <h2 className="text-section-title" style={{ marginBottom: 12 }}>Source Sentence</h2>
            <div
              style={{
                padding: '16px 20px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-subtle)',
                borderLeft: '4px solid var(--primary)',
                fontSize: 14,
                fontStyle: 'italic',
                color: 'var(--text-secondary)',
                lineHeight: 1.7,
              }}
            >
              {caseData.source_sentence || 'No source sentence available'}
            </div>
          </div>
        </div>

        {/* Right Column: Audit Log */}
        <div className="card" style={{ position: 'sticky', top: 88 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
            <Activity size={18} style={{ color: 'var(--primary)' }} />
            <h2 className="text-card-title">Activity Log</h2>
          </div>

          <div style={{ maxHeight: 500, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
            {auditLog && auditLog.length > 0 ? (
              auditLog.map((log) => (
                <div
                  key={log.id}
                  style={{
                    paddingBottom: 16,
                    borderBottom: '1px solid var(--border-subtle)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                    <div
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: 'var(--primary)',
                        marginTop: 6,
                        flexShrink: 0,
                      }}
                    />
                    <div style={{ flex: 1 }}>
                      <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', textTransform: 'capitalize' }}>
                        {log.action_type?.replace(/_/g, ' ')}
                      </p>
                      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                        {log.edited_by}
                      </p>
                      {log.old_value && log.new_value && (
                        <div
                          style={{
                            marginTop: 8,
                            padding: '8px 12px',
                            borderRadius: 'var(--radius-sm)',
                            background: 'var(--bg-surface)',
                            border: '1px solid var(--border-subtle)',
                            fontSize: 12,
                          }}
                        >
                          <span style={{ color: 'var(--danger-text)', textDecoration: 'line-through' }}>
                            {log.old_value}
                          </span>
                          <span style={{ color: 'var(--text-muted)', margin: '0 6px' }}>→</span>
                          <span style={{ color: 'var(--success-text)', fontWeight: 600 }}>
                            {log.new_value}
                          </span>
                        </div>
                      )}
                      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
                        {new Date(log.timestamp).toLocaleString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                          hour: 'numeric',
                          minute: '2-digit',
                        })}
                      </p>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div style={{ padding: '32px 0', textAlign: 'center' }}>
                <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No activity recorded yet</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Responsive override */}
      <style>{`
        @media (max-width: 900px) {
          div[style*="grid-template-columns: 1fr 340px"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
}
