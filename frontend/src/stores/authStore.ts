import { create } from 'zustand';
import { User } from '@/lib/types';
import { api } from '@/lib/api';

interface AuthState {
  user: User | null;
  loading: boolean;
  loginLoading: boolean;
  loginError: string | null;
  login: (provider: 'google' | 'github') => Promise<void>;
  logout: () => Promise<void>;
  fetchMe: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: true,
  loginLoading: false,
  loginError: null,
  login: async (provider) => {
    set({ loginLoading: true, loginError: null });
    try {
      const data = await api.post(`/auth/mock-login?provider=${provider}`);
      set({ user: data.user, loginLoading: false, loginError: null });
      if (typeof window !== 'undefined') {
        window.location.href = '/projects';
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : '登录失败，请检查服务是否运行';
      set({ user: null, loginLoading: false, loginError: msg });
    }
  },
  logout: async () => {
    // 先通知服务端清除 session_user_id cookie；失败也忽略，确保本地退出仍可完成。
    try {
      await api.post('/auth/logout');
    } catch {
      // 忽略登出接口错误（如接口未实现/网络异常）。
    }
    set({ user: null });
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  },
  fetchMe: async () => {
    try {
      const data = await api.get('/auth/me');
      set({ user: data.user ?? null, loading: false });
    } catch {
      set({ user: null, loading: false });
    }
  },
}));
