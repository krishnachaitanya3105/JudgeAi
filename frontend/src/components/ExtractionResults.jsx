import {
  Calendar,
  Hash,
  Building2,
  Clock,
  FileText,
} from 'lucide-react';
import ConfidenceGauge from './ui/ConfidenceGauge';

const fieldConfig = [
  { key: 'case_number', label: 'Case Number', icon: Hash },
  { key: 'judgment_date', label: 'Judgment Date', icon: Calendar },
  { key: 'department', label: 'Department', icon: Building2 },
  { key: 'deadline', label: 'Deadline', icon: Clock },
  { key: 'directive', label: 'Directive', icon: FileText },
];

function formatValue(key, value) {
  if (value === null || value === undefined) return 'N/A';
  if (key === 'confidence_score') return `${(value * 100).toFixed(1)}%`;
  return String(value);
}

/** Prefer fused reasoning score when demo/extract payload includes action_plan_reasoning. */
function resolveFusedScore(reasoning, extracted, actionPlan) {
  const r = reasoning?.final_action_plan_confidence;
  if (typeof r === 'number' && !Number.isNaN(r)) return Math.min(1, Math.max(0, r));
  const fromR = r != null && r !== '' ? Number(r) : NaN;
  if (!Number.isNaN(fromR)) return Math.min(1, Math.max(0, fromR));
  const ap = actionPlan?.confidence_score;
  if (ap != null && ap !== '') {
    const n = typeof ap === 'number' ? ap : Number(ap);
    if (!Number.isNaN(n)) return Math.min(1, Math.max(0, n));
  }
  const ec = extracted?.confidence_score ?? 0;
  const n = typeof ec === 'number' ? ec : Number(ec);
  return Number.isNaN(n) ? 0 : Math.min(1, Math.max(0, n));
}

export default function ExtractionResults({ data }) {
  if (!data) return null;

  if (data.batch && data.job_id) {
    return (
      <section style={{ maxWidth: 720, margin: '0 auto', padding: '48px 24px', textAlign: 'center' }}>
        <div className="card" style={{ padding: 28 }}>
          <h2 className="text-section-title">Batch job queued</h2>
          <p style={{ fontSize: 14, color: 'var(--text-muted)', marginTop: 12 }}>
            Job ID <strong style={{ fontFamily: 'monospace' }}>{data.job_id}</strong> — poll{' '}
            <span style={{ fontFamily: 'monospace' }}>{`/api/batch-status/${data.job_id}`}</span>
          </p>
          <p style={{ fontSize: 13, marginTop: 8 }}>
            Files enqueued: <strong>{data.files_enqueued}</strong>
          </p>
        </div>
      </section>
    );
  }

  const extracted = data.extracted_data || data;
  const actionPlan = data.action_plan || null;
  const reasoning = data.action_plan_reasoning || {};
  const fusedUi = resolveFusedScore(reasoning, extracted, actionPlan);
  const displayStatus = data.workflow_status || data.status || data.action_status;

  return (
    <section style={{ maxWidth: 720, margin: '0 auto', padding: '48px 24px' }}>
      <div className="animate-fade-in-up" style={{ textAlign: 'center', marginBottom: 40 }}>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 16px',
            borderRadius: 'var(--radius-full)',
            background: 'var(--success-muted)',
            border: '1px solid rgba(16, 185, 129, 0.2)',
            marginBottom: 16,
          }}
        >
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--success)' }} />
          <span style={{ fontSize: 13, color: 'var(--success-text)', fontWeight: 600 }}>
            Extraction Complete
          </span>
        </div>
        <h2 className="text-section-title" style={{ marginBottom: 8 }}>Extracted Actions</h2>
          <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>Structured data extracted by LLaMA3 + governance classifier stack</p>
      </div>

      {/* Confidence Score Card */}
      <div
        className="card animate-fade-in-up"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 20,
          gap: 20,
          flexWrap: 'wrap',
        }}
      >
        <div>
          <p className="text-caption" style={{ marginBottom: 4 }}>Final confidence (fused)</p>
          <p style={{ fontSize: 28, fontWeight: 800, color: 'var(--text-primary)', fontFamily: 'monospace', letterSpacing: '-0.02em' }}>
            {(fusedUi * 100).toFixed(2)}%
          </p>
        </div>
        <ConfidenceGauge
          score={fusedUi}
          size={90}
          showLabel={false}
          gaugeSubtitle="Final Confidence Score"
          percentFractionDigits={2}
        />
      </div>

      {actionPlan && (
        <div className="card animate-fade-in-up" style={{ marginBottom: 20, padding: 20 }}>
          <p className="text-caption" style={{ marginBottom: 12 }}>Action plan preview</p>
          <pre
            style={{
              whiteSpace: 'pre-wrap',
              fontSize: 12,
              lineHeight: 1.65,
              color: 'var(--text-secondary)',
            }}
          >
            {JSON.stringify(actionPlan, null, 2)}
          </pre>
        </div>
      )}

      {/* Result Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
        {fieldConfig.map(({ key, label, icon: Icon }, index) => {
          const value = formatValue(key, extracted[key]);
          return (
            <div
              key={key}
              className="card card-interactive animate-fade-in-up"
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 14,
                padding: 20,
                animationDelay: `${index * 0.08}s`,
              }}
            >
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--primary-muted)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <Icon size={18} style={{ color: 'var(--primary)' }} />
              </div>
              <div style={{ minWidth: 0 }}>
                <p className="text-caption" style={{ marginBottom: 4 }}>{label}</p>
                <p
                  style={{
                    fontSize: 14,
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    wordBreak: 'break-word',
                  }}
                >
                  {value}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Status Badge */}
      {displayStatus && (
        <div className="animate-fade-in-up" style={{ textAlign: 'center', marginTop: 24 }}>
          <span className="chip chip-pending">
            <Clock size={12} />
            Status: {displayStatus}
          </span>
        </div>
      )}

      {/* Raw JSON Toggle */}
      <details
        className="animate-fade-in-up"
        style={{
          marginTop: 24,
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-default)',
          overflow: 'hidden',
        }}
      >
        <summary
          style={{
            padding: '12px 20px',
            background: 'var(--bg-card)',
            color: 'var(--text-muted)',
            fontSize: 13,
            cursor: 'pointer',
            fontWeight: 500,
          }}
        >
          View Raw JSON
        </summary>
        <pre
          style={{
            padding: 20,
            fontSize: 12,
            color: 'var(--text-secondary)',
            overflowX: 'auto',
            background: 'var(--bg-surface)',
            lineHeight: 1.6,
          }}
        >
          {JSON.stringify(extracted, null, 2)}
        </pre>
      </details>
    </section>
  );
}
