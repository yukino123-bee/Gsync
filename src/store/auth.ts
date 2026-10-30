import { create } from 'zustand';

import { authApi } from '@/api/auth';
import { setAuthFailureHandler } from '@/api/client';
import type { Role, User } from '@/types';
import { tokenStorage } from '@/utils/tokenStorage';

type Status = 'loading' | 'signedOut' | 'signedIn';

interface AuthState {
  user: User | null;
  status: Status;
  bootstrap: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string, role: Exclude<Role, 'admin'>) => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  status: 'loading',

  // Restore a saved session on app start
  async bootstrap() {
    try {
      const { access } = await tokenStorage.load();
      if (!access) return set({ user: null, status: 'signedOut' });
      const user = await authApi.me(); // the client refreshes an expired access token itself
      set({ user, status: 'signedIn' });
    } catch {
      // Invalid session or server unreachable: show login (tokens are kept if it was only the network)
      set({ user: null, status: 'signedOut' });
    }
  },

  async login(email, password) {
    const res = await authApi.login(email.trim(), password);
    await tokenStorage.save(res.access_token, res.refresh_token);
    set({ user: res.user, status: 'signedIn' });
  },

  async register(name, email, password, role) {
    const res = await authApi.register(name.trim(), email.trim(), password, role);
    await tokenStorage.save(res.access_token, res.refresh_token);
    set({ user: res.user, status: 'signedIn' });
  },

  async logout() {
    // Forget the push token server-side so a shared device stops receiving this user's alerts
    await authApi.setPushToken(null).catch(() => {});
    await tokenStorage.clear();
    set({ user: null, status: 'signedOut' });
  },
}));

setAuthFailureHandler(() => useAuth.setState({ user: null, status: 'signedOut' }));
