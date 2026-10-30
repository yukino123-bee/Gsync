import { create } from 'zustand';

import { notificationsApi } from '@/api/notifications';

interface NotificationState {
  unread: number;
  refreshUnread: () => Promise<void>;
  setUnread: (n: number) => void;
}

export const useNotificationStore = create<NotificationState>((set) => ({
  unread: 0,
  async refreshUnread() {
    try {
      set({ unread: await notificationsApi.unreadCount() });
    } catch {
      // The badge is cosmetic; ignore transient failures
    }
  },
  setUnread: (unread) => set({ unread }),
}));
