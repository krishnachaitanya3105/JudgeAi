import { Tooltip as RechartsTooltip } from 'recharts';

/**
 * Styled Recharts tooltip using our design tokens.
 */
export default function ChartTooltip(props) {
  return (
    <RechartsTooltip
      contentStyle={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border-default)',
        borderRadius: 'var(--radius-md)',
        padding: '12px 16px',
        boxShadow: 'var(--shadow-lg)',
        fontSize: 13,
      }}
      labelStyle={{
        color: 'var(--text-primary)',
        fontWeight: 600,
        marginBottom: 4,
      }}
      itemStyle={{
        color: 'var(--text-secondary)',
        fontSize: 13,
        padding: '2px 0',
      }}
      cursor={{ fill: 'var(--primary-muted)' }}
      {...props}
    />
  );
}
