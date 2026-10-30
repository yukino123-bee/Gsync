import { useRouter } from 'expo-router';
import { FlatList, View } from 'react-native';

import { projectsApi } from '@/api/projects';
import { Async } from '@/components/Async';
import { Badge, Body, Button, Card, EmptyState, Row } from '@/components/ui';
import { spacing } from '@/theme';
import { formatDate } from '@/utils/format';
import { useLoad } from '@/utils/useLoad';

export default function Projects() {
  const router = useRouter();
  const load = useLoad(() => projectsApi.list());

  return (
    <Async load={load}>
      {(projects) => (
        <FlatList
          data={projects}
          keyExtractor={(p) => String(p.id)}
          refreshing={load.refreshing}
          onRefresh={load.refresh}
          contentContainerStyle={{ padding: spacing.lg, flexGrow: 1 }}
          ListHeaderComponent={
            <View style={{ marginBottom: spacing.md }}>
              <Button title="New project" icon="add" onPress={() => router.push('/project/new')} />
            </View>
          }
          ListEmptyComponent={
            <EmptyState icon="folder-open-outline" title="No projects yet" message="Create a project, then split your class into groups." />
          }
          renderItem={({ item }) => (
            <Card onPress={() => router.push({ pathname: '/project/[id]', params: { id: String(item.id) } })}>
              <Body style={{ fontWeight: '700', fontSize: 18 }}>{item.title}</Body>
              {item.description ? <Body small muted numberOfLines={2}>{item.description}</Body> : null}
              <Row style={{ marginTop: spacing.md }}>
                <Badge tone="info" icon="people" label={`${item.group_count} group${item.group_count === 1 ? '' : 's'}`} />
                {item.deadline ? <Badge icon="calendar" label={`Due ${formatDate(item.deadline)}`} /> : null}
              </Row>
            </Card>
          )}
        />
      )}
    </Async>
  );
}
