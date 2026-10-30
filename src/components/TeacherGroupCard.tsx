import { useRouter } from 'expo-router';
import { View } from 'react-native';

import { Badge, Body, Card, ProgressBar, Row } from '@/components/ui';
import { spacing } from '@/theme';
import { formatDate, timeAgo } from '@/utils/format';
import type { GroupCard } from '@/types';

export function TeacherGroupCard({ card }: { card: GroupCard }) {
  const router = useRouter();
  const warn = card.overdue_tasks > 0 || card.is_inactive;
  return (
    <Card
      onPress={() => router.push({ pathname: '/group/[id]', params: { id: String(card.group_id) } })}
      style={warn ? { borderLeftWidth: 4, borderLeftColor: card.overdue_tasks > 0 ? '#DC2626' : '#D97706' } : undefined}
    >
      <Row style={{ justifyContent: 'space-between' }}>
        <Body style={{ fontWeight: '700', fontSize: 18, flex: 1 }}>{card.name}</Body>
        <Body small muted>{card.member_count} member{card.member_count === 1 ? '' : 's'}</Body>
      </Row>
      <View style={{ marginTop: spacing.md, gap: 6 }}>
        <Row style={{ justifyContent: 'space-between' }}>
          <Body small muted>{card.done_tasks} of {card.total_tasks} tasks done</Body>
          <Body small style={{ fontWeight: '700' }}>{card.percent_done}%</Body>
        </Row>
        <ProgressBar percent={card.percent_done} />
      </View>
      <Row style={{ marginTop: spacing.md, flexWrap: 'wrap' }}>
        {card.overdue_tasks > 0 ? <Badge tone="danger" icon="alert-circle" label={`${card.overdue_tasks} overdue`} /> : null}
        {card.is_inactive ? <Badge tone="warning" icon="moon" label="Inactive 3+ days" /> : null}
        {card.next_milestone ? (
          <Badge tone="info" icon="flag" label={`${card.next_milestone.title}${card.next_milestone.due_date ? ` · ${formatDate(card.next_milestone.due_date)}` : ''}`} />
        ) : (
          <Badge label="No milestone" />
        )}
      </Row>
      <Body small muted style={{ marginTop: spacing.sm }}>Last activity: {timeAgo(card.last_activity_at)}</Body>
    </Card>
  );
}
