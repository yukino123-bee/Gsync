import math
import random

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from app.deps import DbSession, TeacherUser
from app.models import Group, GroupMember, Project, Role, Task, TeacherGroup, User
from app.schemas.project import (
    GroupCreate,
    GroupOut,
    MemberAdd,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    RandomizeRequest,
)
from app.schemas.workspace import GroupCard
from app.services.access import get_group, owned_project, teacher_link
from app.services.group_code import generate_code
from app.services.progress import group_stats

router = APIRouter(tags=["projects"])


def project_out(db, project: Project) -> ProjectOut:
    count = db.scalar(select(func.count()).select_from(Group).where(Group.project_id == project.id))
    out = ProjectOut.model_validate(project)
    out.group_count = count or 0
    return out


def group_out(db, group: Group) -> GroupOut:
    link = teacher_link(db, group.id)
    return GroupOut(
        id=group.id,
        project_id=group.project_id,
        name=group.name,
        group_code=group.group_code,
        status=group.status.value,
        join_enabled=group.join_enabled,
        created_by=group.created_by,
        created_at=group.created_at,
        members=[m.user for m in group.members],
        teacher=db.get(User, link.teacher_id) if link else None,
        project=project_out(db, group.project) if group.project else None,
    )


def new_project_group(db, project: Project, name: str) -> Group:
    """A teacher-created group inside a project: it gets a Group ID and goes straight onto that teacher's dashboard."""
    group = Group(project_id=project.id, name=name, group_code=generate_code(db))
    db.add(group)
    db.flush()
    db.add(TeacherGroup(teacher_id=project.teacher_id, group_id=group.id))
    db.flush()
    return group


def _project_group(db, group_id: int, teacher: User) -> Group:
    """Legacy member management: only for groups inside one of this teacher's projects."""
    group = get_group(db, group_id)
    if group.project_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Students join this group with its Group ID")
    owned_project(db, group.project_id, teacher)
    return group


def _students_in_project(db, project_id: int) -> set[int]:
    rows = db.scalars(
        select(GroupMember.user_id).join(Group).where(Group.project_id == project_id)
    )
    return set(rows)


def _add_members(db, group: Group, user_ids: list[int]) -> None:
    """Add students to a group, enforcing one group per student per project."""
    taken = _students_in_project(db, group.project_id)
    for uid in dict.fromkeys(user_ids):
        user = db.get(User, uid)
        if user is None or user.role != Role.student:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"User {uid} is not a student")
        if uid in taken:
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"{user.name} is already in a group for this project"
            )
        db.add(GroupMember(group_id=group.id, user_id=uid))
        taken.add(uid)
    db.flush()


# ---- projects ----------------------------------------------------------------


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, teacher: TeacherUser, db: DbSession):
    project = Project(teacher_id=teacher.id, **body.model_dump())
    db.add(project)
    db.commit()
    return project_out(db, project)


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(teacher: TeacherUser, db: DbSession):
    projects = db.scalars(
        select(Project).where(Project.teacher_id == teacher.id).order_by(Project.created_at.desc(), Project.id.desc())
    )
    return [project_out(db, p) for p in projects]


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, teacher: TeacherUser, db: DbSession):
    return project_out(db, owned_project(db, project_id, teacher))


@router.put("/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, body: ProjectUpdate, teacher: TeacherUser, db: DbSession):
    project = owned_project(db, project_id, teacher)
    for key in body.model_fields_set:
        value = getattr(body, key)
        if value is None and key != "deadline":
            continue  # non-nullable columns ignore explicit nulls
        setattr(project, key, value)
    db.commit()
    return project_out(db, project)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, teacher: TeacherUser, db: DbSession):
    project = owned_project(db, project_id, teacher)
    # Groups belong to their students: detach them instead of deleting their work
    db.execute(update(Group).where(Group.project_id == project.id).values(project_id=None))
    db.refresh(project)
    db.delete(project)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- groups (teacher) ----------------------------------------------------------


@router.get("/projects/{project_id}/groups", response_model=list[GroupOut])
def list_project_groups(project_id: int, teacher: TeacherUser, db: DbSession):
    project = owned_project(db, project_id, teacher)
    groups = db.scalars(
        select(Group)
        .where(Group.project_id == project.id)
        .options(selectinload(Group.members).selectinload(GroupMember.user))
        .order_by(Group.id)
    )
    return [group_out(db, g) for g in groups]


@router.post("/projects/{project_id}/groups", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(project_id: int, body: GroupCreate, teacher: TeacherUser, db: DbSession):
    project = owned_project(db, project_id, teacher)
    group = new_project_group(db, project, body.name.strip())
    try:
        _add_members(db, group, body.member_ids)
    except HTTPException:
        db.rollback()
        raise
    db.commit()
    db.refresh(group)
    return group_out(db, group)


@router.post(
    "/projects/{project_id}/groups/randomize",
    response_model=list[GroupOut],
    status_code=status.HTTP_201_CREATED,
)
def randomize_groups(project_id: int, body: RandomizeRequest, teacher: TeacherUser, db: DbSession):
    project = owned_project(db, project_id, teacher)
    if body.student_ids is None:
        candidates = set(db.scalars(select(User.id).where(User.role == Role.student)))
    else:
        candidates = set(body.student_ids)
        found = set(db.scalars(select(User.id).where(User.id.in_(candidates), User.role == Role.student)))
        if found != candidates:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Some selected users are not students")
    pool = list(candidates - _students_in_project(db, project.id))
    if not pool:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No ungrouped students available")

    random.shuffle(pool)
    n_groups = math.ceil(len(pool) / body.group_size)
    existing = db.scalar(select(func.count()).select_from(Group).where(Group.project_id == project.id)) or 0
    groups = [new_project_group(db, project, f"Group {existing + i + 1}") for i in range(n_groups)]
    # Round-robin keeps group sizes within one of each other (no lonely leftover group)
    for i, uid in enumerate(pool):
        db.add(GroupMember(group_id=groups[i % n_groups].id, user_id=uid))
    db.commit()
    for g in groups:
        db.refresh(g)
    return [group_out(db, g) for g in groups]


@router.post("/groups/{group_id}/members", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def add_member(group_id: int, body: MemberAdd, teacher: TeacherUser, db: DbSession):
    group = _project_group(db, group_id, teacher)
    user_id = body.user_id
    if body.email:
        user = db.scalar(select(User).where(User.email == body.email.lower()))
        if user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No user with that email")
        user_id = user.id
    try:
        _add_members(db, group, [user_id])
    except HTTPException:
        db.rollback()
        raise
    db.commit()
    db.refresh(group)
    return group_out(db, group)


@router.delete("/groups/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(group_id: int, user_id: int, teacher: TeacherUser, db: DbSession):
    _project_group(db, group_id, teacher)
    member = db.scalar(
        select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
    )
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That student is not in this group")
    # Keep their tasks but unassign them
    for task in db.scalars(select(Task).where(Task.group_id == group_id, Task.assignee_id == user_id)):
        task.assignee_id = None
    db.delete(member)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- teacher dashboard ------------------------------------------------------------


class ProjectDashboard(BaseModel):
    project: ProjectOut
    groups: list[GroupCard]


@router.get("/projects/{project_id}/dashboard", response_model=ProjectDashboard)
def project_dashboard(project_id: int, teacher: TeacherUser, db: DbSession):
    project = owned_project(db, project_id, teacher)
    cards = []
    for g in db.scalars(select(Group).where(Group.project_id == project.id).order_by(Group.id)):
        member_count = db.scalar(select(func.count()).select_from(GroupMember).where(GroupMember.group_id == g.id))
        cards.append(GroupCard(group_id=g.id, name=g.name, member_count=member_count or 0, **group_stats(db, g)))
    return ProjectDashboard(project=project_out(db, project), groups=cards)
