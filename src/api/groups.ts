import { Platform } from 'react-native';

import { api } from './client';
import type {
  Activity, Comment, EvaluationItem, EvaluationStatus, EvaluationSummary, FileItem, Group, GroupStats,
  Milestone, Note, Task, TaskStatus,
} from '@/types';

export interface TaskInput {
  title: string;
  description?: string;
  assignee_id?: number | null;
  due_date?: string | null;
}

export interface UploadAsset {
  uri: string;
  name: string;
  mimeType?: string;
}

export const groupsApi = {
  mine: () => api.get<Group[]>('/groups/my').then((r) => r.data),
  get: (id: number) => api.get<Group>(`/groups/${id}`).then((r) => r.data),
  stats: (id: number) => api.get<GroupStats>(`/groups/${id}/dashboard`).then((r) => r.data),

  tasks: (id: number) => api.get<Task[]>(`/groups/${id}/tasks`).then((r) => r.data),
  createTask: (id: number, body: TaskInput) => api.post<Task>(`/groups/${id}/tasks`, body).then((r) => r.data),
  updateTask: (taskId: number, body: TaskInput) => api.put<Task>(`/tasks/${taskId}`, body).then((r) => r.data),
  setTaskStatus: (taskId: number, status: TaskStatus) =>
    api.patch<Task>(`/tasks/${taskId}/status`, { status }).then((r) => r.data),
  deleteTask: (taskId: number) => api.delete(`/tasks/${taskId}`),

  milestones: (id: number) => api.get<Milestone[]>(`/groups/${id}/milestones`).then((r) => r.data),
  createMilestone: (id: number, body: { title: string; due_date?: string | null }) =>
    api.post<Milestone>(`/groups/${id}/milestones`, body).then((r) => r.data),
  updateMilestone: (
    milestoneId: number,
    body: { title?: string; due_date?: string | null; status?: 'pending' | 'submitted' },
  ) => api.put<Milestone>(`/milestones/${milestoneId}`, body).then((r) => r.data),
  comments: (milestoneId: number) => api.get<Comment[]>(`/milestones/${milestoneId}/comments`).then((r) => r.data),
  addComment: (milestoneId: number, content: string) =>
    api.post<Comment>(`/milestones/${milestoneId}/comments`, { content }).then((r) => r.data),

  files: (id: number) => api.get<FileItem[]>(`/groups/${id}/files`).then((r) => r.data),
  uploadFile: async (id: number, asset: UploadAsset) => {
    const form = new FormData();
    if (Platform.OS === 'web') {
      // Browsers need a real Blob; the picker's uri is a blob:/data: URL
      const blob = await (await fetch(asset.uri)).blob();
      form.append('file', blob, asset.name);
    } else {
      // React Native's FormData accepts a { uri, name, type } descriptor in place of a Blob
      form.append('file', {
        uri: asset.uri,
        name: asset.name,
        type: asset.mimeType ?? 'application/octet-stream',
      } as unknown as Blob);
    }
    return api
      .post<FileItem>(`/groups/${id}/files`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60_000,
      })
      .then((r) => r.data);
  },

  notes: (id: number) => api.get<Note[]>(`/groups/${id}/notes`).then((r) => r.data),
  addNote: (id: number, content: string) => api.post<Note>(`/groups/${id}/notes`, { content }).then((r) => r.data),

  activity: (id: number, limit = 100) =>
    api.get<Activity[]>(`/groups/${id}/activity`, { params: { limit } }).then((r) => r.data),

  evaluationStatus: (id: number) => api.get<EvaluationStatus>(`/groups/${id}/evaluations/status`).then((r) => r.data),
  submitEvaluations: (id: number, evaluations: EvaluationItem[]) =>
    api.post(`/groups/${id}/evaluations`, { evaluations }),
  evaluationSummary: (id: number) =>
    api.get<EvaluationSummary>(`/groups/${id}/evaluations/summary`).then((r) => r.data),
};
