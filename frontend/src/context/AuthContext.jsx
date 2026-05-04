import { useCallback, useEffect, useMemo, useState } from 'react';
import { AuthContext, ROLE_CREDENTIALS } from './auth-core';
import { supabase } from '../lib/supabase';

const AUTH_REQUEST_TIMEOUT_MS = 7000;

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);

  const resolveRole = useCallback((preferredRole, email, profileRole) => {
    if (profileRole === 'admin' || profileRole === 'officer') return profileRole;
    if (preferredRole === 'admin' || preferredRole === 'officer') return preferredRole;
    if ((email || '').toLowerCase().includes('admin')) return 'admin';
    return 'officer';
  }, []);

  const normalizeUser = useCallback((authUser, preferredRole, profile) => {
    const role = resolveRole(preferredRole, authUser?.email, profile?.role);
    const account = ROLE_CREDENTIALS[role];
    return {
      role,
      email: authUser?.email,
      name: profile?.full_name || authUser?.user_metadata?.full_name || account?.name || 'User',
      defaultRoute: account?.defaultRoute || '/officer-dashboard',
      id: authUser?.id,
    };
  }, [resolveRole]);

  useEffect(() => {
    let active = true;
    const init = async () => {
      const { data: sessionData } = await supabase.auth.getSession();
      const authUser = sessionData?.session?.user;
      if (authUser && active) {
        // Render authenticated state immediately; hydrate profile details asynchronously.
        setUser(normalizeUser(authUser, null, null));
        supabase
          .from('users')
          .select('role, full_name')
          .eq('email', authUser.email)
          .maybeSingle()
          .then(({ data: profile }) => {
            if (!active) return;
            setUser(normalizeUser(authUser, null, profile));
          })
          .catch(() => {});
      }
      if (active) setIsAuthLoading(false);
    };
    init();

    const { data } = supabase.auth.onAuthStateChange(async (_event, session) => {
      if (!active) return;
      const authUser = session?.user;
      if (!authUser) {
        setUser(null);
        return;
      }
      setUser(normalizeUser(authUser, null, null));
      supabase
        .from('users')
        .select('role, full_name')
        .eq('email', authUser.email)
        .maybeSingle()
        .then(({ data: profile }) => {
          if (!active) return;
          setUser(normalizeUser(authUser, null, profile));
        })
        .catch(() => {});
    });

    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
  }, [normalizeUser]);

  const login = useCallback(async ({ role, email, password }) => {
    const account = ROLE_CREDENTIALS[role];
    if (!account) {
      return { ok: false, message: 'Unsupported role selected.' };
    }

    // Fast local fallback for demo credentials to avoid auth round-trip latency.
    if (email === account.email && password === account.password) {
      const fallbackUser = {
        role,
        email,
        name: account.name,
        defaultRoute: account.defaultRoute,
        isLocalFallback: true,
      };
      setUser(fallbackUser);
      return { ok: true, user: fallbackUser };
    }

    const timeoutError = {
      message: 'Login is taking too long. Please check network or Supabase availability.',
    };
    const authPromise = supabase.auth.signInWithPassword({ email, password });
    const timeoutPromise = new Promise((resolve) => {
      setTimeout(() => resolve({ data: null, error: timeoutError }), AUTH_REQUEST_TIMEOUT_MS);
    });
    const { data, error } = await Promise.race([authPromise, timeoutPromise]);

    if (error) {
      const msg = String(error.message || 'Login failed');
      if (msg.toLowerCase().includes('invalid login credentials')) {
        return {
          ok: false,
          message: 'Invalid email or password for this Supabase project.',
        };
      }
      return { ok: false, message: msg };
    }

    const authUser = data?.user;
    const authenticatedUser = normalizeUser(authUser, role, null);
    setUser(authenticatedUser);
    supabase
      .from('users')
      .select('role, full_name')
      .eq('email', email)
      .maybeSingle()
      .then(({ data: profile }) => {
        setUser(normalizeUser(authUser, role, profile));
      })
      .catch(() => {});
    return { ok: true, user: authenticatedUser };
  }, [normalizeUser]);

  const logout = useCallback(async () => {
    await supabase.auth.signOut();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      role: user?.role ?? null,
      isAuthenticated: Boolean(user),
      isAuthLoading,
      login,
      logout,
      credentialsHint: ROLE_CREDENTIALS,
    }),
    [user, isAuthLoading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
