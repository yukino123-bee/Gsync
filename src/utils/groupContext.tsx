import { createContext, useContext } from 'react';

import type { Group } from '@/types';

export interface GroupContextValue {
  group: Group;
  /** Teachers see the workspace read-only. */
  readOnly: boolean;
  reloadGroup: () => void;
  /** Peer evaluation unlocks once the final milestone is submitted. */
  evalOpen: boolean;
  refreshEval: () => void;
  memberName: (id: number | null | undefined) => string;
}

export const GroupContext = createContext<GroupContextValue | null>(null);

export function useGroup(): GroupContextValue {
  const ctx = useContext(GroupContext);
  if (!ctx) throw new Error('useGroup must be used inside the group layout');
  return ctx;
}
