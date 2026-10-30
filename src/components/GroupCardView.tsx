import { useRouter } from 'expo-router';
import { View } from 'react-native';

import { Avatar, Badge, Body, Card, ProgressBar, Row } from '@/components/ui';
import { spacing } from '@/theme';
import { formatDate, timeAgo } from '@/utils/format';
import type { Group, GroupStats } from '@/types';

export function GroupSummaryCard({ group, stats }: { group: Group; stats: GroupStats }) {
  const router = useRouter();
  return (
    <Card onPress={() => router.push({ pathname: '/group/[id]', params: { id: String(group.id) } })}>
      <Body style={{ fontWeight: '700', fontSize: 18 }}>{group.name}</Body>
      <Body muted small>{group.project.title}</Body>

      <View style={{ marginTop: spacing.md, gap: 6 }}>
        <Row style={{ justifyContent: 'space-between' }}>
          <Body small muted>{stats.done_tasks} of {stats.total_tasks} tasks done</Body>
          <Body small style={{ fontWeight: '700' }}>{stats.percent_done}%</Body>
        </Row>
        <ProgressBar percent={stats.percent_done} />
      </View>

      <Row style={{ marginTop: spacing.md, flexWrap: 'wrap' }}>
        {stats.overdue_tasks > 0 ? <Badge tone="danger" icon="alert-circle" label={`${stats.overdue_tasks} overdue`} /> : null}
        {stats.is_inactive ? <Badge tone="warning" icon="moon" label="Inactive" /> : null}
        {stats.next_milestone ? (
          <Badge tone="info" icon="flag" label={`${stats.next_milestone.title}${stats.next_milestone.due_date ? ` · ${formatDate(stats.next_milestone.due_date)}` : ''}`} />
        ) : null}
      </Row>

      <Row style={{ marginTop: spacing.md, justifyContent: 'space-between' }}>
        <Row style={{ gap: 4 }}>
          {group.members.slice(0, 5).map((m) => <Avatar key={m.id} name={m.name} size={28} />)}
        </Row>
        <Body small muted>Active {timeAgo(stats.last_activity_at)}</Body>
      </Row>
    </Card>
  );
}
