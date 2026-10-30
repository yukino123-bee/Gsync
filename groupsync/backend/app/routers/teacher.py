from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.deps import DbSession, TeacherUser
from app.models import Group, GroupMember, GroupStatus, Project, TeacherGroup
from app.routers.groups import find_group_by_code
from app.routers.projects import _students_in_project
from app.schemas.classroom import (
    GroupCodeRequest, OverviewCounts, ProjectAttach, TeacherGroupCard, TeacherGroupUpdate, TeacherOverview,
)
from app.services.access import authorize_group, owned_project, teacher_link
from app.services.activity import log_activity
from app.services.coordination import compute_coordination, rank_key

router = APIRouter(prefix="/teacher", tags=["teacher"])

IncludeArchived = Annotated[bool, Query(description="Also list archived groups")]


def _card(db, group: Group, link: TeacherGroup) -> tuple[TeacherGroupCard, dict]:
    result = compute_coordination(db, group)
    top = result["warnings"][0]["message"] if result["warnings"] else None
    card = TeacherGroupCard(
        group_id=group.id,
        name=group.name,
        group_code=group.group_code,
        group_status=group.status.value,
        member_count=len(group.members),
        percent_done=result["percent_done"],
        health=result["status"],
        coordination_score=result["score"],
        overdue_tasks=result["task_health"]["overdue"],
        last_activity_at=result["last_activity_at"],
        warning_count=len(result["warnings"]),
        top_warning=top,
        project_title=group.project.title if group.project else None,
        added_at=link.added_at,
    )
    return card, result


def _links(db, teacher, include_archived: bool) -> list[tuple[Group, TeacherGroup]]:
    stmt = (
        select(Group, TeacherGroup)
        .join(TeacherGroup, TeacherGroup.group_id == Group.id)
        .where(TeacherGroup.teacher_id == teacher.id)
        .options(selectinload(Group.members).selectinload(GroupMember.user), selectinload(Group.project))
        .order_by(TeacherGroup.added_at.desc(), Group.id.desc())
    )
    if not include_archived:
        stmt = stmt.where(Group.status == GroupStatus.active)
    return [(g, link) for g, link in db.execute(stmt).all()]


@router.post("/groups", response_model=TeacherGroupCard, status_code=status.HTTP_201_CREATED)
def add_group(body: GroupCodeRequest, teacher: TeacherUser, db: DbSession):
    """Add a group to the dashboard with its Group ID."""
    group = find_group_by_code(db, body.group_code)
    link = teacher_link(db, group.id)
    if link is not None and link.teacher_id == teacher.id:
        raise HTTPException(status.HTTP_409_CONFLICT, f"{group.name} is already on your dashboard.")
    if link is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This group is already linked to another teacher.")
    if group.status == GroupStatus.archived:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This group is archived and can't be added.")
    if not group.join_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This Group ID has been disabled. Ask the group for a new one.")
    link = TeacherGroup(teacher_id=teacher.id, group_id=group.id)
    db.add(link)
    log_activity(db, group.id, teacher.id, "teacher_added", f"{teacher.name} added the group as its teacher", teacher.id)
    db.commit()
    db.refresh(link)
    return _card(db, group, link)[0]


@router.get("/groups", response_model=list[TeacherGroupCard])
def list_groups(teacher: TeacherUser, db: DbSession, include_archived: IncludeArchived = False):
    return [_card(db, g, link)[0] for g, link in _links(db, teacher, include_archived)]


@router.patch("/groups/{group_id}", response_model=TeacherGroupCard)
def update_group(group_id: int, body: TeacherGroupUpdate, teacher: TeacherUser, db: DbSession):
    """Rename or archive/unarchive a group on your dashboard. The new name is shown to the students too."""
    group = authorize_group(db, group_id, teacher)
    if body.name is not None:
        new_name = body.name.strip()
        if not new_name:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "The name can't be empty")
        if new_name != group.name:
            log_activity(db, group.id, teacher.id, "group_renamed", f"{teacher.name} renamed the group to '{new_name}'", group.id)
            group.name = new_name
    if body.archived is not None:
        group.status = GroupStatus.archived if body.archived else GroupStatus.active
        word = "archived" if body.archived else "restored"
        log_activity(db, group.id, teacher.id, f"group_{word}", f"{teacher.name} {word} the group", group.id)
    db.commit()
    return _card(db, group, teacher_link(db, group.id))[0]


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_group(group_id: int, teacher: TeacherUser, db: DbSession):
    """Take the group off your dashboard. The group and its work are untouched; it can be added again with its ID."""
    authorize_group(db, group_id, teacher)
    db.delete(teacher_link(db, group_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/groups/{group_id}/project", response_model=TeacherGroupCard)
def attach_project(group_id: int, body: ProjectAttach, teacher: TeacherUser, db: DbSession):
    """Attach (or detach, with null) one of your projects as the group's assignment."""
    group = authorize_group(db, group_id, teacher)
    if body.project_id is None:
        group.project_id = None
    else:
        project = owned_project(db, body.project_id, teacher)
        member_ids = {m.user_id for m in group.members}
        clash = member_ids & _students_in_project(db, project.id)
        # Members of this group are not "taken" by it; only students already in a different group of the project
        other = [
            uid for uid in clash
            if db.scalar(
                select(GroupMember.id).join(Group).where(
                    Group.project_id == project.id, Group.id != group.id, GroupMember.user_id == uid
                )
            )
        ]
        if other:
            raise HTTPException(status.HTTP_409_CONFLICT, "A member of this group is already in another group for that project")
        group.project_id = project.id
    db.commit()
    db.refresh(group)
    return _card(db, group, teacher_link(db, group.id))[0]


@router.get("/overview", response_model=TeacherOverview)
def overview(
    teacher: TeacherUser,
    db: DbSession,
    health: Annotated[Literal["on_track", "needs_attention", "inactive"] | None, Query(alias="status")] = None,
    include_archived: IncludeArchived = False,
):
    """Every group on the dashboard ranked by health: needs attention first, then inactive, then on track."""
    scored = [_card(db, g, link) for g, link in _links(db, teacher, include_archived)]
    counts = OverviewCounts(
        total=len(scored),
        needs_attention=sum(1 for c, _ in scored if c.health == "needs_attention"),
        inactive=sum(1 for c, _ in scored if c.health == "inactive"),
        on_track=sum(1 for c, _ in scored if c.health == "on_track"),
    )
    scored.sort(key=lambda pair: (*rank_key(pair[1]), pair[0].name.lower()))
    groups = [c for c, _ in scored if health is None or c.health == health]
    return TeacherOverview(counts=counts, groups=groups)
