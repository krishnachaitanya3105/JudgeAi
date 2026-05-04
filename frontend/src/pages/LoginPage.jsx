import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { KeyRound, ShieldCheck, Scale, Sun, Moon, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../context/useAuth';
import { useTheme } from '../context/ThemeContext';

const roleOptions = [
  {
    id: 'officer',
    label: 'Officer Verification Portal',
    subtitle: 'Verification workflow, case review, and officer dashboard access',
    icon: ShieldCheck,
    gradient: 'linear-gradient(135deg, #6366f1 0%, #818cf8 100%)',
    iconBg: 'rgba(99, 102, 241, 0.12)',
  },
  {
    id: 'admin',
    label: 'Admin Analytics Console',
    subtitle: 'System analytics, officer management, and complete case visibility',
    icon: KeyRound,
    gradient: 'linear-gradient(135deg, #a78bfa 0%, #c084fc 100%)',
    iconBg: 'rgba(167, 139, 250, 0.12)',
  },
];

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, isAuthenticated, user, credentialsHint } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const [role, setRole] = useState('officer');
  const [email, setEmail] = useState(credentialsHint.officer.email);
  const [password, setPassword] = useState(credentialsHint.officer.password);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  if (isAuthenticated) {
    return <Navigate to={user.defaultRoute} replace />;
  }

  const handleRoleChange = (nextRole) => {
    setRole(nextRole);
    setEmail(credentialsHint[nextRole].email);
    setPassword(credentialsHint[nextRole].password);
    setError('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    const result = await login({ role, email, password });
    setSubmitting(false);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    navigate(result.user.defaultRoute, { replace: true });
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--bg-base)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 20px',
        position: 'relative',
        overflow: 'hidden',
        transition: 'background-color 0.3s ease',
      }}
    >
      {/* Background elements */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          overflow: 'hidden',
        }}
      >
        {/* Watermark pattern */}
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: 600,
            height: 600,
            opacity: 0.03,
          }}
        >
          <Scale style={{ width: '100%', height: '100%', color: 'var(--text-primary)' }} />
        </div>
        {/* Gradient orbs */}
        <div
          style={{
            position: 'absolute',
            top: -200,
            right: -200,
            width: 500,
            height: 500,
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(99, 102, 241, 0.08) 0%, transparent 70%)',
          }}
        />
        <div
          style={{
            position: 'absolute',
            bottom: -200,
            left: -200,
            width: 500,
            height: 500,
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(167, 139, 250, 0.06) 0%, transparent 70%)',
          }}
        />
      </div>

      {/* Theme toggle */}
      <button
        onClick={toggleTheme}
        style={{
          position: 'absolute',
          top: 24,
          right: 24,
          width: 40,
          height: 40,
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-default)',
          background: 'var(--bg-card)',
          color: 'var(--text-secondary)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.2s ease',
          zIndex: 10,
        }}
        aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      >
        {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
      </button>

      {/* Main Card */}
      <div
        className="animate-fade-in-up"
        style={{
          position: 'relative',
          zIndex: 5,
          width: '100%',
          maxWidth: 520,
        }}
      >
        {/* Logo Header */}
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 'var(--radius-lg)',
              background: 'linear-gradient(135deg, var(--primary), var(--accent-violet))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px',
              boxShadow: '0 8px 30px rgba(99, 102, 241, 0.3)',
            }}
          >
            <Scale style={{ width: 28, height: 28, color: 'white' }} />
          </div>
          <h1
            style={{
              fontSize: 28,
              fontWeight: 800,
              color: 'var(--text-primary)',
              letterSpacing: '-0.02em',
              marginBottom: 8,
            }}
          >
            JudgeAI Access Portal
          </h1>
          <p style={{ fontSize: 14, color: 'var(--text-muted)', lineHeight: 1.5 }}>
            Sign in to access the AI-powered legal case verification platform
          </p>
        </div>

        {/* Role Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 32 }}>
          {roleOptions.map((option) => {
            const Icon = option.icon;
            const active = role === option.id;
            return (
              <button
                key={option.id}
                type="button"
                onClick={() => handleRoleChange(option.id)}
                style={{
                  padding: 20,
                  borderRadius: 'var(--radius-lg)',
                  border: `2px solid ${active ? 'var(--primary)' : 'var(--border-default)'}`,
                  background: active ? 'var(--primary-muted)' : 'var(--bg-card)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                  transform: active ? 'scale(1.02)' : 'scale(1)',
                  boxShadow: active ? 'var(--shadow-glow)' : 'var(--shadow-sm)',
                  position: 'relative',
                  overflow: 'hidden',
                }}
              >
                {/* Active indicator bar */}
                {active && (
                  <div
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      height: 3,
                      background: option.gradient,
                      borderRadius: '0 0 4px 4px',
                    }}
                  />
                )}
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 'var(--radius-md)',
                    background: option.iconBg,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: 12,
                  }}
                >
                  <Icon
                    size={20}
                    style={{ color: active ? 'var(--primary)' : 'var(--text-muted)' }}
                  />
                </div>
                <p
                  style={{
                    fontSize: 14,
                    fontWeight: 700,
                    color: 'var(--text-primary)',
                    marginBottom: 4,
                  }}
                >
                  {option.label}
                </p>
                <p style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.4 }}>
                  {option.subtitle}
                </p>
              </button>
            );
          })}
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 16 }}>
            <label
              style={{
                display: 'block',
                fontSize: 13,
                fontWeight: 600,
                color: 'var(--text-secondary)',
                marginBottom: 6,
              }}
            >
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input"
              placeholder="Enter your email"
              required
              autoComplete="email"
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <label
              style={{
                display: 'block',
                fontSize: 13,
                fontWeight: 600,
                color: 'var(--text-secondary)',
                marginBottom: 6,
              }}
            >
              Password
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                style={{ paddingRight: 44 }}
                placeholder="Enter your password"
                required
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: 12,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: 4,
                }}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {error && (
            <div
              style={{
                padding: '12px 16px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--danger-muted)',
                color: 'var(--danger-text)',
                fontSize: 13,
                fontWeight: 500,
                marginBottom: 16,
              }}
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            style={{
              width: '100%',
              padding: '14px 24px',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              background: 'linear-gradient(135deg, var(--primary), var(--accent-violet))',
              color: 'white',
              fontSize: 15,
              fontWeight: 700,
              cursor: submitting ? 'wait' : 'pointer',
              opacity: submitting ? 0.7 : 1,
              transition: 'all 0.2s ease',
              boxShadow: '0 4px 16px rgba(99, 102, 241, 0.3)',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            {submitting ? (
              <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                <span
                  style={{
                    width: 16,
                    height: 16,
                    borderRadius: '50%',
                    border: '2px solid rgba(255,255,255,0.3)',
                    borderTopColor: 'white',
                    animation: 'spin 0.6s linear infinite',
                    display: 'inline-block',
                  }}
                />
                Signing in...
              </span>
            ) : (
              `Continue as ${role === 'admin' ? 'Admin' : 'Officer'}`
            )}
          </button>
        </form>

        {/* Footer */}
        <p
          style={{
            textAlign: 'center',
            fontSize: 11,
            color: 'var(--text-muted)',
            marginTop: 32,
            letterSpacing: '0.02em',
          }}
        >
          JudgeAI · AI-Powered Legal Governance Platform
        </p>
      </div>
    </div>
  );
}
