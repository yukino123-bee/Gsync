import { api } from './client';
import type { AuthResponse, Role, User } from '@/types';

export const authApi = {
  login: (email: string, password: string) =>
    api.post<AuthResponse>('/auth/login', { email, password }).then((r) => r.data),
  register: (name: string, email: string, password: string, role: Exclude<Role, 'admin'>) =>
    api.post<AuthResponse>('/auth/register', { name, email, password, role }).then((r) => r.data),
  me: () => api.get<User>('/auth/me').then((r) => r.data),
  setPushToken: (push_token: string | null) => api.put<User>('/auth/push-token', { push_token }).then((r) => r.data),
};
