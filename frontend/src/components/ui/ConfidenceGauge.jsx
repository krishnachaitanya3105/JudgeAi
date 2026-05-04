import { useEffect, useState } from 'react';

/**
 * Animated radial confidence gauge.
 * @param {{ score: number, size?: number, strokeWidth?: number, showLabel?: boolean }} props
 *   score: 0-1 (fraction), will be displayed as 0-100%
 */
export default function ConfidenceGauge({
  score = 0,
  size = 120,
  strokeWidth = 10,
  showLabel = true,
  gaugeSubtitle = null,
  /** 0 = whole percent; use 2–4 for audit-style display */
  percentFractionDigits = 0,
}) {
  const [animatedScore, setAnimatedScore] = useState(0);
  const pct = Math.min(Math.max(score * 100, 0), 100);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  useEffect(() => {
    const timer = setTimeout(() => setAnimatedScore(pct), 100);
    return () => clearTimeout(timer);
  }, [pct]);

  const dashArray = (animatedScore / 100) * circumference;

  const getColor = (val) => {
    if (val >= 70) return 'var(--success)';
    if (val >= 40) return 'var(--warning)';
    return 'var(--danger)';
  };

  const getLabel = (val) => {
    if (val >= 70) return 'HIGH CONFIDENCE';
    if (val >= 40) return 'MEDIUM CONFIDENCE';
    return 'LOW CONFIDENCE';
  };

  const getLabelColor = (val) => {
    if (val >= 70) return 'var(--success-text)';
    if (val >= 40) return 'var(--warning-text)';
    return 'var(--danger-text)';
  };

  const color = getColor(pct);

  return (
    <div className="gauge-container" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="gauge-svg">
        <circle
          className="gauge-track"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
        />
        <circle
          className="gauge-fill"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          stroke={color}
          strokeDasharray={`${dashArray} ${circumference}`}
          style={{ transition: 'stroke-dasharray 1.2s cubic-bezier(0.4, 0, 0.2, 1)' }}
        />
      </svg>
      <div className="gauge-center">
        <span
          style={{
            fontSize: size * 0.22,
            fontWeight: 800,
            color,
            lineHeight: 1,
          }}
        >
          {percentFractionDigits > 0
            ? `${animatedScore.toFixed(percentFractionDigits)}%`
            : `${Math.round(animatedScore)}%`}
        </span>
        {showLabel && (
          <span
            style={{
              fontSize: Math.max(size * 0.075, 9),
              fontWeight: 600,
              color: getLabelColor(pct),
              marginTop: 2,
              letterSpacing: '0.05em',
              textAlign: 'center',
              lineHeight: 1.2,
            }}
            title="Final Confidence Score blends LLM extraction, timeline parser, department classifier, and appeal recommender (weighted fusion)."
          >
            {getLabel(pct)}
          </span>
        )}
        {gaugeSubtitle && (
          <span
            style={{
              fontSize: Math.max(size * 0.065, 8),
              fontWeight: 700,
              color: 'var(--text-muted)',
              marginTop: 4,
              textAlign: 'center',
              letterSpacing: '0.08em',
            }}
          >
            {gaugeSubtitle}
          </span>
        )}
      </div>
    </div>
  );
}
