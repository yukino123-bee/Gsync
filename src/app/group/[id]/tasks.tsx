import { useState } from 'react';
import { View } from 'react-native';
import { Alert } from '@/utils/alert';

import { groupsApi, TaskInput } from '@/api/groups';
import { Async } from '@/components/Async';
import { FormModal } from '@/components/FormModal';
import { TaskFormModal } from '@/components/TaskForm';
import {
  Badge, Body, Button, Card, EmptyState, ErrorBanner, Row, Screen, Segmented,
} from '@/components/ui';
import { useAuth } from '@/store/auth';
import { spacing } from '@/theme';
import { getErrorMessage } from '@/utils/errors';
import { formatDate, isPast } from '@/utils/format';
import { useGroup } from '@/utils/groupContext';
import { useLoad } from '@/utils/useLoad';
import type { Task, TaskStatus } from '@/types';

const COLUMNS: { value: TaskStatus; label: string }[] = [
  { value: 'todo', label: 'To Do' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'done', label: 'Done' },
];

export default function Tasks() {
  const { group, readOnly, memberName } = useGroup();
  const me = useAuth((s) => s.user);
  const load = useLoad(() => groupsApi.tasks(group.id), [group.id]);
  const [column, setColumn] = useState<TaskStatus>('todo');
  const [mineOnly, setMineOnly] = useState(false);
  const [selected, setSelected] = useState<Task | null>(null);
  const [form, setForm] = useState<{ open: boolean; task: Task | null }>({ open: false, task: null });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<unknown>): Promise<boolean> {
    setError(null);
    setBusy(true);
    try {
      await action();
      load.reload();
      return true;
    } catch (e) {
      setError(getErrorMessage(e));
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function saveTask(input: TaskInput) {
    const editing = form.task;
    const ok = await run(() => (editing ? groupsApi.updateTask(editing.id, input) : groupsApi.createTask(group.id, input)));
    if (ok) {
      setForm({ open: false, task: null });
      setSelected(null);
    }
  }

  async function move(task: Task, status: TaskStatus) {
    if (status === task.status) return;
    if (await run(() => groupsApi.setTaskStatus(task.id, status))) {
      setSelected(null);
      setColumn(status); // follow the card so the move is visible
    }
  }

  function confirmDelete(task: Task) {
    Alert.alert('Delete task', `Delete "${task.title}"? This can't be undone.`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => { if (await run(() => groupsApi.deleteTask(task.id))) setSelected(null); } },
    ]);
  }

  return (
    <Screen refreshing={load.refreshing} onRefresh={load.refresh}>
      <ErrorBanner message={selected || form.open ? null : error} />
      <Async load={load}>
        {(tasks) => {
          const visible = mineOnly ? tasks.filter((t) => t.assignee_id === me?.id) : tasks;
          const count = (s: TaskStatus) => visible.filter((t) => t.status === s).length;
          const shown = visible.filter((t) => t.status === column);
          return (
            <>
              <Segmented value={column} onChange={setColumn} options={COLUMNS.map((c) => ({ value: c.value, label: `${c.label} (${count(c.value)})` }))} />
              <Row style={{ justifyContent: 'space-between', marginBottom: spacing.md }}>
                <Segmented
                  value={mineOnly ? 'mine' : 'all'} onChange={(v) => setMineOnly(v === 'mine')}
                  options={[{ value: 'all', label: 'All tasks' }, { value: 'mine', label: 'Mine' }]}
                />
              </Row>
              {!readOnly ? <Button title="New task" icon="add" onPress={() => { setError(null); setForm({ open: true, task: null }); }} style={{ marginBottom: spacing.md }} /> : null}

              {shown.length === 0 ? (
                <EmptyState
                  icon="checkbox-outline" title={`Nothing in ${COLUMNS.find((c) => c.value === column)!.label}`}
                  message={tasks.length === 0 ? (readOnly ? 'This group has no tasks yet.' : 'Create the first task to get started.') : 'Tap a task and move it between columns as work progresses.'}
                />
              ) : (
                shown.map((t) => (
                  <Card key={t.id} onPress={() => { setError(null); setSelected(t); }}>
                    <Body style={{ fontWeight: '600' }}>{t.title}</Body>
                    <Row style={{ marginTop: spacing.sm, flexWrap: 'wrap' }}>
                      <Badge icon="person" label={memberName(t.assignee_id)} tone={t.assignee_id ? 'info' : 'neutral'} />
                      {t.due_date ? (
                        <Badge icon="calendar" label={formatDate(t.due_date)} tone={t.status !== 'done' && isPast(t.due_date) ? 'danger' : 'neutral'} />
                      ) : null}
                      {t.status !== 'done' && isPast(t.due_date) ? <Badge tone="danger" label="Overdue" /> : null}
                    </Row>
                  </Card>
                ))
              )}
            </>
          );
        }}
      </Async>

      {/* Task details + move between columns */}
      <FormModal visible={!!selected && !form.open} title={selected?.title ?? ''} onClose={() => setSelected(null)}>
        {selected ? (
          <>
            <ErrorBanner message={error} />
            {selected.description ? <Body style={{ marginBottom: spacing.md }}>{selected.description}</Body> : null}
            <Body small muted>Assigned to: {memberName(selected.assignee_id)}</Body>
            <Body small muted style={{ marginBottom: spacing.lg }}>Due: {formatDate(selected.due_date)}</Body>
            {!readOnly ? (
              <>
                <Body style={{ fontWeight: '600', marginBottom: spacing.sm }}>Move to</Body>
                <View style={{ gap: spacing.sm, marginBottom: spacing.lg }}>
                  {COLUMNS.map((c) => (
                    <Button
                      key={c.value} title={c.label + (c.value === selected.status ? ' (current)' : '')}
                      variant={c.value === selected.status ? 'secondary' : 'primary'}
                      disabled={c.value === selected.status || busy}
                      onPress={() => move(selected, c.value)}
                    />
                  ))}
                </View>
                <Row>
                  <Button style={{ flex: 1 }} title="Edit" icon="create-outline" variant="secondary" onPress={() => setForm({ open: true, task: selected })} />
                  <Button style={{ flex: 1 }} title="Delete" icon="trash-outline" variant="danger" onPress={() => confirmDelete(selected)} />
                </Row>
              </>
            ) : null}
          </>
        ) : null}
      </FormModal>

      <TaskFormModal
        visible={form.open} task={form.task} members={group.members} error={error}
        onClose={() => setForm({ open: false, task: null })} onSave={saveTask}
      />
    </Screen>
  );
}
