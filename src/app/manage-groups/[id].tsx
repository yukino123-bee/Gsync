import { useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { View } from 'react-native';
import { Alert } from '@/utils/alert';

import { projectsApi } from '@/api/projects';
import { Async } from '@/components/Async';
import { FormModal } from '@/components/FormModal';
import { Avatar, Body, Button, Card, EmptyState, ErrorBanner, Row, Screen, SectionHeader, TextField } from '@/components/ui';
import { spacing } from '@/theme';
import { getErrorMessage } from '@/utils/errors';
import { useLoad } from '@/utils/useLoad';
import type { Group, UserBrief } from '@/types';

export default function ManageGroups() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const projectId = Number(id);
  const load = useLoad(() => projectsApi.groups(projectId), [projectId]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [newName, setNewName] = useState('');
  const [size, setSize] = useState('3');
  const [adding, setAdding] = useState<Group | null>(null);

  async function run(action: () => Promise<unknown>) {
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

  async function createGroup() {
    if (!newName.trim()) return setError('Give the group a name.');
    if (await run(() => projectsApi.createGroup(projectId, newName.trim()))) setNewName('');
  }

  function randomize() {
    const n = parseInt(size, 10);
    if (!n || n < 1 || n > 20) return setError('Enter a group size between 1 and 20.');
    Alert.alert('Randomize groups', `Split every student who is not in a group yet into new groups of about ${n}?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Randomize', onPress: () => run(() => projectsApi.randomize(projectId, n)) },
    ]);
  }

  function confirmRemove(group: Group, member: UserBrief) {
    Alert.alert('Remove student', `Remove ${member.name} from ${group.name}? Their tasks will become unassigned.`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Remove', style: 'destructive', onPress: () => run(() => projectsApi.removeMember(group.id, member.id)) },
    ]);
  }

  return (
    <Screen refreshing={load.refreshing} onRefresh={load.refresh}>
      <ErrorBanner message={adding ? null : error} />

      <Card>
        <Body style={{ fontWeight: '700', marginBottom: spacing.sm }}>Create a group</Body>
        <TextField placeholder="Group name" value={newName} onChangeText={setNewName} maxLength={120} />
        <Button title="Create group" icon="add" onPress={createGroup} loading={busy} />
      </Card>

      <Card>
        <Body style={{ fontWeight: '700' }}>Randomize groups</Body>
        <Body small muted style={{ marginBottom: spacing.sm }}>Splits all students who are not in a group yet into evenly sized groups.</Body>
        <TextField label="Students per group" value={size} onChangeText={setSize} keyboardType="number-pad" maxLength={2} />
        <Button title="Randomize" icon="shuffle" variant="secondary" onPress={randomize} loading={busy} />
      </Card>

      <SectionHeader title="Groups" />
      <Async load={load}>
        {(groups) =>
          groups.length === 0 ? (
            <EmptyState icon="people-outline" title="No groups yet" message="Create a group above or randomize your class." />
          ) : (
            <>
              {groups.map((g) => (
                <Card key={g.id}>
                  <Row style={{ justifyContent: 'space-between' }}>
                    <Body style={{ fontWeight: '700', fontSize: 18, flex: 1 }}>{g.name}</Body>
                    <Button small variant="secondary" icon="person-add-outline" title="Add" onPress={() => { setError(null); setAdding(g); }} />
                  </Row>
                  {g.members.length === 0 ? <Body small muted style={{ marginTop: spacing.sm }}>No students yet.</Body> : null}
                  {g.members.map((m) => (
                    <Row key={m.id} style={{ marginTop: spacing.sm, justifyContent: 'space-between' }}>
                      <Row style={{ flex: 1 }}>
                        <Avatar name={m.name} size={30} />
                        <View style={{ flex: 1 }}><Body>{m.name}</Body><Body small muted>{m.email}</Body></View>
                      </Row>
                      <Button small variant="ghost" icon="close-circle-outline" title="Remove" onPress={() => confirmRemove(g, m)} />
                    </Row>
                  ))}
                </Card>
              ))}
              <AddStudentModal
                group={adding} groups={groups} error={error}
                onClose={() => setAdding(null)}
                onAdd={async (student) => { if (adding) await run(() => projectsApi.addMember(adding.id, student.id)); }}
              />
            </>
          )
        }
      </Async>
    </Screen>
  );
}

function AddStudentModal({ group, groups, error, onClose, onAdd }: {
  group: Group | null; groups: Group[]; error: string | null; onClose: () => void; onAdd: (s: UserBrief) => Promise<void>;
}) {
  const [q, setQ] = useState('');
  const [results, setResults] = useState<UserBrief[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Debounced search; also loads the first page when the sheet opens
  useEffect(() => {
    if (!group) return;
    let cancelled = false;
    const t = setTimeout(() => {
      projectsApi.searchStudents(q).then((r) => !cancelled && (setResults(r), setSearchError(null)), (e) => !cancelled && setSearchError(getErrorMessage(e)));
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [q, group]);

  const groupOf = (userId: number) => groups.find((g) => g.members.some((m) => m.id === userId));

  return (
    <FormModal visible={!!group} title={group ? `Add to ${group.name}` : ''} onClose={onClose}>
      <ErrorBanner message={error ?? searchError} />
      <TextField placeholder="Search students by name or email" value={q} onChangeText={setQ} autoCapitalize="none" />
      {results.length === 0 ? <Body muted>No students found.</Body> : null}
      {results.map((s) => {
        const existing = groupOf(s.id);
        return (
          <Row key={s.id} style={{ justifyContent: 'space-between', marginBottom: spacing.sm }}>
            <View style={{ flex: 1 }}>
              <Body>{s.name}</Body>
              <Body small muted>{existing ? `In ${existing.name}` : s.email}</Body>
            </View>
            <Button small title={existing ? (existing.id === group?.id ? 'Added' : 'In a group') : 'Add'} disabled={!!existing} onPress={() => onAdd(s)} />
          </Row>
        );
      })}
    </FormModal>
  );
}
