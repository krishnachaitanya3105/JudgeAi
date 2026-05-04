import { Scale, ArrowDown } from 'lucide-react';

export default function Hero() {
  return (
    <section
      style={{
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '55vh',
        padding: '0 24px',
        textAlign: 'center',
        overflow: 'hidden',
      }}
    >
      {/* Background Effects */}
      <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
        <div
          className="animate-float"
          style={{
            position: 'absolute',
            top: '20%',
            left: '20%',
            width: 400,
            height: 400,
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(99, 102, 241, 0.08), transparent 70%)',
            filter: 'blur(60px)',
          }}
        />
        <div
          className="animate-float"
          style={{
            position: 'absolute',
            bottom: '20%',
            right: '20%',
            width: 350,
            height: 350,
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(167, 139, 250, 0.06), transparent 70%)',
            filter: 'blur(60px)',
            animationDelay: '3s',
          }}
        />
      </div>

      {/* Content */}
      <div style={{ position: 'relative', zIndex: 10 }} className="animate-fade-in-up">
        {/* Badge */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 16px',
            borderRadius: 'var(--radius-full)',
            background: 'var(--primary-muted)',
            border: '1px solid rgba(99, 102, 241, 0.2)',
            marginBottom: 32,
          }}
        >
          <Scale style={{ width: 14, height: 14, color: 'var(--primary)' }} />
          <span style={{ fontSize: 13, color: 'var(--primary)', fontWeight: 600 }}>
            AI-Powered Legal Analysis
          </span>
        </div>

        {/* Heading */}
        <h1 style={{ fontSize: 'clamp(36px, 6vw, 64px)', fontWeight: 900, letterSpacing: '-0.03em', lineHeight: 1.1, marginBottom: 24 }}>
          <span className="gradient-text">Court Judgments</span>
          <br />
          <span style={{ color: 'var(--text-primary)' }}>Decoded by AI</span>
        </h1>

        {/* Subtitle */}
        <p
          style={{
            fontSize: 'clamp(15px, 2vw, 18px)',
            color: 'var(--text-muted)',
            maxWidth: 600,
            margin: '0 auto 40px',
            lineHeight: 1.7,
          }}
        >
          Upload court judgment PDFs and let{' '}
          <span style={{ color: 'var(--primary)', fontWeight: 600 }}>LLaMA3</span> extract
          case numbers, deadlines, directives, and responsible departments — instantly.
        </p>

        {/* CTA */}
        <a
          href="#upload"
          className="btn btn-primary"
          style={{
            padding: '16px 32px',
            fontSize: 16,
            fontWeight: 700,
            borderRadius: 'var(--radius-lg)',
            textDecoration: 'none',
            boxShadow: '0 8px 30px rgba(99, 102, 241, 0.3)',
            transition: 'all 0.3s ease',
          }}
        >
          Get Started
          <ArrowDown style={{ width: 18, height: 18, animation: 'float 2s ease-in-out infinite' }} />
        </a>
      </div>

      {/* Stats Bar */}
      <div
        className="animate-fade-in-up"
        style={{
          position: 'relative',
          zIndex: 10,
          marginTop: 64,
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 32,
          maxWidth: 480,
          width: '100%',
          animationDelay: '0.3s',
        }}
      >
        {[
          { value: 'LLaMA3', label: 'AI Engine' },
          { value: '< 10s', label: 'Extraction' },
          { value: '95%+', label: 'Accuracy' },
        ].map((stat) => (
          <div key={stat.label} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)' }}>{stat.value}</div>
            <div className="text-caption" style={{ marginTop: 4 }}>{stat.label}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
