from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession, TeacherUser
from app.models import Comment, Milestone, MilestoneStatus, User
from app.schemas.workspace import CommentCreate, CommentOut, MilestoneCreate, MilestoneOut, MilestoneUpdate
from app.services.access import authorize_group, require_member
from app.services.activity import log_activity

router = APIRouter(tags=["milestones"])


def _get_milestone(db, milestone_id: int) -> Milestone:
    m = db.get(Milestone, milestone_id)
    if m is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Milestone not found")
    return m


def _comment_out(db, c: Comment) -> CommentOut:
    teacher = db.get(User, c.teacher_id)
    return CommentOut(
        id=c.id, milestone_id=c.milestone_id, teacher_id=c.teacher_id,
        teacher_name=teacher.name if teacher else "Teacher", content=c.content, created_at=c.created_at,
    )


@router.post("/groups/{group_id}/milestones", response_model=MilestoneOut, status_code=status.HTTP_201_CREATED)
def create_milestone(group_id: int, body: MilestoneCreate, user: CurrentUser, db: DbSession):
    require_member(db, group_id, user)
    m = Milestone(group_id=group_id, title=body.title.strip(), due_date=body.due_date)
    db.add(m)
    db.flush()
    log_activity(db, group_id, user.id, "milestone_created", f"{user.name} added milestone '{m.title}'", m.id)
    db.commit()
    return m


@router.get("/groups/{group_id}/milestones", response_model=list[MilestoneOut])
def list_milestones(group_id: int, user: CurrentUser, db: DbSession):
    authorize_group(db, group_id, user)
    ms = list(db.scalars(select(Milestone).where(Milestone.group_id == group_id)))
    ms.sort(key=lambda m: (m.due_date is None, m.due_date.replace(tzinfo=None) if m.due_date else 0, m.id))
    return ms


@router.put("/milestones/{milestone_id}", response_model=MilestoneOut)
def update_milestone(milestone_id: int, body: MilestoneUpdate, user: CurrentUser, db: DbSession):
    m = _get_milestone(db, milestone_id)
    require_member(db, m.group_id, user)
    if "due_date" in body.model_fields_set:
        m.due_date = body.due_date
    if body.title is not None:
        m.title = body.title.strip()
    action, text = "milestone_updated", f"{user.name} updated milestone '{m.title}'"
    if body.status is not None and body.status != m.status.value:
        m.status = MilestoneStatus(body.status)
        if m.status == MilestoneStatus.submitted:
            action, text = "milestone_submitted", f"{user.name} submitted milestone '{m.title}'"
    log_activity(db, m.group_id, user.id, action, text, m.id)
    db.commit()
    return m


@router.post("/milestones/{milestone_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(milestone_id: int, body: CommentCreate, teacher: TeacherUser, db: DbSession):
    m = _get_milestone(db, milestone_id)
    authorize_group(db, m.group_id, teacher)  # must be the owning teacher
    c = Comment(milestone_id=m.id, teacher_id=teacher.id, content=body.content.strip())
    db.add(c)
    if m.status == MilestoneStatus.submitted:
        m.status = MilestoneStatus.reviewed
    db.commit()
    return _comment_out(db, c)


@router.get("/milestones/{milestone_id}/comments", response_model=list[CommentOut])
def list_comments(milestone_id: int, user: CurrentUser, db: DbSession):
    m = _get_milestone(db, milestone_id)
    authorize_group(db, m.group_id, user)
    comments = db.scalars(select(Comment).where(Comment.milestone_id == m.id).order_by(Comment.created_at, Comment.id))
    return [_comment_out(db, c) for c in comments]
