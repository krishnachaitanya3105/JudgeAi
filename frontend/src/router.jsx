import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import Navbar from './components/Navbar';
import { useAuth } from './context/useAuth';

const HomePage = lazy(() => import('./pages/HomePage'));
const VerificationPage = lazy(() => import('./pages/VerificationPage'));
const OfficerDashboard = lazy(() => import('./pages/OfficerDashboard'));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'));
const CaseDetailsPage = lazy(() => import('./pages/CaseDetailsPage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));

function RouteLoader() {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '60vh',
      }}
    >
      <div
        style={{
          width: 40,
          height: 40,
          borderRadius: '50%',
          border: '3px solid var(--border-default)',
          borderTopColor: 'var(--primary)',
          animation: 'spin 0.8s linear infinite',
        }}
      />
    </div>
  );
}

function ProtectedRoute() {
  const { isAuthenticated, isAuthLoading } = useAuth();
  if (isAuthLoading) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          background: 'var(--bg-base)',
        }}
      >
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: '50%',
            border: '3px solid var(--border-default)',
            borderTopColor: 'var(--primary)',
            animation: 'spin 0.8s linear infinite',
          }}
        />
      </div>
    );
  }
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />;
}

function RoleRoute({ allow }) {
  const { role } = useAuth();
  if (!allow.includes(role)) {
    return <Navigate to={role === 'admin' ? '/admin-dashboard' : '/officer-dashboard'} replace />;
  }
  return <Outlet />;
}

function AppShell() {
  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--bg-base)',
        transition: 'background-color 0.3s ease',
      }}
    >
      <Navbar />
      <main style={{ padding: '88px 24px 48px', maxWidth: 1400, margin: '0 auto' }}>
        <Outlet />
      </main>
    </div>
  );
}

function RootRedirect() {
  const { isAuthenticated, role, isAuthLoading } = useAuth();
  if (isAuthLoading) return null;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Navigate to={role === 'admin' ? '/admin-dashboard' : '/officer-dashboard'} replace />;
}

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Suspense fallback={<RouteLoader />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<RootRedirect />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route path="/upload" element={<HomePage />} />
              <Route element={<RoleRoute allow={['officer', 'admin']} />}>
                <Route path="/verification" element={<VerificationPage />} />
                <Route path="/officer-dashboard" element={<OfficerDashboard />} />
                <Route path="/case/:id" element={<CaseDetailsPage />} />
              </Route>
              <Route element={<RoleRoute allow={['admin']} />}>
                <Route path="/admin-dashboard" element={<AdminDashboard />} />
              </Route>
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
