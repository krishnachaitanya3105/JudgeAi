import { useEffect, useState } from 'react';
import {
  AlertCircle,
  BarChart3,
  TrendingDown,
  Users,
  Download,
  Calendar,
  UserPlus,
  X,
  CheckCircle,
  Activity,
  PieChart as PieIcon,
  Clock,
} from 'lucide-react';
import { getAdminDashboard } from '../lib/api';
import { supabase } from '../lib/supabase';
import toast from 'react-hot-toast';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  CartesianGrid,
  Legend,
  Area,
  AreaChart,
} from 'recharts';
import StatCard from '../components/ui/StatCard';
import StatusChip from '../components/ui/StatusChip';
import ChartTooltip from '../components/ui/ChartTooltip';
import EmptyState from '../components/ui/EmptyState';
import { SkeletonCard } from '../components/ui/Skeleton';

const CHART_COLORS = {
  primary: '#6366f1',
  success: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444',
  info: '#3b82f6',
  violet: '#a78bfa',
  cyan: '#22d3ee',
};

const PIE_COLORS = ['#6366f1', '#10b981', '#ef4444', '#f59e0b', '#a78bfa'];

export default function AdminDashboard() {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState('');
  const [showCreateOfficer, setShowCreateOfficer] = useState(false);
  const [officerForm, setOfficerForm] = useState({ email: '', password: '', full_name: '' });
  const [creatingOfficer, setCreatingOfficer] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await getAdminDashboard();
        setDashboard(data);
      } catch (err) {
        const message = err.response?.data?.detail || err.message || 'Failed to load dashboard';
        setError(message);
        toast.error(message);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleCreateOfficer = async (e) => {
    e.preventDefault();
    if (!officerForm.email || !officerForm.password || !officerForm.full_name) {
      toast.error('Please fill in all fields');
      return;
    }

    setCreatingOfficer(true);
    try {
      // Create auth user via Supabase
      const { data: authData, error: authError } = await supabase.auth.signUp({
        email: officerForm.email,
        password: officerForm.password,
        options: {
          data: { full_name: officerForm.full_name, role: 'officer' },
        },
      });

      if (authError) throw authError;

      // Insert into users table
      const { error: profileError } = await supabase.from('users').insert({
        id: authData.user?.id,
        email: officerForm.email,
        full_name: officerForm.full_name,
        role: 'officer',
      });

      if (profileError) {
        console.warn('Profile insert warning:', profileError.message);
      }

      toast.success(`Officer "${officerForm.full_name}" created successfully`);
      setOfficerForm({ email: '', password: '', full_name: '' });
      setShowCreateOfficer(false);
    } catch (err) {
      toast.error(err.message || 'Failed to create officer');
    } finally {
      setCreatingOfficer(false);
    }
  };

  const csvEscape = (cell) => {
    const s = cell === null || cell === undefined ? '' : String(cell);
    if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
    return s;
  };

  const downloadCSV = () => {
    if (!dashboard) return;
    const rows = [['Metric', 'Value']];
    rows.push(['Total Cases', dashboard.total_cases]);
    Object.entries(dashboard.verification_counts || {}).forEach(([k, v]) => {
      rows.push([`Verification: ${k}`, v]);
    });
    Object.entries(dashboard.status_distribution || {}).forEach(([k, v]) => {
      rows.push([`Status: ${k}`, v]);
    });

    const fa = dashboard.confidence_fusion_analytics || {};
    if (fa.rows_with_fusion_reasoning != null) {
      rows.push([]);
      rows.push(['Confidence fusion summary', '']);
      rows.push([
        'Rows with action_plan_reasoning / fusion',
        fa.rows_with_fusion_reasoning,
      ]);
      if (fa.neutral_imputation_reference != null) {
        rows.push([
          'Neutral imputation constant (missing subsystem)',
          fa.neutral_imputation_reference,
        ]);
      }
      if (fa.default_weights_reference && typeof fa.default_weights_reference === 'object') {
        Object.entries(fa.default_weights_reference).forEach(([k, v]) => {
          rows.push([`Fusion default weight (${k})`, v]);
        });
      }
      const fin = fa.final_action_plan_confidence || {};
      ['count', 'mean', 'min', 'max', 'pstdev'].forEach((k) => {
        if (fin[k] != null) rows.push([`Final fused score ${k}`, fin[k]]);
      });
      const sub = fa.subsystem_effective_clamped01 || {};
      Object.entries(sub).forEach(([sys, agg]) => {
        if (!agg || typeof agg !== 'object') return;
        ['count', 'mean', 'min', 'max', 'pstdev'].forEach((mk) => {
          if (agg[mk] != null) rows.push([`Subsystem ${sys} effective ${mk}`, agg[mk]]);
        });
      });
      if (fa.raw_signal_present_count && typeof fa.raw_signal_present_count === 'object') {
        Object.entries(fa.raw_signal_present_count).forEach(([k, v]) => {
          rows.push([`Raw signal present count (${k})`, v]);
        });
      }
      if (fa.subsystem_imputed_count && typeof fa.subsystem_imputed_count === 'object') {
        Object.entries(fa.subsystem_imputed_count).forEach(([k, v]) => {
          rows.push([`Subsystem imputed count (${k})`, v]);
        });
      }
      const snaps = fa.per_action_fusion_snapshot || [];
      if (snaps.length > 0) {
        rows.push([]);
        rows.push(['Per-action fusion snapshot (JSON)', '']);
        snaps.forEach((snap) => {
          rows.push(['fusion_snapshot_json', JSON.stringify(snap)]);
        });
      }
    }

    const csv = rows.map((r) => r.map(csvEscape).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `judgeai-analytics-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('CSV downloaded');
  };

  if (loading) {
    return (
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <div className="breadcrumb" style={{ marginBottom: 24 }}>
          <span className="current">Admin Panel</span>
        </div>
        <h1 className="text-page-title" style={{ marginBottom: 32 }}>Admin Dashboard</h1>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: 16 }}>
          {[1, 2, 3].map((i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <div
          className="card"
          style={{
            display: 'flex',
            gap: 16,
            alignItems: 'flex-start',
            borderColor: 'var(--danger)',
            background: 'var(--danger-muted)',
          }}
        >
          <AlertCircle size={20} style={{ color: 'var(--danger)', flexShrink: 0, marginTop: 2 }} />
          <div>
            <h3 style={{ fontWeight: 600, color: 'var(--danger-text)', marginBottom: 4 }}>Error</h3>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)' }}>{error}</p>
          </div>
        </div>
      </div>
    );
  }

  const verificationAccuracy = dashboard?.verification_counts
    ? (() => {
        const total =
          (dashboard.verification_counts.approved || 0) +
          (dashboard.verification_counts.edited || 0) +
          (dashboard.verification_counts.rejected || 0);
        if (total === 0) return 0;
        return Math.round(
          ((dashboard.verification_counts.approved || 0) / total) * 100
        );
      })()
    : 0;

  return (
    <div style={{ maxWidth: 1280, margin: '0 auto' }} className="animate-fade-in">
      {/* Breadcrumb */}
      <div className="breadcrumb" style={{ marginBottom: 8 }}>
        <span className="current">Admin Panel</span>
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
        <div>
          <h1 className="text-page-title" style={{ marginBottom: 4 }}>Admin Dashboard</h1>
          <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>
            System-wide analytics, officer management, and performance metrics
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-ghost" onClick={downloadCSV}>
            <Download size={16} />
            Export CSV
          </button>
          <button className="btn btn-primary" onClick={() => setShowCreateOfficer(true)}>
            <UserPlus size={16} />
            Create Officer
          </button>
        </div>
      </div>

      {/* Create Officer Modal */}
      {showCreateOfficer && (
        <div className="modal-overlay" onClick={() => setShowCreateOfficer(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--primary-muted)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <UserPlus size={20} style={{ color: 'var(--primary)' }} />
                </div>
                <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>Create New Officer</h3>
              </div>
              <button
                onClick={() => setShowCreateOfficer(false)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 4 }}
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCreateOfficer}>
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                  Full Name
                </label>
                <input
                  type="text"
                  value={officerForm.full_name}
                  onChange={(e) => setOfficerForm({ ...officerForm, full_name: e.target.value })}
                  className="input"
                  placeholder="Officer full name"
                  required
                />
              </div>
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                  Email
                </label>
                <input
                  type="email"
                  value={officerForm.email}
                  onChange={(e) => setOfficerForm({ ...officerForm, email: e.target.value })}
                  className="input"
                  placeholder="officer@judgeai.local"
                  required
                />
              </div>
              <div style={{ marginBottom: 24 }}>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                  Password
                </label>
                <input
                  type="password"
                  value={officerForm.password}
                  onChange={(e) => setOfficerForm({ ...officerForm, password: e.target.value })}
                  className="input"
                  placeholder="Minimum 6 characters"
                  required
                  minLength={6}
                />
              </div>
              <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn-ghost" onClick={() => setShowCreateOfficer(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={creatingOfficer}>
                  {creatingOfficer ? 'Creating...' : 'Create Officer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Section: System Overview */}
      <h2
        className="text-caption"
        style={{ marginBottom: 16, paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}
      >
        System Overview
      </h2>

      {/* Key Metrics */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))',
          gap: 16,
          marginBottom: 40,
        }}
      >
        <StatCard
          title="Total Cases"
          value={dashboard?.total_cases || 0}
          icon={BarChart3}
          color="var(--info)"
          subtitle="in system"
        />
        <StatCard
          title="Active Departments"
          value={dashboard?.department_stats ? Object.keys(dashboard.department_stats).length : 0}
          icon={Users}
          color="var(--accent-violet)"
          subtitle="departments"
        />
        <StatCard
          title="Pending Verification"
          value={dashboard?.verification_counts?.pending || 0}
          icon={Clock}
          color="var(--warning)"
          trend={(dashboard?.verification_counts?.pending || 0) > 0 ? 'up' : 'neutral'}
          subtitle="awaiting action"
        />
        <StatCard
          title="Verification Accuracy"
          value={`${verificationAccuracy}%`}
          icon={CheckCircle}
          color="var(--success)"
          trend={verificationAccuracy > 70 ? 'up' : verificationAccuracy > 40 ? 'neutral' : 'down'}
          subtitle="approval rate"
        />
      </div>

      <h2
        className="text-caption"
        style={{ marginBottom: 16, paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}
      >
        Government decision intelligence
      </h2>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
          gap: 16,
          marginBottom: 32,
        }}
      >
        {[
          {
            title: 'Appeal recommended cases',
            color: CHART_COLORS.violet,
            rows: dashboard?.appeal_recommended_cases || [],
            keyFn: (r) => r.id || r.case_number,
          },
          {
            title: 'Compliance required',
            color: CHART_COLORS.warning,
            rows: dashboard?.compliance_required_cases || [],
            keyFn: (r) => r.id || r.case_number,
          },
          {
            title: 'Upcoming deadlines (7 days)',
            color: CHART_COLORS.info,
            rows: dashboard?.upcoming_deadlines_7_days || [],
            keyFn: (r) => `${r.case_number}-${r.deadline}`,
          },
          {
            title: 'Department pending backlog',
            color: CHART_COLORS.primary,
            rows: dashboard?.department_pending_breakdown || [],
            keyFn: (r) => r.department,
          },
        ].map((block) => (
          <div key={block.title} className="card" style={{ display: 'flex', flexDirection: 'column', minHeight: 220 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <div
                style={{
                  width: 8,
                  height: 36,
                  borderRadius: 'var(--radius-sm)',
                  background: block.color,
                }}
              />
              <h3 className="text-card-title" style={{ margin: 0 }}>{block.title}</h3>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', maxHeight: 220, fontSize: 13, color: 'var(--text-secondary)' }}>
              {block.rows.length === 0 && <p style={{ color: 'var(--text-muted)' }}>None right now.</p>}
              {(block.rows || []).slice(0, 8).map((row) => (
                <div
                  key={block.keyFn(row)}
                  style={{
                    padding: '10px 0',
                    borderBottom: '1px solid var(--border-subtle)',
                    lineHeight: 1.45,
                  }}
                >
                  {row.case_number !== undefined ? (
                    <>
                      <div style={{ fontWeight: 600 }}>{row.case_number}</div>
                      <div style={{ fontSize: 11, marginTop: 4 }}>{row.directive}</div>
                      {row.deadline !== undefined ? (
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                          Deadline: {row.deadline}
                          {typeof row.days_remaining === 'number' ? ` (${row.days_remaining}d)` : ''}
                        </div>
                      ) : null}
                    </>
                  ) : (
                    <>
                      <div style={{ fontWeight: 600 }}>{row.department}</div>
                      <div style={{ fontSize: 12, marginTop: 4 }}>
                        Pending: <strong>{row.pending}</strong>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Section: Analytics */}
      <h2
        className="text-caption"
        style={{ marginBottom: 16, paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}
      >
        Confidence fusion analytics
      </h2>
      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <Activity size={18} style={{ color: 'var(--primary)' }} />
          <h3 className="text-card-title" style={{ margin: 0 }}>
            Exact fusion statistics (stored reasoning)
          </h3>
        </div>
        {(() => {
          const fa = dashboard?.confidence_fusion_analytics || {};
          const n = fa.rows_with_fusion_reasoning ?? 0;
          const fin = fa.final_action_plan_confidence || {};
          const neu = fa.neutral_imputation_reference;
          const wref = fa.default_weights_reference || {};
          const totalActions = Object.values(dashboard?.verification_counts || {}).reduce((a, x) => a + (Number(x) || 0), 0);
          if (!n) {
            if (totalActions === 0) {
              return (
                <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 }}>
                  No extracted actions yet. Upload and process judgments to populate <code style={{ fontSize: 11 }}>action_plan_reasoning</code>.
                </p>
              );
            }
            return (
              <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 }}>
                {totalActions} action(s) exist but none carry a fusion ledger — re-run extraction with the current pipeline to backfill reasoning JSON.
              </p>
            );
          }
          return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>
                Aggregates over <strong>{n}</strong> extracted actions carrying{' '}
                <code style={{ fontSize: 11 }}>final_action_plan_confidence</code> and effective subsystem inputs (not LLM-only).
                {neu != null ? (
                  <>
                    {' '}
                    Neutral imputation when a signal is absent:{' '}
                    <span style={{ fontFamily: 'monospace' }}>{Number(neu).toFixed(8)}</span>.
                  </>
                ) : null}
              </p>
              {Object.keys(wref).length > 0 && (
                <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0 }}>
                  Reference weights — LLM:{Number(wref.llm ?? 0).toFixed(4)}, timeline:{Number(wref.timeline ?? 0).toFixed(4)},
                  department:{Number(wref.department ?? 0).toFixed(4)}, appeal:{Number(wref.appeal ?? 0).toFixed(4)}.
                </p>
              )}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
                  gap: 10,
                }}
              >
                {[
                  ['Mean final', fin.mean],
                  ['Min final', fin.min],
                  ['Max final', fin.max],
                  ['σ (final)', fin.pstdev],
                ].map(([label, val]) => (
                  <div
                    key={label}
                    style={{
                      padding: '12px',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border-subtle)',
                      background: 'var(--bg-surface)',
                    }}
                  >
                    <p className="text-caption" style={{ marginBottom: 4 }}>
                      {label}
                    </p>
                    <p style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>
                      {val != null ? Number(val).toFixed(8) : '—'}
                    </p>
                  </div>
                ))}
              </div>
              <div className="table-container">
                <table style={{ width: '100%', fontSize: 12 }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left', padding: '8px 6px' }}>Subsystem (effective)</th>
                      <th style={{ textAlign: 'right', padding: '8px 6px' }}>n</th>
                      <th style={{ textAlign: 'right', padding: '8px 6px' }}>mean</th>
                      <th style={{ textAlign: 'right', padding: '8px 6px' }}>min</th>
                      <th style={{ textAlign: 'right', padding: '8px 6px' }}>max</th>
                      <th style={{ textAlign: 'right', padding: '8px 6px' }}>pstdev</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(fa.subsystem_effective_clamped01 || {}).map(([sys, agg]) =>
                      agg && typeof agg === 'object' ? (
                        <tr key={sys}>
                          <td style={{ padding: '8px 6px', fontWeight: 600 }}>{sys}</td>
                          <td style={{ padding: '8px 6px', textAlign: 'right', fontFamily: 'monospace' }}>{agg.count ?? '—'}</td>
                          <td style={{ padding: '8px 6px', textAlign: 'right', fontFamily: 'monospace' }}>
                            {agg.mean != null ? Number(agg.mean).toFixed(8) : '—'}
                          </td>
                          <td style={{ padding: '8px 6px', textAlign: 'right', fontFamily: 'monospace' }}>
                            {agg.min != null ? Number(agg.min).toFixed(8) : '—'}
                          </td>
                          <td style={{ padding: '8px 6px', textAlign: 'right', fontFamily: 'monospace' }}>
                            {agg.max != null ? Number(agg.max).toFixed(8) : '—'}
                          </td>
                          <td style={{ padding: '8px 6px', textAlign: 'right', fontFamily: 'monospace' }}>
                            {agg.pstdev != null ? Number(agg.pstdev).toFixed(8) : '—'}
                          </td>
                        </tr>
                      ) : null,
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })()}
      </div>

      <h2
        className="text-caption"
        style={{ marginBottom: 16, paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}
      >
        Performance Analytics
      </h2>

      {/* Charts Row 1 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 16, marginBottom: 16 }}>
        {/* Status Distribution Pie */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
            <PieIcon size={18} style={{ color: 'var(--primary)' }} />
            <h3 className="text-card-title">Status Distribution</h3>
          </div>
          <div style={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={Object.entries(dashboard?.status_distribution || {}).map(([name, value]) => ({
                    name: name.charAt(0).toUpperCase() + name.slice(1),
                    value,
                  }))}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={95}
                  innerRadius={55}
                  paddingAngle={3}
                  strokeWidth={0}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {PIE_COLORS.map((color, i) => (
                    <Cell key={i} fill={color} />
                  ))}
                </Pie>
                <ChartTooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Verification Stats Bar */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
            <BarChart3 size={18} style={{ color: 'var(--primary)' }} />
            <h3 className="text-card-title">Verification Stats</h3>
          </div>
          <div style={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={Object.entries(dashboard?.verification_counts || {}).map(([name, value]) => ({
                  name: name.charAt(0).toUpperCase() + name.slice(1),
                  value,
                }))}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
                <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                <ChartTooltip />
                <Bar dataKey="value" fill={CHART_COLORS.primary} radius={[6, 6, 0, 0]} maxBarSize={50} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 16, marginBottom: 40 }}>
        {/* Department Breakdown */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
            <Users size={18} style={{ color: 'var(--accent-violet)' }} />
            <h3 className="text-card-title">Cases per Department</h3>
          </div>
          <div style={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dashboard?.cases_processed_per_department || []} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" horizontal={false} />
                <XAxis type="number" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis
                  type="category"
                  dataKey="department"
                  stroke="var(--text-muted)"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  width={120}
                />
                <ChartTooltip />
                <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-muted)' }} />
                <Bar dataKey="total" fill={CHART_COLORS.violet} name="Total" radius={[0, 4, 4, 0]} maxBarSize={20} />
                <Bar dataKey="approved" fill={CHART_COLORS.success} name="Approved" radius={[0, 4, 4, 0]} maxBarSize={20} />
                <Bar dataKey="pending" fill={CHART_COLORS.warning} name="Pending" radius={[0, 4, 4, 0]} maxBarSize={20} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Accuracy Trend */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
            <Activity size={18} style={{ color: 'var(--success)' }} />
            <h3 className="text-card-title">Verification Accuracy Trend</h3>
          </div>
          <div style={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={dashboard?.verification_accuracy_trend || []}>
                <defs>
                  <linearGradient id="gradApproved" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={CHART_COLORS.success} stopOpacity={0.3} />
                    <stop offset="100%" stopColor={CHART_COLORS.success} stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradEdited" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={CHART_COLORS.warning} stopOpacity={0.3} />
                    <stop offset="100%" stopColor={CHART_COLORS.warning} stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradRejected" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={CHART_COLORS.danger} stopOpacity={0.3} />
                    <stop offset="100%" stopColor={CHART_COLORS.danger} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
                <XAxis dataKey="date" stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                <ChartTooltip />
                <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-muted)' }} />
                <Area type="monotone" dataKey="approved" stroke={CHART_COLORS.success} fill="url(#gradApproved)" strokeWidth={2} name="Approved" />
                <Area type="monotone" dataKey="edited" stroke={CHART_COLORS.warning} fill="url(#gradEdited)" strokeWidth={2} name="Edited" />
                <Area type="monotone" dataKey="rejected" stroke={CHART_COLORS.danger} fill="url(#gradRejected)" strokeWidth={2} name="Rejected" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Section: Deadline Alerts */}
      {dashboard?.deadline_alerts && dashboard.deadline_alerts.length > 0 && (
        <>
          <h2
            className="text-caption"
            style={{ marginBottom: 16, paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}
          >
            Deadline Alerts
          </h2>
          <div className="card" style={{ marginBottom: 40 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 300, overflowY: 'auto' }}>
              {dashboard.deadline_alerts.map((alert, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '14px 16px',
                    borderRadius: 'var(--radius-md)',
                    border: `1px solid ${alert.priority === 'urgent' ? 'var(--danger)' : 'var(--warning)'}`,
                    background: alert.priority === 'urgent' ? 'var(--danger-muted)' : 'var(--warning-muted)',
                    flexWrap: 'wrap',
                    gap: 8,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <AlertCircle
                      size={18}
                      style={{
                        color: alert.priority === 'urgent' ? 'var(--danger)' : 'var(--warning)',
                      }}
                    />
                    <div>
                      <p style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 14 }}>
                        {alert.case_number}
                      </p>
                      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                        <Calendar size={10} style={{ display: 'inline', marginRight: 4, verticalAlign: 'middle' }} />
                        {alert.deadline}
                      </p>
                    </div>
                  </div>
                  <span
                    style={{
                      fontSize: 13,
                      fontWeight: 700,
                      color: alert.priority === 'urgent' ? 'var(--danger-text)' : 'var(--warning-text)',
                    }}
                  >
                    {alert.days_remaining} days remaining
                  </span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Section: Recent Activities */}
      {dashboard?.recent_activities && dashboard.recent_activities.length > 0 && (
        <>
          <h2
            className="text-caption"
            style={{ marginBottom: 16, paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}
          >
            Recent Activity Log
          </h2>
          <div className="card">
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Action</th>
                    <th>Changed By</th>
                    <th>Details</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.recent_activities.map((activity) => (
                    <tr key={activity.id}>
                      <td>
                        <StatusChip status={
                          activity.action_type === 'status_change' || activity.action_type === 'approval'
                            ? 'approved'
                            : activity.action_type === 'rejection'
                            ? 'rejected'
                            : 'edited'
                        } />
                      </td>
                      <td style={{ fontSize: 13 }}>{activity.edited_by || 'System'}</td>
                      <td style={{ fontSize: 13, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {activity.old_value && activity.new_value
                          ? `${activity.old_value} → ${activity.new_value}`
                          : activity.action_type}
                      </td>
                      <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        {new Date(activity.timestamp).toLocaleString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          hour: 'numeric',
                          minute: '2-digit',
                        })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
