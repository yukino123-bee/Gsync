import { AxiosError, InternalAxiosRequestConfig, create, isAxiosError } from 'axios';

import { API_URL } from '@/utils/config';
import { tokenStorage } from '@/utils/tokenStorage';
import type { TokenPair } from '@/types';

export const api = create({
  baseURL: `${API_URL}/api/v1`,
  timeout: 20_000,
});

// Separate instance without interceptors, used only for token refresh
const bare = create({ timeout: 20_000 });

// Called when the refresh token is rejected, so the app can drop back to the login screen
let onAuthFailure: () => void = () => {};
export function setAuthFailureHandler(fn: () => void) {
  onAuthFailure = fn;
}

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean };

const AUTH_PATHS = ['/auth/login', '/auth/register', '/auth/refresh'];

api.interceptors.request.use((config) => {
  const token = tokenStorage.access;
  if (token) config.headers.set('Authorization', `Bearer ${token}`);
  return config;
});

// One refresh at a time: concurrent 401s all wait on the same promise
let refreshing: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokenStorage.refresh;
  if (!refresh) return null;
  try {
    // Bare axios call so this request doesn't go through the interceptors
    const { data } = await bare.post<TokenPair>(
      `${API_URL}/api/v1/auth/refresh`,
      { refresh_token: refresh },
    );
    await tokenStorage.save(data.access_token, data.refresh_token);
    return data.access_token;
  } catch (e) {
    // Only a rejected token ends the session; a network blip must not log the user out
    if (isAxiosError(e) && e.response?.status === 401) {
      await tokenStorage.clear();
      return null;
    }
    throw e;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetriableConfig | undefined;
    const isAuthCall = AUTH_PATHS.some((p) => original?.url?.includes(p));
    if (error.response?.status !== 401 || !original || original._retried || isAuthCall) {
      throw error;
    }
    original._retried = true;

    refreshing ??= refreshAccessToken().finally(() => {
      refreshing = null;
    });
    const newToken = await refreshing;
    if (!newToken) {
      onAuthFailure();
      throw error;
    }
    original.headers.set('Authorization', `Bearer ${newToken}`);
    return api(original);
  },
);
