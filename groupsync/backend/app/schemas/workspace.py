from typing import Literal

from pydantic import BaseModel, Field

from app.models import MilestoneStatus, TaskStatus
from app.schemas.common import ORMModel, UserBrief, UtcDatetime


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    assignee_id: int | None = None
    due_date: UtcDatetime | None = None
    status: TaskStatus = TaskStatus.todo


class TaskUpdate(BaseModel):
    """Partial update: only fields present in the request body are changed."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    assignee_id: int | None = None
    due_date: UtcDatetime | None = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskOut(ORMModel):
    id: int
    group_id: int
    title: str
    description: str
    assignee_id: int | None
    status: TaskStatus
    due_date: UtcDatetime | None
    created_by: int
    created_at: UtcDatetime
    completed_at: UtcDatetime | None


class MilestoneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    due_date: UtcDatetime | None = None


class MilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    due_date: UtcDatetime | None = None
    # Students can't mark a milestone "reviewed"; that happens when the teacher comments
    status: Literal["pending", "submitted"] | None = None


class MilestoneOut(ORMModel):
    id: int
    group_id: int
    title: str
    due_date: UtcDatetime | None
    status: MilestoneStatus


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class CommentOut(BaseModel):
    id: int
    milestone_id: int
    teacher_id: int
    teacher_name: str
    content: str
    created_at: UtcDatetime


class FileOut(ORMModel):
    id: int
    group_id: int
    uploader_id: int
    filename: str
    version: int
    size: int
    mime_type: str
    uploaded_at: UtcDatetime
    is_latest: bool = True


class NoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class NoteOut(BaseModel):
    id: int
    group_id: int
    author_id: int
    author_name: str
    content: str
    created_at: UtcDatetime


class ActivityOut(BaseModel):
    id: int
    group_id: int
    user_id: int
    user_name: str
    action_type: str
    reference_id: int | None
    description: str
    created_at: UtcDatetime


class EvaluationItem(BaseModel):
    evaluatee_id: int
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class EvaluationSubmit(BaseModel):
    evaluations: list[EvaluationItem] = Field(min_length=1)


class EvaluationStatus(BaseModel):
    is_open: bool
    has_submitted: bool
    final_milestone: MilestoneOut | None
    members_to_rate: list[UserBrief]


class EvaluationRatingOut(BaseModel):
    evaluator: UserBrief
    rating: int
    comment: str | None


class MemberEvaluationSummary(BaseModel):
    user: UserBrief
    average_rating: float | None
    rating_count: int
    ratings: list[EvaluationRatingOut]
    tasks_completed: int
    activity_count: int


class EvaluationSummary(BaseModel):
    group_id: int
    member_count: int
    submitted_count: int
    members: list[MemberEvaluationSummary]


class NotificationOut(ORMModel):
    id: int
    title: str
    body: str
    type: str
    group_id: int | None
    reference_id: int | None
    is_read: bool
    created_at: UtcDatetime


class MilestoneBrief(ORMModel):
    id: int
    title: str
    due_date: UtcDatetime | None
    status: MilestoneStatus


class GroupStats(BaseModel):
    total_tasks: int
    todo_tasks: int
    in_progress_tasks: int
    done_tasks: int
    percent_done: int
    overdue_tasks: int
    next_milestone: MilestoneBrief | None
    last_activity_at: UtcDatetime | None
    is_inactive: bool


class GroupCard(GroupStats):
    group_id: int
    name: str
    member_count: int
