import Constants, { ExecutionEnvironment } from 'expo-constants';
import * as Device from 'expo-device';
import { useRouter } from 'expo-router';
import { useEffect } from 'react';
import { Platform } from 'react-native';

import { authApi } from '@/api/auth';
import { useNotificationStore } from '@/store/notifications';

type NotificationsModule = typeof import('expo-notifications');

/**
 * Remote push is unavailable on web, simulators, and Android Expo Go (removed in SDK 53).
 * In those cases we skip loading expo-notifications altogether; the in-app notification list
 * (polled from the API) still works everywhere.
 */
export function pushSupported(): boolean {
  if (Platform.OS === 'web' || !Device.isDevice) return false;
  const inExpoGo = Constants.executionEnvironment === ExecutionEnvironment.StoreClient;
  return !(Platform.OS === 'android' && inExpoGo);
}

async function registerForPushToken(Notifications: NotificationsModule): Promise<string | null> {
  if (Platform.OS === 'android') {
    // Android 13+ will not show the permission prompt until a channel exists
    await Notifications.setNotificationChannelAsync('default', {
      name: 'GroupSync',
      importance: Notifications.AndroidImportance.HIGH,
      lightColor: '#4F46E5',
    });
  }

  let { granted } = await Notifications.getPermissionsAsync();
  if (!granted) ({ granted } = await Notifications.requestPermissionsAsync());
  if (!granted) return null;

  const projectId = Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId;
  const { data } = await Notifications.getExpoPushTokenAsync(projectId ? { projectId } : undefined);
  return data;
}

/** Registers this device for push once signed in and routes notification taps to the right group. */
export function usePushNotifications(signedIn: boolean) {
  const router = useRouter();
  const refreshUnread = useNotificationStore((s) => s.refreshUnread);

  useEffect(() => {
    if (!signedIn || !pushSupported()) return;
    let cancelled = false;
    const subs: { remove: () => void }[] = [];

    (async () => {
      try {
        const Notifications = await import('expo-notifications');
        if (cancelled) return;

        Notifications.setNotificationHandler({
          handleNotification: async () => ({
            shouldShowBanner: true, shouldShowList: true, shouldPlaySound: false, shouldSetBadge: false,
          }),
        });

        const openFrom = (data: Record<string, unknown> | undefined) => {
          const groupId = data?.group_id;
          if (typeof groupId === 'number') router.push({ pathname: '/group/[id]', params: { id: String(groupId) } });
        };

        subs.push(
          Notifications.addNotificationReceivedListener(() => refreshUnread()),
          Notifications.addNotificationResponseReceivedListener((resp) => {
            refreshUnread();
            openFrom(resp.notification.request.content.data);
          }),
        );

        const token = await registerForPushToken(Notifications);
        if (token && !cancelled) await authApi.setPushToken(token);
      } catch (e) {
        // Push is a bonus: missing permission, offline, or no EAS project id must never break the app
        console.warn('Push registration skipped:', e instanceof Error ? e.message : e);
      }
    })();

    return () => {
      cancelled = true;
      subs.forEach((s) => s.remove());
    };
  }, [signedIn, router, refreshUnread]);
}
