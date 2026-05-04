import { Scale } from 'lucide-react';

export default function Footer() {
  return (
    <footer
      style={{
        borderTop: '1px solid var(--border-subtle)',
        marginTop: 80,
      }}
    >
      <div
        style={{
          maxWidth: 1280,
          margin: '0 auto',
          padding: '32px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 16,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Scale style={{ width: 14, height: 14, color: 'var(--primary)' }} />
          <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            JudgeAI &copy; {new Date().getFullYear()} — AI Legal Governance
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {['Powered by Groq LLaMA3', 'Supabase', 'FastAPI'].map((item, i) => (
            <span key={item} style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {i > 0 && <span style={{ marginRight: 16 }}>·</span>}
              {item}
            </span>
          ))}
        </div>
      </div>
    </footer>
  );
}
