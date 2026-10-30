import { Stack, Tabs, useLocalSearchParams } from 'expo-router';
import { useCallback, useMemo } from 'react';

import { groupsApi } from '@/api/groups';
import { ErrorState, Loading } from '@/components/ui';
import { useAuth } from '@/store/auth';
import { colors } from '@/theme';
import { GroupContext } from '@/utils/groupContext';
import { useLoad } from '@/utils/useLoad';

export default function GroupLayout() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const groupId = Number(id);
  const role = useAuth((s) => s.user?.role);
  const readOnly = role !== 'student';

  const group = useLoad(() => groupsApi.get(groupId), [groupId]);
  // Only students have an evaluation form; teachers use the summary screen instead
  const evaluation = useLoad(() => (readOnly ? Promise.resolve(null) : groupsApi.evaluationStatus(groupId)), [groupId, readOnly]);

  const members = group.data?.members;
  const memberName = useCallback(
    (uid: number | null | undefined) => (uid == null ? 'Unassigned' : (members?.find((m) => m.id === uid)?.name ?? 'Former member')),
    [members],
  );
  const reloadGroup = group.reload;
  const refreshEval = evaluation.reload;
  const evalOpen = !!evaluation.data?.is_open;

  const value = useMemo(
    () => (group.data ? { group: group.data, readOnly, reloadGroup, evalOpen, refreshEval, memberName } : null),
    [group.data, readOnly, reloadGroup, evalOpen, refreshEval, memberName],
  );

  if (!value) {
    return group.error ? <ErrorState message={group.error} onRetry={group.reload} /> : <Loading />;
  }

  return (
    <GroupContext.Provider value={value}>
      <Stack.Screen options={{ title: value.group.name }} />
      <Tabs
        screenOptions={{
          headerShown: false,
          tabBarPosition: 'top',
          tabBarActiveTintColor: colors.primary,
          tabBarInactiveTintColor: colors.textMuted,
          tabBarLabelStyle: { fontSize: 13, fontWeight: '600', textTransform: 'none' },
          tabBarIcon: () => null,
          tabBarIconStyle: { display: 'none' },
          tabBarItemStyle: { paddingHorizontal: 0 },
          sceneStyle: { backgroundColor: colors.background },
        }}
      >
        <Tabs.Screen name="index" options={{ title: 'Overview' }} />
        <Tabs.Screen name="tasks" options={{ title: 'Tasks' }} />
        <Tabs.Screen name="files" options={{ title: 'Files' }} />
        <Tabs.Screen name="activity" options={{ title: 'Activity' }} />
        <Tabs.Screen name="evaluation" options={{ title: 'Evaluation', ...(readOnly || !evalOpen ? { href: null } : {}) }} />
      </Tabs>
    </GroupContext.Provider>
  );
}
