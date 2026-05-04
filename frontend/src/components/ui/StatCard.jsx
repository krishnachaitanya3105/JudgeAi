import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

/**
 * Dashboard stat card with icon, value, trend indicator, and optional delta.
 * @param {{ title: string, value: string|number, icon: React.ElementType, color?: string, trend?: 'up'|'down'|'neutral', delta?: string, subtitle?: string }} props
 */
export default function StatCard({
  title,
  value,
  icon: Icon,
  color = 'var(--primary)',
  trend,
  delta,
  subtitle,
}) {
  const trendIcon = {
    up: <TrendingUp size={14} />,
    down: <TrendingDown size={14} />,
    neutral: <Minus size={14} />,
  };

  const trendColor = {
    up: 'var(--success-text)',
    down: 'var(--danger-text)',
    neutral: 'var(--text-muted)',
  };

  return (
    <div className="card card-interactive" style={{ cursor: 'default' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div style={{ flex: 1 }}>
          <p className="text-caption" style={{ marginBottom: 8 }}>{title}</p>
          <p style={{ fontSize: 32, fontWeight: 800, color, lineHeight: 1, marginBottom: 4 }}>
            {value}
          </p>
          {(trend || delta) && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 8 }}>
              {trend && (
                <span style={{ color: trendColor[trend], display: 'flex', alignItems: 'center' }}>
                  {trendIcon[trend]}
                </span>
              )}
              {delta && (
                <span style={{ fontSize: 12, fontWeight: 600, color: trendColor[trend || 'neutral'] }}>
                  {delta}
                </span>
              )}
              {subtitle && (
                <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 4 }}>
                  {subtitle}
                </span>
              )}
            </div>
          )}
          {!trend && !delta && subtitle && (
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{subtitle}</p>
          )}
        </div>
        {Icon && (
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 'var(--radius-md)',
              background: `color-mix(in srgb, ${color} 12%, transparent)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <Icon size={24} style={{ color, opacity: 0.8 }} />
          </div>
        )}
      </div>
    </div>
  );
}
