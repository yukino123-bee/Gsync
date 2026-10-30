export type Role = 'student' | 'teacher' | 'admin';
export type TaskStatus = 'todo' | 'in_progress' | 'done';
export type MilestoneStatus = 'pending' | 'submitted' | 'reviewed';

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  created_at: string;
}

export interface UserBrief {
  id: number;
  name: string;
  email: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthResponse extends TokenPair {
  user: User;
}

export interface Project {
  id: number;
  teacher_id: number;
  title: string;
  description: string;
  rubric: string;
  deadline: string | null;
  created_at: string;
  group_count: number;
}

export interface Group {
  id: number;
  project_id: number;
  name: string;
  created_at: string;
  members: UserBrief[];
  project: Project;
}

export interface Task {
  id: number;
  group_id: number;
  title: string;
  description: string;
  assignee_id: number | null;
  status: TaskStatus;
  due_date: string | null;
  created_by: number;
  created_at: string;
  completed_at: string | null;
}

export interface Milestone {
  id: number;
  group_id: number;
  title: string;
  due_date: string | null;
  status: MilestoneStatus;
}

export interface Comment {
  id: number;
  milestone_id: number;
  teacher_id: number;
  teacher_name: string;
  content: string;
  created_at: string;
}

export interface FileItem {
  id: number;
  group_id: number;
  uploader_id: number;
  filename: string;
  version: number;
  size: number;
  mime_type: string;
  uploaded_at: string;
  is_latest: boolean;
}

export interface Note {
  id: number;
  group_id: number;
  author_id: number;
  author_name: string;
  content: string;
  created_at: string;
}

export interface Activity {
  id: number;
  group_id: number;
  user_id: number;
  user_name: string;
  action_type: string;
  reference_id: number | null;
  description: string;
  created_at: string;
}

export interface GroupStats {
  total_tasks: number;
  todo_tasks: number;
  in_progress_tasks: number;
  done_tasks: number;
  percent_done: number;
  overdue_tasks: number;
  next_milestone: Milestone | null;
  last_activity_at: string | null;
  is_inactive: boolean;
}

export interface GroupCard extends GroupStats {
  group_id: number;
  name: string;
  member_count: number;
}

export interface ProjectDashboard {
  project: Project;
  groups: GroupCard[];
}

export interface EvaluationStatus {
  is_open: boolean;
  has_submitted: boolean;
  final_milestone: Milestone | null;
  members_to_rate: UserBrief[];
}

export interface EvaluationItem {
  evaluatee_id: number;
  rating: number;
  comment?: string | null;
}

export interface MemberEvaluationSummary {
  user: UserBrief;
  average_rating: number | null;
  rating_count: number;
  ratings: { evaluator: UserBrief; rating: number; comment: string | null }[];
  tasks_completed: number;
  activity_count: number;
}

export interface EvaluationSummary {
  group_id: number;
  member_count: number;
  submitted_count: number;
  members: MemberEvaluationSummary[];
}

export interface AppNotification {
  id: number;
  title: string;
  body: string;
  type: string;
  group_id: number | null;
  reference_id: number | null;
  is_read: boolean;
  created_at: string;
}
