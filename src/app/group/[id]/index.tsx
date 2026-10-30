import { useRouter } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';

import { groupsApi } from '@/api/groups';
import { Async } from '@/components/Async';
import { DateField } from '@/components/DateField';
import { FormModal } from '@/components/FormModal';
import { MilestoneItem } from '@/components/MilestoneItem';
import {
  Avatar, Badge, Body, Button, Card, EmptyState, ErrorBanner, ProgressBar, Row, Screen, SectionHeader, TextField,
} from '@/components/ui';
import { spacing } from '@/theme';
import { getErrorMessage } from '@/utils/errors';
import { endOfDay, formatDate, timeAgo } from '@/utils/format';
import { useGroup } from '@/utils/groupContext';
import { useLoad } from '@/utils/useLoad';

export default function Overview() {
  const router = useRouter();
  const { group, readOnly } = useGroup();
  const stats = useLoad(() => groupsApi.stats(group.id), [group.id]);
  const milestones = useLoad(() => groupsApi.milestones(group.id), [group.id]);
  const [showRubric, setShowRubric] = useState(false);
  const [adding, setAdding] = useState(false);

  const refresh = () => {
    stats.refresh();
    milestones.refresh();
  };
  const reloadBoth = () => {
    stats.reload();
    milestones.reload();
  };

  return (
    <Screen refreshing={stats.refreshing || milestones.refreshing} onRefresh={refresh}>
      <Card>
        <Body style={{ fontWeight: '700', fontSize: 18 }}>{group.project.title}</Body>
        {group.project.deadline ? <Body small muted>Project deadline: {formatDate(group.project.deadline)}</Body> : null}
        {group.project.description ? <Body small style={{ marginTop: spacing.sm }}>{group.project.description}</Body> : null}
        {group.project.rubric ? (
          <>
            <Button small variant="ghost" title={showRubric ? 'Hide rubric' : 'View rubric'} icon="list-outline" onPress={() => setShowRubric((v) => !v)} style={{ alignSelf: 'flex-start', marginTop: spacing.sm }} />
            {showRubric ? <Body small>{group.project.rubric}</Body> : null}
          </>
        ) : null}
      </Card>

      <Async load={stats}>
        {(s) => (
          <Card>
            <Row style={{ justifyContent: 'space-between' }}>
              <Body style={{ fontWeight: '700' }}>Progress</Body>
              <Body style={{ fontWeight: '700' }}>{s.percent_done}%</Body>
            </Row>
            <View style={{ marginVertical: spacing.sm }}><ProgressBar percent={s.percent_done} height={10} /></View>
            <Row style={{ flexWrap: 'wrap' }}>
              <Badge label={`${s.todo_tasks} to do`} />
              <Badge tone="info" label={`${s.in_progress_tasks} in progress`} />
              <Badge tone="success" label={`${s.done_tasks} done`} />
              {s.overdue_tasks > 0 ? <Badge tone="danger" icon="alert-circle" label={`${s.overdue_tasks} overdue`} /> : null}
            </Row>
            <Body small muted style={{ marginTop: spacing.sm }}>
              {s.next_milestone ? `Next milestone: ${s.next_milestone.title}${s.next_milestone.due_date ? ` (${formatDate(s.next_milestone.due_date)})` : ''}` : 'No upcoming milestone'}
              {' · '}Last activity {timeAgo(s.last_activity_at)}
            </Body>
            {s.is_inactive ? <View style={{ marginTop: spacing.sm }}><Badge tone="warning" icon="moon" label="No activity in 3+ days" /></View> : null}
          </Card>
        )}
      </Async>

      <SectionHeader title="Milestones" action={!readOnly ? <Button small variant="secondary" icon="add" title="Add" onPress={() => setAdding(true)} /> : undefined} />
      <Async load={milestones}>
        {(items) =>
          items.length === 0 ? (
            <EmptyState icon="flag-outline" title="No milestones yet" message={readOnly ? 'This group has not added milestones.' : 'Add milestones like Outline, Draft and Final to track your deadlines.'} />
          ) : (
            <>{items.map((m) => <MilestoneItem key={m.id} milestone={m} onChanged={reloadBoth} />)}</>
          )
        }
      </Async>

      <SectionHeader title={`Members (${group.members.length})`} />
      <Card>
        {group.members.map((m) => (
          <Row key={m.id} style={{ paddingVertical: 4 }}>
            <Avatar name={m.name} />
            <View><Body>{m.name}</Body><Body small muted>{m.email}</Body></View>
          </Row>
        ))}
      </Card>

      {readOnly ? (
        <Button title="View peer evaluations" icon="star-outline" variant="secondary" onPress={() => router.push({ pathname: '/evaluation/[id]', params: { id: String(group.id) } })} />
      ) : null}

      <AddMilestoneModal visible={adding} groupId={group.id} onClose={() => setAdding(false)} onSaved={() => { setAdding(false); reloadBoth(); }} />
    </Screen>
  );
}

function AddMilestoneModal({ visible, groupId, onClose, onSaved }: { visible: boolean; groupId: number; onClose: () => void; onSaved: () => void }) {
  const { refreshEval } = useGroup();
  const [title, setTitle] = useState('');
  const [due, setDue] = useState<Date | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    if (!title.trim()) return setError('Give the milestone a title.');
    setBusy(true);
    setError(null);
    try {
      await groupsApi.createMilestone(groupId, { title: title.trim(), due_date: due ? endOfDay(due).toISOString() : null });
      setTitle('');
      setDue(null);
      refreshEval(); // a new, later milestone changes which one counts as final
      onSaved();
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <FormModal visible={visible} title="New milestone" onClose={onClose}>
      <ErrorBanner message={error} />
      <TextField label="Title" value={title} onChangeText={setTitle} placeholder="e.g. Draft" />
      <DateField label="Due date" value={due} onChange={setDue} />
      <Button title="Add milestone" onPress={save} loading={busy} />
    </FormModal>
  );
}
