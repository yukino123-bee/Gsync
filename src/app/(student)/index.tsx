import { FlatList } from 'react-native';

import { groupsApi } from '@/api/groups';
import { Async } from '@/components/Async';
import { GroupSummaryCard } from '@/components/GroupCardView';
import { EmptyState } from '@/components/ui';
import { spacing } from '@/theme';
import { useLoad } from '@/utils/useLoad';

export default function MyGroups() {
  const load = useLoad(async () => {
    const groups = await groupsApi.mine();
    const stats = await Promise.all(groups.map((g) => groupsApi.stats(g.id)));
    return groups.map((group, i) => ({ group, stats: stats[i]! }));
  });

  return (
    <Async load={load}>
      {(items) => (
        <FlatList
          data={items}
          keyExtractor={(i) => String(i.group.id)}
          refreshing={load.refreshing}
          onRefresh={load.refresh}
          contentContainerStyle={{ padding: spacing.lg, flexGrow: 1 }}
          ListEmptyComponent={
            <EmptyState icon="people-outline" title="No groups yet" message="Your teacher hasn't added you to a group. Once they do, it will show up here." />
          }
          renderItem={({ item }) => <GroupSummaryCard group={item.group} stats={item.stats} />}
        />
      )}
    </Async>
  );
}
