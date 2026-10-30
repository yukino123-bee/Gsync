from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import Task, TaskStatus, User
from app.schemas.workspace import TaskCreate, TaskOut, TaskStatusUpdate, TaskUpdate
from app.services.access import authorize_group, is_member, require_member
from app.services.activity import log_activity
from app.services.timeutil import utcnow

router = APIRouter(tags=["tasks"])


def _check_assignee(db, group_id: int, assignee_id: int | None) -> None:
    if assignee_id is not None and not is_member(db, group_id, assignee_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Assignee must be a member of the group")


def _get_task(db, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return task


def _apply_status(db, task: Task, new_status: TaskStatus, user: User) -> None:
    if new_status == task.status:
        return
    old = task.status
    task.status = new_status
    task.completed_at = utcnow() if new_status == TaskStatus.done else None
    if new_status == TaskStatus.done:
        log_activity(db, task.group_id, user.id, "task_completed", f"{user.name} completed task '{task.title}'", task.id)
    else:
        log_activity(
            db, task.group_id, user.id, "task_status_changed",
            f"{user.name} moved '{task.title}' from {old.value} to {new_status.value}", task.id,
        )


@router.post("/groups/{group_id}/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(group_id: int, body: TaskCreate, user: CurrentUser, db: DbSession):
    require_member(db, group_id, user)
    _check_assignee(db, group_id, body.assignee_id)
    task = Task(
        group_id=group_id,
        title=body.title.strip(),
        description=body.description,
        assignee_id=body.assignee_id,
        due_date=body.due_date,
        status=body.status,
        created_by=user.id,
        completed_at=utcnow() if body.status == TaskStatus.done else None,
    )
    db.add(task)
    db.flush()
    log_activity(db, group_id, user.id, "task_created", f"{user.name} created task '{task.title}'", task.id)
    db.commit()
    return task


@router.get("/groups/{group_id}/tasks", response_model=list[TaskOut])
def list_tasks(
    group_id: int,
    user: CurrentUser,
    db: DbSession,
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    assignee_id: int | None = None,
):
    authorize_group(db, group_id, user)
    stmt = select(Task).where(Task.group_id == group_id)
    if status_filter:
        stmt = stmt.where(Task.status == status_filter)
    if assignee_id:
        stmt = stmt.where(Task.assignee_id == assignee_id)
    return list(db.scalars(stmt.order_by(Task.created_at, Task.id)))


@router.put("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, body: TaskUpdate, user: CurrentUser, db: DbSession):
    task = _get_task(db, task_id)
    require_member(db, task.group_id, user)
    fields = body.model_fields_set
    if "assignee_id" in fields:
        _check_assignee(db, task.group_id, body.assignee_id)
        task.assignee_id = body.assignee_id
    if "due_date" in fields:
        task.due_date = body.due_date
    if body.title is not None:
        task.title = body.title.strip()
    if body.description is not None:
        task.description = body.description
    log_activity(db, task.group_id, user.id, "task_updated", f"{user.name} updated task '{task.title}'", task.id)
    db.commit()
    return task


@router.patch("/tasks/{task_id}/status", response_model=TaskOut)
def change_task_status(task_id: int, body: TaskStatusUpdate, user: CurrentUser, db: DbSession):
    task = _get_task(db, task_id)
    require_member(db, task.group_id, user)
    _apply_status(db, task, body.status, user)
    db.commit()
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, user: CurrentUser, db: DbSession):
    task = _get_task(db, task_id)
    require_member(db, task.group_id, user)
    log_activity(db, task.group_id, user.id, "task_deleted", f"{user.name} deleted task '{task.title}'")
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
