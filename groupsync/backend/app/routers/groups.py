from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.deps import CurrentUser, DbSession, StudentUser, TeacherUser
from app.models import Group, GroupMember, GroupStatus, Role, TeacherGroup
from app.routers.projects import group_out
from app.schemas.classroom import (
    CodeAction, CodeOut, CoordinationOut, GroupCodeRequest, GroupCreateByStudent, GroupLookup,
)
from app.schemas.project import GroupOut
from app.schemas.workspace import GroupStats
from app.services.access import authorize_group, get_group, is_linked_teacher, is_member, teacher_link
from app.services.activity import log_activity
from app.services.coordination import compute_coordination, save_health
from app.services.group_code import generate_code, is_valid_format, normalize_code
from app.services.progress import group_stats

router = APIRouter(tags=["groups"])

BAD_CODE = "That Group ID doesn't look right. It should look like GS-4K7P2Q."
UNKNOWN_CODE = "No group found with that Group ID. Check the code and try again."


def find_group_by_code(db, raw: str) -> Group:
    code = normalize_code(raw)
    if not is_valid_format(code):
        raise HTTPException(status.HTTP_404_NOT_FOUND, BAD_CODE)
    group = db.scalar(select(Group).where(Group.group_code == code))
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, UNKNOWN_CODE)
    return group


def member_count(db, group_id: int) -> int:
    return db.scalar(select(func.count()).select_from(GroupMember).where(GroupMember.group_id == group_id)) or 0


@router.get("/groups/my", response_model=list[GroupOut])
def my_groups(user: CurrentUser, db: DbSession):
    """Students: groups they belong to. Teachers: groups on their dashboard."""
    stmt = select(Group).options(selectinload(Group.members).selectinload(GroupMember.user))
    if user.role == Role.student:
        stmt = stmt.join(GroupMember).where(GroupMember.user_id == user.id)
    elif user.role == Role.teacher:
        stmt = stmt.join(TeacherGroup, TeacherGroup.group_id == Group.id).where(TeacherGroup.teacher_id == user.id)
    else:
        return []
    return [group_out(db, g) for g in db.scalars(stmt.order_by(Group.id))]


@router.post("/groups", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(body: GroupCreateByStudent, student: StudentUser, db: DbSession):
    """A student starts a group and gets a Group ID to share with classmates and their teacher."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Give the group a name")
    group = Group(name=name, group_code=generate_code(db), created_by=student.id)
    db.add(group)
    db.flush()
    db.add(GroupMember(group_id=group.id, user_id=student.id))
    log_activity(db, group.id, student.id, "group_created", f"{student.name} created the group", group.id)
    db.commit()
    db.refresh(group)
    return group_out(db, group)


@router.post("/groups/join", response_model=GroupOut)
def join_group(body: GroupCodeRequest, student: StudentUser, db: DbSession):
    group = find_group_by_code(db, body.group_code)
    if is_member(db, group.id, student.id):
        raise HTTPException(status.HTTP_409_CONFLICT, f"You're already in {group.name}.")
    if group.status == GroupStatus.archived:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "That group is archived, so no one can join it.")
    if not group.join_enabled:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Joining is turned off for this group. Ask a member for a new Group ID."
        )
    if member_count(db, group.id) >= settings.group_max_members:
        raise HTTPException(status.HTTP_409_CONFLICT, f"That group is full (max {settings.group_max_members} members).")
    log_activity(db, group.id, student.id, "member_joined", f"{student.name} joined the group", student.id)
    db.add(GroupMember(group_id=group.id, user_id=student.id))
    db.commit()
    db.refresh(group)
    return group_out(db, group)


@router.get("/groups/lookup/{group_code}", response_model=GroupLookup)
def lookup_group(group_code: str, teacher: TeacherUser, db: DbSession):
    """Preview a group before adding it to the dashboard. Invalid IDs are a 404; other problems come back as can_add=false."""
    group = find_group_by_code(db, group_code)
    link = teacher_link(db, group.id)
    already = link is not None and link.teacher_id == teacher.id
    reason = None
    if already:
        reason = f"{group.name} is already on your dashboard."
    elif link is not None:
        reason = "This group is already linked to another teacher."
    elif group.status == GroupStatus.archived:
        reason = "This group is archived."
    elif not group.join_enabled:
        reason = "This Group ID has been disabled. Ask the group for a new one."
    members = [m.user for m in sorted(group.members, key=lambda m: m.id)]
    return GroupLookup(
        group_id=group.id, name=group.name, group_code=group.group_code, status=group.status.value,
        join_enabled=group.join_enabled, member_count=len(members), members=members,
        already_added=already, can_add=reason is None, blocked_reason=reason,
    )


@router.get("/groups/{group_id}", response_model=GroupOut)
def get_group_detail(group_id: int, user: CurrentUser, db: DbSession):
    return group_out(db, authorize_group(db, group_id, user))


@router.get("/groups/{group_id}/dashboard", response_model=GroupStats)
def get_group_dashboard(group_id: int, user: CurrentUser, db: DbSession):
    return group_stats(db, authorize_group(db, group_id, user))


@router.patch("/groups/{group_id}/code", response_model=CodeOut)
def change_group_code(group_id: int, body: CodeAction, user: CurrentUser, db: DbSession):
    """Regenerate, disable or re-enable the Group ID. Allowed for the group's creator and its teacher."""
    group = get_group(db, group_id)
    allowed = (
        (user.role == Role.teacher and is_linked_teacher(db, group.id, user.id))
        or (user.role == Role.student and group.created_by == user.id and is_member(db, group.id, user.id))
    )
    if not allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the group's creator or its teacher can change the Group ID")
    if group.status == GroupStatus.archived:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Archived groups cannot change their Group ID")

    if body.action == "regenerate":
        group.group_code = generate_code(db)
        text = f"{user.name} generated a new Group ID"
    elif body.action == "disable":
        group.join_enabled = False
        text = f"{user.name} turned off joining"
    else:
        group.join_enabled = True
        text = f"{user.name} turned on joining"
    log_activity(db, group.id, user.id, f"group_code_{body.action}", text, group.id)
    db.commit()
    return CodeOut(group_id=group.id, group_code=group.group_code, join_enabled=group.join_enabled)


@router.get("/groups/{group_id}/coordination", response_model=CoordinationOut)
def group_coordination(group_id: int, user: CurrentUser, db: DbSession):
    group = authorize_group(db, group_id, user)
    result = compute_coordination(db, group)
    save_health(db, result)
    db.commit()
    return result
