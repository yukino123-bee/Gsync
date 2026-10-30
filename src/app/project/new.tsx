import { useRouter } from 'expo-router';
import { useState } from 'react';

import { projectsApi } from '@/api/projects';
import { DateField } from '@/components/DateField';
import { Button, ErrorBanner, Screen, TextField } from '@/components/ui';
import { endOfDay } from '@/utils/format';
import { getErrorMessage } from '@/utils/errors';

export default function NewProject() {
  const router = useRouter();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [rubric, setRubric] = useState('');
  const [deadline, setDeadline] = useState<Date | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function create() {
    if (!title.trim()) return setError('Give the project a title.');
    setError(null);
    setBusy(true);
    try {
      const project = await projectsApi.create({
        title: title.trim(), description: description.trim(), rubric: rubric.trim(),
        deadline: deadline ? endOfDay(deadline).toISOString() : null,
      });
      router.replace({ pathname: '/manage-groups/[id]', params: { id: String(project.id) } }); // next step: create groups
    } catch (e) {
      setError(getErrorMessage(e));
      setBusy(false);
    }
  }

  return (
    <Screen>
      <ErrorBanner message={error} />
      <TextField label="Title" value={title} onChangeText={setTitle} placeholder="e.g. Climate Change Presentation" maxLength={200} />
      <TextField label="Description" value={description} onChangeText={setDescription} multiline placeholder="What should students do?" />
      <TextField label="Grading rubric" value={rubric} onChangeText={setRubric} multiline placeholder={'Research 40%\nPresentation 30%\nTeamwork 30%'} />
      <DateField label="Deadline" value={deadline} onChange={setDeadline} minimumDate={new Date()} />
      <Button title="Create project" onPress={create} loading={busy} />
    </Screen>
  );
}
