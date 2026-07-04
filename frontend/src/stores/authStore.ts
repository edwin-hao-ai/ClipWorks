import { create } from 'zustand';
import { User } from '@/lib/types';
import { api } from '@/lib/api';

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
    const data = await api.post(`/auth/mock-login?provider=${provider}`);
    set({ user: data.user });
    window.location.href = '/projects';
  },
  logout: () => {
    set({ user: null });
    window.location.href = '/login';
  },
  fetchMe: async () => {
    try {
      const data = await api.get('/auth/me');
      set({ user: data.user, loading: false });
    } catch {
      set({ user: null, loading: false });
    }
  },
}));
