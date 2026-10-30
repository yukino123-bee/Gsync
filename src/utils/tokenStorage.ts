import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const ACCESS = 'gs_access_token';
const REFRESH = 'gs_refresh_token';

async function setItem(key: string, value: string | null) {
  if (Platform.OS === 'web') {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
    return;
  }
  if (value === null) await SecureStore.deleteItemAsync(key);
  else await SecureStore.setItemAsync(key, value);
}

async function getItem(key: string): Promise<string | null> {
  if (Platform.OS === 'web') return localStorage.getItem(key);
  return SecureStore.getItemAsync(key);
}

// In-memory copy so the axios interceptor never awaits storage on the hot path
let cache: { access: string | null; refresh: string | null } = { access: null, refresh: null };

export const tokenStorage = {
  async load() {
    cache = { access: await getItem(ACCESS), refresh: await getItem(REFRESH) };
    return cache;
  },
  get access() {
    return cache.access;
  },
  get refresh() {
    return cache.refresh;
  },
  async save(access: string, refresh: string) {
    cache = { access, refresh };
    await Promise.all([setItem(ACCESS, access), setItem(REFRESH, refresh)]);
  },
  async clear() {
    cache = { access: null, refresh: null };
    await Promise.all([setItem(ACCESS, null), setItem(REFRESH, null)]);
  },
};
