import { api } from './client';
import type { Group, Project, ProjectDashboard, UserBrief } from '@/types';

export interface ProjectInput {
  title: string;
  description?: string;
  rubric?: string;
  deadline?: string | null;
}

export const projectsApi = {
  list: () => api.get<Project[]>('/projects').then((r) => r.data),
  get: (id: number) => api.get<Project>(`/projects/${id}`).then((r) => r.data),
  create: (body: ProjectInput) => api.post<Project>('/projects', body).then((r) => r.data),
  update: (id: number, body: Partial<ProjectInput>) => api.put<Project>(`/projects/${id}`, body).then((r) => r.data),
  remove: (id: number) => api.delete(`/projects/${id}`),
  dashboard: (id: number) => api.get<ProjectDashboard>(`/projects/${id}/dashboard`).then((r) => r.data),

  groups: (id: number) => api.get<Group[]>(`/projects/${id}/groups`).then((r) => r.data),
  createGroup: (id: number, name: string, member_ids: number[] = []) =>
    api.post<Group>(`/projects/${id}/groups`, { name, member_ids }).then((r) => r.data),
  randomize: (id: number, group_size: number) =>
    api.post<Group[]>(`/projects/${id}/groups/randomize`, { group_size }).then((r) => r.data),
  addMember: (groupId: number, user_id: number) =>
    api.post<Group>(`/groups/${groupId}/members`, { user_id }).then((r) => r.data),
  removeMember: (groupId: number, userId: number) => api.delete(`/groups/${groupId}/members/${userId}`),
  searchStudents: (q: string) => api.get<UserBrief[]>('/users/students', { params: { q } }).then((r) => r.data),
};
