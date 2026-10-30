from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel, UserBrief, UtcDatetime

HealthStatus = Literal["on_track", "needs_attention", "inactive"]


class GroupCreateByStudent(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class GroupCodeRequest(BaseModel):
    # Accepts "GS-4K7P2Q", "gs4k7p2q" or "4K7P2Q"; the server normalises it
    group_code: str = Field(min_length=1, max_length=20)


class CodeAction(BaseModel):
    action: Literal["regenerate", "disable", "enable"]


class CodeOut(BaseModel):
    group_id: int
    group_code: str
    join_enabled: bool


class GroupLookup(BaseModel):
    """What a teacher sees before confirming 'Add group'."""

    group_id: int
    name: str
    group_code: str
    status: str
    join_enabled: bool
    member_count: int
    members: list[UserBrief]
    already_added: bool
    can_add: bool
    # Plain-language reason shown when can_add is false
    blocked_reason: str | None = None


class TeacherGroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    archived: bool | None = None


class ProjectAttach(BaseModel):
    project_id: int | None = None


class WarningOut(BaseModel):
    code: str
    severity: Literal["warning", "danger"]
    message: str
    member_id: int | None = None


class MemberContribution(BaseModel):
    user: UserBrief
    tasks_assigned: int
    completed_tasks: int
    overdue_tasks: int
    files_uploaded: int
    notes_added: int
    # completed_tasks + files_uploaded + notes_added
    points: int
    share_percent: int
    last_active_at: UtcDatetime | None
    days_inactive: int
    is_inactive: bool


class TaskHealth(BaseModel):
    todo: int
    in_progress: int
    done: int
    overdue: int
    total: int


class ScoreComponents(BaseModel):
    workload_balance: int | None
    on_time: int | None
    activity: int | None
    milestones: int | None


class CoordinationOut(BaseModel):
    group_id: int
    # None until the group has any tasks, files, notes or milestones
    score: int | None
    status: HealthStatus
    components: ScoreComponents
    task_health: TaskHealth
    percent_done: int
    last_activity_at: UtcDatetime | None
    is_inactive: bool
    members: list[MemberContribution]
    warnings: list[WarningOut]
    calculated_at: UtcDatetime


class TeacherGroupCard(BaseModel):
    group_id: int
    name: str
    group_code: str
    group_status: str  # active / archived
    member_count: int
    percent_done: int
    health: HealthStatus
    coordination_score: int | None
    overdue_tasks: int
    last_activity_at: UtcDatetime | None
    warning_count: int
    top_warning: str | None
    project_title: str | None
    added_at: UtcDatetime


class OverviewCounts(BaseModel):
    total: int
    needs_attention: int
    inactive: int
    on_track: int


class TeacherOverview(BaseModel):
    counts: OverviewCounts
    groups: list[TeacherGroupCard]
