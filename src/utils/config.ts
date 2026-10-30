import Constants from 'expo-constants';
import { Platform } from 'react-native';

const API_PORT = 8000;

/**
 * Backend base URL. Priority:
 *  1. EXPO_PUBLIC_API_URL (set it in .env for a deployed backend)
 *  2. In a browser: the page's own hostname on port 8000
 *  3. The dev machine's LAN address, taken from the Metro host, so Expo Go on a real
 *     phone reaches the FastAPI server running on the same computer
 *  4. localhost
 */
function resolveApiUrl(): string {
  const fromEnv = process.env.EXPO_PUBLIC_API_URL;
  if (fromEnv) return fromEnv.replace(/\/$/, '');

  // In a browser, talk to the API on whichever host served the page (works for localhost and LAN access)
  if (Platform.OS === 'web' && typeof window !== 'undefined') return `${window.location.protocol}//${window.location.hostname}:${API_PORT}`;

  const hostUri = Constants.expoConfig?.hostUri; // e.g. "192.168.1.20:8081"
  const host = hostUri?.split(':')[0];
  if (host) return `http://${host}:${API_PORT}`;

  return Platform.OS === 'android' ? `http://10.0.2.2:${API_PORT}` : `http://localhost:${API_PORT}`;
}

export const API_URL = resolveApiUrl();
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
