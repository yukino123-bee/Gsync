import { Ionicons } from '@expo/vector-icons';
import { FlatList, View } from 'react-native';

import { groupsApi } from '@/api/groups';
import { Async } from '@/components/Async';
import { Body, Card, EmptyState, Row } from '@/components/ui';
import { colors, spacing } from '@/theme';
import { formatDateTime } from '@/utils/format';
import { useGroup } from '@/utils/groupContext';
import { useLoad } from '@/utils/useLoad';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

const ICONS: Record<string, { name: IconName; color: string }> = {
  task_created: { name: 'add-circle-outline', color: colors.info },
  task_updated: { name: 'create-outline', color: colors.textMuted },
  task_status_changed: { name: 'swap-horizontal-outline', color: colors.warning },
  task_completed: { name: 'checkmark-circle', color: colors.success },
  task_deleted: { name: 'trash-outline', color: colors.danger },
  file_uploaded: { name: 'cloud-upload-outline', color: colors.primary },
  note_added: { name: 'reader-outline', color: colors.primary },
  milestone_created: { name: 'flag-outline', color: colors.info },
  milestone_updated: { name: 'flag-outline', color: colors.textMuted },
  milestone_submitted: { name: 'flag', color: colors.success },
};

export default function ActivityFeed() {
  const { group } = useGroup();
  const load = useLoad(() => groupsApi.activity(group.id), [group.id]);

  return (
    <Async load={load}>
      {(items) => (
        <FlatList
          data={items}
          keyExtractor={(a) => String(a.id)}
          refreshing={load.refreshing}
          onRefresh={load.refresh}
          contentContainerStyle={{ padding: spacing.lg, flexGrow: 1 }}
          ListEmptyComponent={<EmptyState icon="pulse-outline" title="No activity yet" message="Created tasks, completed work, uploaded files and notes are logged here automatically." />}
          renderItem={({ item }) => {
            const icon = ICONS[item.action_type] ?? { name: 'ellipse-outline' as const, color: colors.textMuted };
            return (
              <Card>
                <Row style={{ alignItems: 'flex-start' }}>
                  <Ionicons name={icon.name} size={22} color={icon.color} />
                  <View style={{ flex: 1 }}>
                    <Body>{item.description}</Body>
                    <Body small muted>{formatDateTime(item.created_at)}</Body>
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
