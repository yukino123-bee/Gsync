from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Group, GroupMember, GroupStatus, Project, Role, TeacherGroup, User


def get_group(db: Session, group_id: int) -> Group:
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Group not found")
    return group


def is_member(db: Session, group_id: int, user_id: int) -> bool:
    return (
        db.scalar(
            select(GroupMember.id).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
        )
        is not None
    )


def teacher_link(db: Session, group_id: int) -> TeacherGroup | None:
    """The teacher currently linked to a group (a group has at most one)."""
    return db.scalar(select(TeacherGroup).where(TeacherGroup.group_id == group_id))


def is_linked_teacher(db: Session, group_id: int, teacher_id: int) -> bool:
    return (
        db.scalar(
            select(TeacherGroup.id).where(TeacherGroup.group_id == group_id, TeacherGroup.teacher_id == teacher_id)
        )
        is not None
    )


def authorize_group(db: Session, group_id: int, user: User) -> Group:
    """Read access: a member of the group, or the teacher who added it with its Group ID."""
    group = get_group(db, group_id)
    if user.role == Role.teacher and is_linked_teacher(db, group_id, user.id):
        return group
    if user.role == Role.student and is_member(db, group_id, user.id):
        return group
    raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have access to this group")


def require_member(db: Session, group_id: int, user: User) -> Group:
    """Write access: only student members, and only while the group is not archived."""
    group = authorize_group(db, group_id, user)
    if user.role != Role.student:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Teachers have read-only access to group workspaces")
    if group.status == GroupStatus.archived:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This group is archived and read-only")
    return group


def linked_group(db: Session, group_id: int, teacher: User) -> Group:
    """A group on this teacher's dashboard (403 if it is not)."""
    return authorize_group(db, group_id, teacher)


def owned_project(db: Session, project_id: int, teacher: User) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if project.teacher_id != teacher.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not own this project")
    return project
