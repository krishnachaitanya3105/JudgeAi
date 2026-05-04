import { FileX, Upload, Search, BarChart3 } from 'lucide-react';

const presets = {
  'no-cases': {
    icon: FileX,
    title: 'No pending cases',
    text: 'All cases have been processed. Upload a new judgment document to begin verification.',
  },
  'no-data': {
    icon: BarChart3,
    title: 'No data available',
    text: 'Analytics will appear here once cases are processed through the verification pipeline.',
  },
  'no-results': {
    icon: Search,
    title: 'No results found',
    text: 'Try adjusting your search or filter criteria to find what you\'re looking for.',
  },
  upload: {
    icon: Upload,
    title: 'Upload a judgment document',
    text: 'Drop a court judgment PDF to begin AI-powered extraction and verification.',
  },
};

/**
 * Illustrated empty state placeholder.
 * @param {{ preset?: string, icon?: React.ElementType, title?: string, text?: string, action?: React.ReactNode }} props
 */
export default function EmptyState({ preset, icon, title, text, action }) {
  const p = preset ? presets[preset] : null;
  const Icon = icon || p?.icon || FileX;
  const heading = title || p?.title || 'Nothing here yet';
  const desc = text || p?.text || '';

  return (
    <div className="empty-state animate-fade-in">
      <div className="empty-state-icon">
        <Icon size={28} style={{ color: 'var(--primary)', opacity: 0.7 }} />
      </div>
      <h3 className="empty-state-title">{heading}</h3>
      {desc && <p className="empty-state-text">{desc}</p>}
      {action && <div style={{ marginTop: 20 }}>{action}</div>}
    </div>
  );
}
