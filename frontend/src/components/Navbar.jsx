import {
  Scale,
  FileText,
  CheckSquare,
  LayoutDashboard,
  Shield,
  LogOut,
  Sun,
  Moon,
  Menu,
  X,
} from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { useTheme } from '../context/ThemeContext';
import { useState } from 'react';

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { role, logout, user } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const userRole = role || 'officer';
  const [mobileOpen, setMobileOpen] = useState(false);

  const onLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const navLinks = [
    { to: '/upload', label: 'Upload Cases', icon: FileText },
    { to: '/verification', label: 'Verify Queue', icon: CheckSquare },
    { to: '/officer-dashboard', label: 'Dashboard', icon: LayoutDashboard },
  ];

  if (userRole === 'admin') {
    navLinks.push({ to: '/admin-dashboard', label: 'Admin Panel', icon: Shield });
  }

  const isActive = (path) => location.pathname === path;

  return (
    <nav
      className="glass"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 50,
        borderBottom: '1px solid var(--nav-border)',
      }}
    >
      <div
        style={{
          maxWidth: 1280,
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          height: 64,
          padding: '0 24px',
        }}
      >
        {/* Logo */}
        <Link
          to="/"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            textDecoration: 'none',
            transition: 'opacity 0.2s',
          }}
          aria-label="JudgeAI Home"
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 'var(--radius-md)',
              background: 'linear-gradient(135deg, var(--primary), var(--accent-violet))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
            }}
          >
            <Scale style={{ width: 20, height: 20, color: 'white' }} />
          </div>
          <span
            className="gradient-text"
            style={{ fontSize: 20, fontWeight: 800, letterSpacing: '-0.02em' }}
          >
            JudgeAI
          </span>
        </Link>

        {/* Desktop Nav Links */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
          className="desktop-nav"
        >
          {navLinks.map((link) => {
            const Icon = link.icon;
            const active = isActive(link.to);
            return (
              <Link
                key={link.to}
                to={link.to}
                className={`nav-link ${active ? 'active' : ''}`}
                aria-current={active ? 'page' : undefined}
              >
                <Icon size={16} />
                <span className="nav-label">{link.label}</span>
              </Link>
            );
          })}
        </div>

        {/* Right side */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className="btn btn-ghost"
            style={{
              padding: '8px',
              borderRadius: 'var(--radius-sm)',
              width: 36,
              height: 36,
              minWidth: 36,
            }}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>

          {/* User badge */}
          <div
            className="user-badge"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '6px 14px',
              borderRadius: 'var(--radius-full)',
              border: '1px solid var(--border-default)',
              background: 'var(--bg-card)',
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: 'var(--success)',
                animation: 'pulse-glow 3s ease-in-out infinite',
              }}
            />
            <span
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: 'var(--text-secondary)',
              }}
            >
              {user?.name || 'User'}
              <span style={{ color: 'var(--text-muted)', margin: '0 4px' }}>·</span>
              <span style={{ color: 'var(--primary)', textTransform: 'capitalize' }}>{userRole}</span>
            </span>
          </div>

          {/* Logout */}
          <button
            onClick={onLogout}
            className="btn btn-ghost"
            style={{
              padding: '8px 14px',
              fontSize: 12,
              gap: 6,
            }}
            aria-label="Logout"
          >
            <LogOut size={14} />
            <span className="nav-label">Logout</span>
          </button>

          {/* Mobile hamburger */}
          <button
            className="btn btn-ghost mobile-menu-btn"
            style={{
              display: 'none',
              padding: 8,
              width: 36,
              height: 36,
              minWidth: 36,
            }}
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div
          style={{
            padding: '8px 16px 16px',
            borderTop: '1px solid var(--border-default)',
            background: 'var(--bg-surface)',
          }}
          className="mobile-nav"
        >
          {navLinks.map((link) => {
            const Icon = link.icon;
            const active = isActive(link.to);
            return (
              <Link
                key={link.to}
                to={link.to}
                onClick={() => setMobileOpen(false)}
                className={`nav-link ${active ? 'active' : ''}`}
                style={{ width: '100%', marginBottom: 4 }}
              >
                <Icon size={16} />
                {link.label}
              </Link>
            );
          })}
        </div>
      )}

      <style>{`
        @media (max-width: 768px) {
          .desktop-nav { display: none !important; }
          .mobile-menu-btn { display: flex !important; }
          .user-badge { display: none !important; }
          .nav-label { display: inline; }
        }
        @media (min-width: 769px) {
          .mobile-nav { display: none !important; }
        }
      `}</style>
    </nav>
  );
}
