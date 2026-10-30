import { useState } from 'react';
import { View } from 'react-native';

import { groupsApi } from '@/api/groups';
import { Badge, Body, Button, Card, ErrorBanner, Row, TextField } from '@/components/ui';
import { spacing } from '@/theme';
import { getErrorMessage } from '@/utils/errors';
import { formatDate, formatDateTime, isPast } from '@/utils/format';
import { useGroup } from '@/utils/groupContext';
import { useLoad } from '@/utils/useLoad';
import type { Milestone } from '@/types';

const TONE = { pending: 'neutral', submitted: 'info', reviewed: 'success' } as const;

export function MilestoneItem({ milestone, onChanged }: { milestone: Milestone; onChanged: () => void }) {
  const { readOnly, refreshEval } = useGroup();
  const [open, setOpen] = useState(false);
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const comments = useLoad(() => groupsApi.comments(milestone.id), [milestone.id]);

  const late = milestone.status === 'pending' && isPast(milestone.due_date);

  async function toggleSubmitted() {
    setBusy(true);
    setError(null);
    try {
      await groupsApi.updateMilestone(milestone.id, { status: milestone.status === 'pending' ? 'submitted' : 'pending' });
      onChanged();
      refreshEval(); // submitting the final milestone unlocks peer evaluation
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function postComment() {
    if (!comment.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await groupsApi.addComment(milestone.id, comment.trim());
      setComment('');
      comments.reload();
      onChanged();
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  const list = comments.data ?? [];

  return (
    <Card>
      <Row style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <View style={{ flex: 1 }}>
          <Body style={{ fontWeight: '700' }}>{milestone.title}</Body>
          <Body small muted>{milestone.due_date ? `Due ${formatDate(milestone.due_date)}` : 'No due date'}</Body>
        </View>
        <View style={{ gap: 4, alignItems: 'flex-end' }}>
          <Badge label={milestone.status} tone={TONE[milestone.status]} />
          {late ? <Badge label="Overdue" tone="danger" /> : null}
        </View>
      </Row>

      <ErrorBanner message={error} />

      <Row style={{ marginTop: spacing.md, justifyContent: 'space-between' }}>
        <Button
          small variant="ghost" icon={open ? 'chevron-up' : 'chatbubble-outline'}
          title={open ? 'Hide comments' : `Comments${list.length ? ` (${list.length})` : ''}`}
          onPress={() => setOpen((o) => !o)}
        />
        {!readOnly && milestone.status !== 'reviewed' ? (
          <Button
            small variant={milestone.status === 'pending' ? 'primary' : 'secondary'}
            title={milestone.status === 'pending' ? 'Mark submitted' : 'Undo submit'}
            onPress={toggleSubmitted} loading={busy}
          />
        ) : null}
      </Row>

      {open ? (
        <View style={{ marginTop: spacing.sm }}>
          {list.length === 0 ? <Body small muted>No comments yet.</Body> : null}
          {list.map((c) => (
            <View key={c.id} style={{ marginBottom: spacing.sm }}>
              <Body small style={{ fontWeight: '600' }}>{c.teacher_name} <Body small muted>· {formatDateTime(c.created_at)}</Body></Body>
              <Body small>{c.content}</Body>
            </View>
          ))}
          {readOnly ? (
            <View style={{ marginTop: spacing.sm }}>
              <TextField placeholder="Leave feedback on this milestone" value={comment} onChangeText={setComment} multiline />
              <Button title="Post comment" icon="send" onPress={postComment} loading={busy} disabled={!comment.trim()} />
            </View>
          ) : null}
        </View>
      ) : null}
    </Card>
  );
}
