import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';

import type { TaskInput } from '@/api/groups';
import { DateField } from '@/components/DateField';
import { FormModal } from '@/components/FormModal';
import { Button, ErrorBanner, TextField } from '@/components/ui';
import { colors, fonts, radius, spacing } from '@/theme';
import { endOfDay } from '@/utils/format';
import type { Task, UserBrief } from '@/types';

interface Props {
  visible: boolean;
  task?: Task | null;
  members: UserBrief[];
  onClose: () => void;
  onSave: (input: TaskInput) => Promise<void>;
  error?: string | null;
}

export function TaskFormModal({ visible, task, members, onClose, onSave, error }: Props) {
  return (
    <FormModal visible={visible} title={task ? 'Edit task' : 'New task'} onClose={onClose}>
      {/* Mounted only while open, so the fields start fresh from `task` each time */}
      {visible ? <TaskFormBody task={task} members={members} onSave={onSave} error={error} /> : null}
    </FormModal>
  );
}

function TaskFormBody({ task, members, onSave, error }: Pick<Props, 'task' | 'members' | 'onSave' | 'error'>) {
  const [title, setTitle] = useState(task?.title ?? '');
  const [description, setDescription] = useState(task?.description ?? '');
  const [assignee, setAssignee] = useState<number | null>(task?.assignee_id ?? null);
  const [due, setDue] = useState<Date | null>(task?.due_date ? new Date(task.due_date) : null);
  const [busy, setBusy] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  async function submit() {
    if (!title.trim()) return setLocalError('Give the task a title.');
    setLocalError(null);
    setBusy(true);
    try {
      await onSave({
        title: title.trim(),
        description: description.trim(),
        assignee_id: assignee,
        due_date: due ? endOfDay(due).toISOString() : null,
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <ErrorBanner message={localError ?? error} />
      <TextField label="Title" value={title} onChangeText={setTitle} placeholder="What needs to be done?" />
      <TextField label="Description (optional)" value={description} onChangeText={setDescription} multiline />
      <Text style={{ fontSize: fonts.size.sm, fontWeight: fonts.weight.medium, color: colors.text, marginBottom: spacing.xs }}>Assign to</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginBottom: spacing.md }}>
        {[{ id: null as number | null, name: 'Unassigned' }, ...members].map((m) => {
          const active = assignee === m.id;
          return (
            <Pressable
              key={String(m.id)} onPress={() => setAssignee(m.id)} accessibilityState={{ selected: active }}
              style={{ paddingHorizontal: 12, paddingVertical: 8, borderRadius: radius.pill, backgroundColor: active ? colors.primary : colors.border }}
            >
              <Text style={{ color: active ? colors.textOnPrimary : colors.text, fontSize: fonts.size.sm }}>{m.name}</Text>
            </Pressable>
          );
        })}
      </View>
      <DateField label="Due date" value={due} onChange={setDue} />
      <Button title={task ? 'Save changes' : 'Create task'} onPress={submit} loading={busy} />
    </>
  );
}
