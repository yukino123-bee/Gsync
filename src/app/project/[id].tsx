import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Alert } from '@/utils/alert';

import { projectsApi } from '@/api/projects';
import { Async } from '@/components/Async';
import { TeacherGroupCard } from '@/components/TeacherGroupCard';
import { Body, Button, Card, EmptyState, ErrorBanner, Row, Screen, SectionHeader } from '@/components/ui';
import { spacing } from '@/theme';
import { getErrorMessage } from '@/utils/errors';
import { formatDate } from '@/utils/format';
import { useLoad } from '@/utils/useLoad';

export default function ProjectDashboard() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const projectId = Number(id);
  const load = useLoad(() => projectsApi.dashboard(projectId), [projectId]);
  const [showRubric, setShowRubric] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function confirmDelete(title: string) {
    Alert.alert('Delete project', `Delete "${title}" and all of its groups, tasks and files? This can't be undone.`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete', style: 'destructive',
        onPress: async () => {
          try {
            await projectsApi.remove(projectId);
            router.back();
          } catch (e) {
            setError(getErrorMessage(e));
          }
        },
      },
    ]);
  }

  return (
    <Screen refreshing={load.refreshing} onRefresh={load.refresh}>
      <Async load={load}>
        {({ project, groups }) => (
          <>
            <Stack.Screen options={{ title: project.title }} />
            <ErrorBanner message={error} />
            <Card>
              <Body style={{ fontWeight: '700', fontSize: 18 }}>{project.title}</Body>
              {project.deadline ? <Body small muted>Deadline: {formatDate(project.deadline)}</Body> : null}
              {project.description ? <Body small style={{ marginTop: spacing.sm }}>{project.description}</Body> : null}
              {project.rubric ? (
                <>
                  <Button small variant="ghost" icon="list-outline" title={showRubric ? 'Hide rubric' : 'View rubric'} onPress={() => setShowRubric((v) => !v)} style={{ alignSelf: 'flex-start' }} />
                  {showRubric ? <Body small>{project.rubric}</Body> : null}
                </>
              ) : null}
            </Card>

            <Row>
              <Button style={{ flex: 1 }} icon="people-outline" variant="secondary" title="Manage groups" onPress={() => router.push({ pathname: '/manage-groups/[id]', params: { id: String(project.id) } })} />
              <Button icon="trash-outline" variant="ghost" title="Delete" onPress={() => confirmDelete(project.title)} />
            </Row>

            <SectionHeader title={`Groups (${groups.length})`} />
            {groups.length === 0 ? (
              <EmptyState icon="people-outline" title="No groups yet" message="Create groups or split your class randomly." />
            ) : (
              groups.map((g) => <TeacherGroupCard key={g.group_id} card={g} />)
            )}
          </>
        )}
      </Async>
    </Screen>
  );
}
