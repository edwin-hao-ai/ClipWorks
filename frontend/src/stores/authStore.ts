import { create } from 'zustand';
import { User } from '@/lib/types';
import { api } from '@/lib/api';
import { DEMO_USER } from '@/lib/demoData';

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (provider: 'google' | 'github') => Promise<void>;
  logout: () => void;
  fetchMe: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: true,
  login: async (provider) => {
    try {
      const data = await api.post(`/auth/mock-login?provider=${provider}`);
      set({ user: data.user });
    } catch {
      // Demo fallback: pretend login succeeded with demo user
      set({ user: { ...DEMO_USER, provider } });
    }
    if (typeof window !== 'undefined') {
      window.location.href = '/projects';
    }
  },
  logout: () => {
    set({ user: null });
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  },
  fetchMe: async () => {
    try {
      const data = await api.get('/auth/me');
      set({ user: data.user ?? DEMO_USER, loading: false });
    } catch {
      set({ user: DEMO_USER, loading: false });
    }
  },
}));
