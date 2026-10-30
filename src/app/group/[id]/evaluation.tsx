import { useState } from 'react';

import { groupsApi } from '@/api/groups';
import { Async } from '@/components/Async';
import { StarRating } from '@/components/StarRating';
import { Avatar, Body, Button, Card, EmptyState, ErrorBanner, Row, Screen, TextField } from '@/components/ui';
import { spacing } from '@/theme';
import { getErrorMessage } from '@/utils/errors';
import { useGroup } from '@/utils/groupContext';
import { useLoad } from '@/utils/useLoad';

export default function PeerEvaluation() {
  const { group, refreshEval } = useGroup();
  const load = useLoad(() => groupsApi.evaluationStatus(group.id), [group.id]);
  const [ratings, setRatings] = useState<Record<number, number>>({});
  const [comments, setComments] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(memberIds: number[]) {
    setBusy(true);
    setError(null);
    try {
      await groupsApi.submitEvaluations(
        group.id,
        memberIds.map((id) => ({ evaluatee_id: id, rating: ratings[id]!, comment: comments[id]?.trim() || null })),
      );
      load.reload();
      refreshEval();
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen refreshing={load.refreshing} onRefresh={load.refresh}>
      <Async load={load}>
        {(status) => {
          if (!status.is_open) {
            return <EmptyState icon="lock-closed-outline" title="Not open yet" message="Peer evaluation opens after your group submits its final milestone." />;
          }
          if (status.has_submitted) {
            return <EmptyState icon="checkmark-circle-outline" title="Evaluation submitted" message="Thanks! Your ratings are private and only your teacher can see them." />;
          }
          const ids = status.members_to_rate.map((m) => m.id);
          if (ids.length === 0) {
            return <EmptyState icon="person-outline" title="Nobody to rate" message="You're the only member of this group." />;
          }
          const ready = ids.every((id) => ratings[id]);
          return (
            <>
              <Body muted style={{ marginBottom: spacing.md }}>
                Rate each teammate from 1 to 5. Only your teacher will see your ratings and comments.
              </Body>
              <ErrorBanner message={error} />
              {status.members_to_rate.map((m) => (
                <Card key={m.id}>
                  <Row style={{ marginBottom: spacing.sm }}>
                    <Avatar name={m.name} />
                    <Body style={{ fontWeight: '600' }}>{m.name}</Body>
                  </Row>
                  <StarRating value={ratings[m.id] ?? 0} onChange={(v) => setRatings((r) => ({ ...r, [m.id]: v }))} />
                  <TextField
                    style={{ marginTop: spacing.md }} placeholder="Comment (optional)" multiline
                    value={comments[m.id] ?? ''} onChangeText={(t) => setComments((c) => ({ ...c, [m.id]: t }))} maxLength={1000}
                  />
                </Card>
              ))}
              <Button title="Submit evaluation" onPress={() => submit(ids)} loading={busy} disabled={!ready} />
              {!ready ? <Body small muted style={{ textAlign: 'center', marginTop: spacing.sm }}>Rate every teammate to submit. You can&apos;t change it afterwards.</Body> : null}
            </>
          );
        }}
      </Async>
    </Screen>
  );
}
