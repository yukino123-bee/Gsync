# Import every model so Base.metadata (and Alembic) sees all tables.
from app.models.project import Group, GroupHealth, GroupMember, GroupStatus, Project, TeacherGroup
from app.models.user import Role, User
from app.models.workspace import (
    ActivityLog,
    Comment,
    FileRecord,
    Milestone,
    MilestoneStatus,
    Note,
    Notification,
    PeerEvaluation,
    Task,
    TaskStatus,
)

__all__ = [
    "ActivityLog", "Comment", "FileRecord", "Group", "GroupHealth", "GroupMember", "GroupStatus", "Milestone",
    "MilestoneStatus", "Note", "Notification", "PeerEvaluation", "Project", "Role",
    "Task", "TaskStatus", "TeacherGroup", "User",
]
