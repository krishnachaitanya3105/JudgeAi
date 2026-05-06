import { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  CheckCircle,
  Clock,
  TrendingUp,
  Search,
  ChevronRight,
  FileText,
  Calendar,
} from 'lucide-react';
import { getOfficerDashboard, getCases } from '../lib/api';
import toast from 'react-hot-toast';
import StatCard from '../components/ui/StatCard';
import StatusChip from '../components/ui/StatusChip';
import EmptyState from '../components/ui/EmptyState';
import { SkeletonCard } from '../components/ui/Skeleton';

export default function OfficerDashboard() {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [pendingCases, setPendingCases] = useState([]);
  const [departmentFilter, setDepartmentFilter] = useState('');
  const [caseSearch, setCaseSearch] = useState('');       // raw input (unthrottled)
  const [debouncedSearch, setDebouncedSearch] = useState(''); // debounced (used in API)
  const searchTimerRef = useRef(null);
  const [error, setError] = useState('');

  // Debounce caseSearch → debouncedSearch (350 ms)
  useEffect(() => {
    clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      setDebouncedSearch(caseSearch.trim());
    }, 350);
    return () => clearTimeout(searchTimerRef.current);
  }, [caseSearch]);

  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      try {
        // Parallel fetch: dashboard stats + pending cases
        const [data, pendingData] = await Promise.all([
          getOfficerDashboard(departmentFilter || null),
          getCases(0, 50, 'pending', departmentFilter || null, debouncedSearch || null),
        ]);
        if (cancelled) return;
        setDashboard(data);
        setPendingCases(pendingData.data || []);
      } catch (err) {
        if (cancelled) return;
        const message = err.response?.data?.detail || err.message || 'Failed to load dashboard';
        setError(message);
        toast.error(message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchData();
    return () => { cancelled = true; };
  }, [departmentFilter, debouncedSearch]);

  const getDeadlineChip = (deadline) => {
    if (!deadline) return <span className="text-metadata">No deadline</span>;
    const now = new Date();
    const target = new Date(deadline);
    const diffMs = target.getTime() - now.getTime();
    const days = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
    if (Number.isNaN(days)) return <span className="text-metadata">Invalid date</span>;
    if (days < 0)
      return (
        <span className="chip chip-rejected">Overdue</span>
      );
    if (days < 3)
      return (
        <span className="chip chip-rejected">{days}d urgent</span>
      );
    if (days < 7)
      return (
        <span className="chip chip-pending">{days}d remaining</span>
      );
    return (
      <span className="chip chip-approved">{days}d left</span>
    );
  };

  if (loading) {
    return (
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        {/* Breadcrumb */}
        <div className="breadcrumb" style={{ marginBottom: 24 }}>
          <span className="current">Dashboard</span>
        </div>
        <h1 className="text-page-title" style={{ marginBottom: 32 }}>Officer Dashboard</h1>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: 16 }}>
          {[1, 2, 3, 4].map((i) => (
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
            <h3 style={{ fontWeight: 600, color: 'var(--danger-text)', marginBottom: 4 }}>
              Error Loading Dashboard
            </h3>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)' }}>{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1280, margin: '0 auto' }} className="animate-fade-in">
      {/* Breadcrumb */}
      <div className="breadcrumb" style={{ marginBottom: 8 }}>
        <span className="current">Dashboard</span>
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
          <h1 className="text-page-title" style={{ marginBottom: 4 }}>Officer Dashboard</h1>
          <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>
            Monitor cases, track deadlines, and manage verification workflow
          </p>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 24, maxWidth: 600 }}>
        <div style={{ position: 'relative' }}>
          <select
            value={departmentFilter}
            onChange={(e) => setDepartmentFilter(e.target.value)}
            className="input"
            style={{ appearance: 'none', paddingRight: 36, cursor: 'pointer' }}
          >
            <option value="">All Departments</option>
            <option value="Ministry of Environment">Ministry of Environment</option>
            <option value="Revenue Department">Revenue Department</option>
            <option value="Home Department">Home Department</option>
          </select>
          <ChevronRight
            size={14}
            style={{
              position: 'absolute',
              right: 12,
              top: '50%',
              transform: 'translateY(-50%) rotate(90deg)',
              color: 'var(--text-muted)',
              pointerEvents: 'none',
            }}
          />
        </div>
        <div style={{ position: 'relative' }}>
          <Search
            size={16}
            style={{
              position: 'absolute',
              left: 12,
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--text-muted)',
            }}
          />
          <input
            value={caseSearch}
            onChange={(e) => setCaseSearch(e.target.value)}
            placeholder="Search by case number..."
            className="input"
            style={{ paddingLeft: 36 }}
          />
        </div>
      </div>

      {/* Section: System Overview */}
      <h2
        className="text-caption"
        style={{ marginBottom: 16, paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}
      >
        System Overview
      </h2>

      {/* Stats Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))',
          gap: 16,
          marginBottom: 40,
        }}
      >
        <StatCard
          title="Pending Cases"
          value={dashboard?.pending_cases || 0}
          icon={Clock}
          color="var(--warning)"
          trend={dashboard?.pending_cases > 0 ? 'up' : 'neutral'}
          subtitle="awaiting review"
        />
        <StatCard
          title="Approved Cases"
          value={dashboard?.approved_cases || 0}
          icon={CheckCircle}
          color="var(--success)"
          trend="up"
          subtitle="verified"
        />
        <StatCard
          title="Completed Cases"
          value={dashboard?.completed_cases || 0}
          icon={TrendingUp}
          color="var(--info)"
          subtitle="total processed"
        />
        <StatCard
          title="Urgent Deadlines"
          value={dashboard?.urgent_deadlines || 0}
          icon={AlertCircle}
          color="var(--danger)"
          trend={dashboard?.urgent_deadlines > 0 ? 'up' : 'neutral'}
          subtitle="< 3 days"
        />
      </div>

      {/* Section: Recent Activity */}
      <h2
        className="text-caption"
        style={{ marginBottom: 16, paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}
      >
        Recent Activity
      </h2>

      {/* Recent Uploads */}
      <div className="card" style={{ marginBottom: 40 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 20,
          }}
        >
          <h3 className="text-section-title">Recent Uploads</h3>
          <span className="text-metadata">
            {dashboard?.recent_uploads?.length || 0} entries
          </span>
        </div>

        {dashboard?.recent_uploads && dashboard.recent_uploads.length > 0 ? (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Case Number</th>
                  <th>Uploaded By</th>
                  <th>Created At</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {dashboard.recent_uploads.map((item) => (
                  <tr key={item.id}>
                    <td>
                      {item.action_id ? (
                        <Link
                          to={`/case/${item.action_id}`}
                          style={{ fontFamily: 'monospace', color: 'var(--primary)', fontWeight: 600, fontSize: 13, textDecoration: 'none' }}
                        >
                          {item.case_number}
                        </Link>
                      ) : (
                        <span style={{ fontFamily: 'monospace', color: 'var(--text-muted)', fontWeight: 600, fontSize: 13 }}>
                          {item.case_number}
                        </span>
                      )}
                    </td>
                    <td style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div
                        style={{
                          width: 24,
                          height: 24,
                          borderRadius: 'var(--radius-full)',
                          background: 'var(--primary-muted)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: 10,
                          fontWeight: 700,
                          color: 'var(--primary)',
                        }}
                      >
                        {(item.uploaded_by || 'S')[0].toUpperCase()}
                      </div>
                      {item.uploaded_by}
                    </td>
                    <td>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Calendar size={12} style={{ color: 'var(--text-muted)' }} />
                        {new Date(item.created_at).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </span>
                    </td>
                    <td>
                      {item.action_id ? (
                        <Link to={`/case/${item.action_id}`} style={{ display: 'inline-flex', color: 'var(--text-muted)' }} aria-label="Open case details">
                          <ChevronRight size={14} />
                        </Link>
                      ) : (
                        <ChevronRight size={14} style={{ color: 'var(--text-muted)', opacity: 0.4 }} />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState preset="no-data" />
        )}
      </div>

      {/* Section: Verification Queue */}
      <h2
        className="text-caption"
        style={{ marginBottom: 16, paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}
      >
        Verification Queue
      </h2>

      <div className="card">
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 20,
          }}
        >
          <h3 className="text-section-title">Pending Verification</h3>
          <StatusChip status="pending" size="md" />
        </div>

        {pendingCases.length ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {pendingCases.map((item) => (
              <Link
                key={item.id}
                to={`/case/${item.id}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '14px 16px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  background: 'var(--bg-surface)',
                  textDecoration: 'none',
                  transition: 'all 0.2s ease',
                  cursor: 'pointer',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--primary)';
                  e.currentTarget.style.background = 'var(--primary-muted)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border-subtle)';
                  e.currentTarget.style.background = 'var(--bg-surface)';
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: 'var(--radius-sm)',
                      background: 'var(--primary-muted)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <FileText size={16} style={{ color: 'var(--primary)' }} />
                  </div>
                  <div>
                    <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'monospace' }}>
                      {item.case_number}
                    </p>
                    <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                      {item.department || 'Unassigned Department'}
                    </p>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  {getDeadlineChip(item.deadline)}
                  <ChevronRight size={16} style={{ color: 'var(--text-muted)' }} />
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <EmptyState preset="no-cases" />
        )}
      </div>
    </div>
  );
}
