import { useLocalSearchParams } from 'expo-router';
import { View } from 'react-native';

import { groupsApi } from '@/api/groups';
import { Async } from '@/components/Async';
import { StarRating } from '@/components/StarRating';
import { Avatar, Badge, Body, Card, EmptyState, Row, Screen } from '@/components/ui';
import { spacing } from '@/theme';
import { useLoad } from '@/utils/useLoad';

export default function EvaluationSummaryScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const groupId = Number(id);
  const load = useLoad(() => groupsApi.evaluationSummary(groupId), [groupId]);

  return (
    <Screen refreshing={load.refreshing} onRefresh={load.refresh}>
      <Async load={load}>
        {(summary) => (
          <>
            <Card>
              <Body style={{ fontWeight: '700' }}>Submissions</Body>
              <Body muted>{summary.submitted_count} of {summary.member_count} members have submitted their evaluation.</Body>
            </Card>
            {summary.members.length === 0 ? (
              <EmptyState icon="people-outline" title="No members" message="This group has no members." />
            ) : (
              summary.members.map((m) => (
                <Card key={m.user.id}>
                  <Row style={{ justifyContent: 'space-between' }}>
                    <Row style={{ flex: 1 }}>
                      <Avatar name={m.user.name} />
                      <Body style={{ fontWeight: '700', flex: 1 }}>{m.user.name}</Body>
                    </Row>
                    <Badge tone={m.average_rating == null ? 'neutral' : m.average_rating >= 4 ? 'success' : m.average_rating >= 3 ? 'warning' : 'danger'} label={m.average_rating == null ? 'No ratings' : `${m.average_rating.toFixed(1)} avg`} />
                  </Row>
                  <Row style={{ marginTop: spacing.sm, flexWrap: 'wrap' }}>
                    <Badge tone="success" icon="checkmark-circle" label={`${m.tasks_completed} tasks done`} />
                    <Badge tone="info" icon="pulse" label={`${m.activity_count} contributions`} />
                  </Row>
                  {m.ratings.map((r, i) => (
                    <View key={i} style={{ marginTop: spacing.md }}>
                      <Row style={{ justifyContent: 'space-between' }}>
                        <Body small muted>From {r.evaluator.name}</Body>
                        <StarRating value={r.rating} size={16} />
                      </Row>
                      {r.comment ? <Body small>{r.comment}</Body> : null}
                    </View>
                  ))}
                </Card>
              ))
            )}
          </>
        )}
      </Async>
    </Screen>
  );
}
