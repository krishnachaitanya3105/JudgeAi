/**
 * Status chip badge component.
 * @param {{ status: string, size?: 'sm'|'md' }} props
 */
export default function StatusChip({ status, size = 'sm' }) {
  const config = {
    pending: { className: 'chip-pending', label: 'Pending', dot: 'var(--warning)' },
    approved: { className: 'chip-approved', label: 'Approved', dot: 'var(--success)' },
    rejected: { className: 'chip-rejected', label: 'Rejected', dot: 'var(--danger)' },
    edited: { className: 'chip-edited', label: 'Edited', dot: 'var(--info)' },
    completed: { className: 'chip-approved', label: 'Completed', dot: 'var(--success)' },
  };

  const c = config[status] || { className: '', label: status || 'Unknown', dot: 'var(--text-muted)' };

  const sizeStyles = size === 'md'
    ? { padding: '6px 16px', fontSize: 13 }
    : {};

  return (
    <span className={`chip ${c.className}`} style={sizeStyles}>
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: c.dot,
          flexShrink: 0,
        }}
      />
      {c.label}
    </span>
  );
}
