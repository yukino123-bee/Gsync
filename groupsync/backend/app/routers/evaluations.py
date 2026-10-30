from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.deps import CurrentUser, DbSession, TeacherUser
from app.models import ActivityLog, GroupMember, Milestone, MilestoneStatus, PeerEvaluation, Task, TaskStatus
from app.schemas.common import UserBrief
from app.schemas.workspace import (
    EvaluationRatingOut,
    EvaluationStatus,
    EvaluationSubmit,
    EvaluationSummary,
    MemberEvaluationSummary,
    MilestoneOut,
)
from app.services.access import authorize_group, require_member
from app.services.progress import final_milestone

router = APIRouter(tags=["evaluations"])


def _members(db, group_id: int):
    return [gm.user for gm in db.scalars(select(GroupMember).where(GroupMember.group_id == group_id).order_by(GroupMember.id))]


def _final(db, group_id: int) -> Milestone | None:
    return final_milestone(list(db.scalars(select(Milestone).where(Milestone.group_id == group_id))))


def _is_open(final: Milestone | None) -> bool:
    return final is not None and final.status != MilestoneStatus.pending


@router.get("/groups/{group_id}/evaluations/status", response_model=EvaluationStatus)
def evaluation_status(group_id: int, user: CurrentUser, db: DbSession):
    """What a student needs to render the form. Never exposes anyone's ratings."""
    require_member(db, group_id, user)
    final = _final(db, group_id)
    submitted = db.scalar(
        select(func.count()).select_from(PeerEvaluation).where(
            PeerEvaluation.group_id == group_id, PeerEvaluation.evaluator_id == user.id
        )
    )
    return EvaluationStatus(
        is_open=_is_open(final),
        has_submitted=bool(submitted),
        final_milestone=MilestoneOut.model_validate(final) if final else None,
        members_to_rate=[UserBrief.model_validate(m) for m in _members(db, group_id) if m.id != user.id],
    )


@router.post("/groups/{group_id}/evaluations", status_code=status.HTTP_201_CREATED)
def submit_evaluations(group_id: int, body: EvaluationSubmit, user: CurrentUser, db: DbSession):
    require_member(db, group_id, user)
    if not _is_open(_final(db, group_id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Peer evaluation opens once the final milestone is submitted")
    already = db.scalar(
        select(func.count()).select_from(PeerEvaluation).where(
            PeerEvaluation.group_id == group_id, PeerEvaluation.evaluator_id == user.id
        )
    )
    if already:
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already submitted your evaluation")

    expected = {m.id for m in _members(db, group_id)} - {user.id}
    given = [e.evaluatee_id for e in body.evaluations]
    if len(given) != len(set(given)) or set(given) != expected:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Rate every other group member exactly once (not yourself)")
    for e in body.evaluations:
        comment = (e.comment or "").strip() or None
        db.add(PeerEvaluation(group_id=group_id, evaluator_id=user.id, evaluatee_id=e.evaluatee_id, rating=e.rating, comment=comment))
    # Deliberately not written to the activity log: ratings must stay private
    db.commit()
    return {"detail": "Evaluation submitted"}


@router.get("/groups/{group_id}/evaluations/summary", response_model=EvaluationSummary)
def evaluation_summary(group_id: int, teacher: TeacherUser, db: DbSession):
    authorize_group(db, group_id, teacher)  # owning teacher only (students fail the role check)
    members = _members(db, group_id)
    evals = list(db.scalars(select(PeerEvaluation).where(PeerEvaluation.group_id == group_id).order_by(PeerEvaluation.id)))
    by_id = {m.id: m for m in members}
    out = []
    for m in members:
        received = [e for e in evals if e.evaluatee_id == m.id and e.evaluator_id in by_id]
        out.append(
            MemberEvaluationSummary(
                user=UserBrief.model_validate(m),
                average_rating=round(sum(e.rating for e in received) / len(received), 2) if received else None,
                rating_count=len(received),
                ratings=[
                    EvaluationRatingOut(evaluator=UserBrief.model_validate(by_id[e.evaluator_id]), rating=e.rating, comment=e.comment)
                    for e in received
                ],
                tasks_completed=db.scalar(
                    select(func.count()).select_from(Task).where(
                        Task.group_id == group_id, Task.assignee_id == m.id, Task.status == TaskStatus.done
                    )
                ) or 0,
                activity_count=db.scalar(
                    select(func.count()).select_from(ActivityLog).where(
                        ActivityLog.group_id == group_id, ActivityLog.user_id == m.id
                    )
                ) or 0,
            )
        )
    return EvaluationSummary(
        group_id=group_id,
        member_count=len(members),
        submitted_count=len({e.evaluator_id for e in evals}),
        members=out,
    )
