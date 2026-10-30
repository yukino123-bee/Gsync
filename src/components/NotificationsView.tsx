import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { FlatList, View } from 'react-native';

import { notificationsApi } from '@/api/notifications';
import { Async } from '@/components/Async';
import { Body, Button, Card, EmptyState, Row } from '@/components/ui';
import { useNotificationStore } from '@/store/notifications';
import { colors, spacing } from '@/theme';
import { timeAgo } from '@/utils/format';
import { useLoad } from '@/utils/useLoad';
import type { AppNotification } from '@/types';

const ICONS: Record<string, { name: React.ComponentProps<typeof Ionicons>['name']; color: string }> = {
  task_due_soon: { name: 'time-outline', color: colors.warning },
  task_overdue: { name: 'alert-circle-outline', color: colors.danger },
  group_overdue: { name: 'warning-outline', color: colors.danger },
  group_inactive: { name: 'moon-outline', color: colors.info },
};

export function NotificationsView() {
  const router = useRouter();
  const setUnread = useNotificationStore((s) => s.setUnread);
  const load = useLoad(async () => {
    const items = await notificationsApi.list();
    setUnread(items.filter((n) => !n.is_read).length);
    return items;
  });

  async function open(n: AppNotification) {
    if (!n.is_read) {
      load.setData((prev) => prev?.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)));
      setUnread(Math.max(0, useNotificationStore.getState().unread - 1));
      notificationsApi.markRead(n.id).catch(() => load.reload());
    }
    if (n.group_id) router.push({ pathname: '/group/[id]', params: { id: String(n.group_id) } });
  }

  async function markAll() {
    load.setData((prev) => prev?.map((x) => ({ ...x, is_read: true })));
    setUnread(0);
    await notificationsApi.markAllRead().catch(() => load.reload());
  }

  return (
    <Async load={load}>
      {(items) => (
        <FlatList
          data={items}
          keyExtractor={(n) => String(n.id)}
          refreshing={load.refreshing}
          onRefresh={load.refresh}
          contentContainerStyle={{ padding: spacing.lg, flexGrow: 1 }}
          ListHeaderComponent={
            items.some((n) => !n.is_read) ? (
              <View style={{ alignItems: 'flex-end', marginBottom: spacing.sm }}>
                <Button title="Mark all as read" onPress={markAll} variant="ghost" small icon="checkmark-done" />
              </View>
            ) : undefined
          }
          ListEmptyComponent={
            <EmptyState icon="notifications-off-outline" title="You're all caught up" message="Reminders about due and overdue tasks will show up here." />
          }
          renderItem={({ item }) => {
            const icon = ICONS[item.type] ?? { name: 'notifications-outline' as const, color: colors.primary };
            return (
              <Card onPress={() => open(item)} style={!item.is_read ? { borderLeftWidth: 4, borderLeftColor: colors.primary } : undefined}>
                <Row style={{ alignItems: 'flex-start' }}>
                  <Ionicons name={icon.name} size={22} color={icon.color} />
                  <View style={{ flex: 1 }}>
                    <Body style={{ fontWeight: item.is_read ? '400' : '700' }}>{item.title}</Body>
                    <Body muted small>{item.body}</Body>
                    <Body muted small style={{ marginTop: 4 }}>{timeAgo(item.created_at)}</Body>
                  </View>
                </Row>
              </Card>
            );
          }}
        />
      )}
    </Async>
  );
}
