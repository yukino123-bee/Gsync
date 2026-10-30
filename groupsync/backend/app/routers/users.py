from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_, select

from app.deps import AdminUser, DbSession, TeacherUser
from app.models import Role, User
from app.schemas.auth import UserOut
from app.schemas.common import UserBrief

router = APIRouter(tags=["users"])


@router.get("/users/students", response_model=list[UserBrief])
def search_students(
    teacher: TeacherUser, db: DbSession, q: str = Query("", max_length=100), limit: int = Query(30, ge=1, le=100)
):
    """Lets a teacher find students to add to groups."""
    stmt = select(User).where(User.role == Role.student)
    if q.strip():
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(User.name.ilike(like), User.email.ilike(like)))
    return list(db.scalars(stmt.order_by(User.name).limit(limit)))


@router.get("/admin/users", response_model=list[UserOut])
def admin_list_users(admin: AdminUser, db: DbSession):
    return list(db.scalars(select(User).order_by(User.id)))


class RoleUpdate(BaseModel):
    role: Role


@router.patch("/admin/users/{user_id}/role", response_model=UserOut)
def admin_set_role(user_id: int, body: RoleUpdate, admin: AdminUser, db: DbSession):
    if user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot change your own role")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.role = body.role
    db.commit()
    return user
