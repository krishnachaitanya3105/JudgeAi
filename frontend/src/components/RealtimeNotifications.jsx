import { useEffect } from 'react';
import { supabase } from '../lib/supabase';
import toast from 'react-hot-toast';

/** Best-effort Supabase realtime for new deadline notifications (respects your RLS). */
export default function RealtimeNotifications() {
  useEffect(() => {
    try {
      const channel = supabase
        .channel('judgeai-notifications')
        .on(
          'postgres_changes',
          { event: 'INSERT', schema: 'public', table: 'notifications' },
          (payload) => {
            if (payload.new?.notification_type && payload.new.notification_type !== 'deadline_imminent') {
              return;
            }
            const row = payload.new;
            if (row?.message) {
              toast(row.message, { icon: '⏳', duration: 8000 });
            }
          }
        )
        .subscribe();
      return () => {
        supabase.removeChannel(channel);
      };
    } catch {
      /* no-op */
      return undefined;
    }
  }, []);
  return null;
}
