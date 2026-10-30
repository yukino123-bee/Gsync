import { Ionicons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';
import { useEffect } from 'react';
import { AppState } from 'react-native';

import { gradientHeaderOptions } from '@/components/GradientHeader';
import { colors } from '@/theme';
import { useNotificationStore } from '@/store/notifications';

type Icon = React.ComponentProps<typeof Ionicons>['name'];

/** Shared bottom-tab layout; only the first tab's title and icon differ between roles. */
export function RoleTabs({ homeTitle, homeIcon }: { homeTitle: string; homeIcon: Icon }) {
  const unread = useNotificationStore((s) => s.unread);
  const refreshUnread = useNotificationStore((s) => s.refreshUnread);

  // Keep the badge fresh: on mount, every minute, and when the app returns to the foreground
  useEffect(() => {
    refreshUnread();
    const timer = setInterval(refreshUnread, 60_000);
    const sub = AppState.addEventListener('change', (state) => state === 'active' && refreshUnread());
    return () => {
      clearInterval(timer);
      sub.remove();
    };
  }, [refreshUnread]);

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        ...gradientHeaderOptions,
        sceneStyle: { backgroundColor: colors.background },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{ title: homeTitle, tabBarIcon: ({ color, size }) => <Ionicons name={homeIcon} size={size} color={color as string} /> }}
      />
      <Tabs.Screen
        name="notifications"
        options={{
          title: 'Notifications',
          tabBarBadge: unread > 0 ? (unread > 99 ? '99+' : unread) : undefined,
          tabBarIcon: ({ color, size }) => <Ionicons name="notifications-outline" size={size} color={color as string} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{ title: 'Profile', tabBarIcon: ({ color, size }) => <Ionicons name="person-outline" size={size} color={color as string} /> }}
      />
    </Tabs>
  );
}
