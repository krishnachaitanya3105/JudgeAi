import AppRouter from './router';
import { Toaster } from 'react-hot-toast';
import { useTheme } from './context/useTheme';
import RealtimeNotifications from './components/RealtimeNotifications';

export default function App() {
  const { theme } = useTheme();

  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: theme === 'dark' ? '#1f2937' : '#ffffff',
            color: theme === 'dark' ? '#f1f5f9' : '#0f172a',
            border: `1px solid ${theme === 'dark' ? '#374151' : '#e2e8f0'}`,
            borderRadius: '12px',
            fontSize: '14px',
            boxShadow: theme === 'dark'
              ? '0 8px 30px rgba(0,0,0,0.45)'
              : '0 8px 30px rgba(0,0,0,0.1)',
          },
          success: {
            iconTheme: {
              primary: '#10b981',
              secondary: theme === 'dark' ? '#1f2937' : '#ffffff',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: theme === 'dark' ? '#1f2937' : '#ffffff',
            },
          },
        }}
      />
      <RealtimeNotifications />
      <AppRouter />
    </>
  );
}
