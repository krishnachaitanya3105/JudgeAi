/**
 * Skeleton loader for loading states.
 * @param {{ lines?: number, height?: number, width?: string, circle?: boolean }} props
 */
export default function Skeleton({ lines = 3, height = 14, width = '100%', circle = false }) {
  if (circle) {
    return <div className="skeleton skeleton-circle" style={{ width: height, height }} />;
  }

  return (
    <div style={{ width }}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="skeleton skeleton-line"
          style={{
            height,
            width: i === lines - 1 ? '60%' : '100%',
          }}
        />
      ))}
    </div>
  );
}

/**
 * Card-shaped skeleton loader.
 */
export function SkeletonCard() {
  return (
    <div className="card" style={{ padding: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
        <Skeleton circle height={40} />
        <Skeleton lines={1} height={16} width="50%" />
      </div>
      <Skeleton lines={3} />
    </div>
  );
}
