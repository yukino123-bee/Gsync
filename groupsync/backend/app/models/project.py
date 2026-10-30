import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.user import User


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    rubric: Mapped[str] = mapped_column(Text, default="")
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # No delete cascade: groups belong to their students, so deleting a project just detaches them
    groups: Mapped[list["Group"]] = relationship(back_populates="project")


class GroupStatus(str, enum.Enum):
    active = "active"
    archived = "archived"


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Optional assignment a teacher can attach to the group
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    # Shareable join code, format GS-XXXXXX
    group_code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", name="fk_groups_created_by"), nullable=True
    )
    status: Mapped[GroupStatus] = mapped_column(
        Enum(GroupStatus, native_enum=False, length=20), default=GroupStatus.active, server_default="active"
    )
    join_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped[Project | None] = relationship(back_populates="groups")
    members: Mapped[list["GroupMember"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    group: Mapped[Group] = relationship(back_populates="members")
    user: Mapped[User] = relationship()


class TeacherGroup(Base):
    """A group on a teacher's dashboard. group_id is unique: a group has one teacher at a time."""

    __tablename__ = "teacher_groups"
    __table_args__ = (UniqueConstraint("teacher_id", "group_id", name="uq_teacher_group"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), unique=True, index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    group: Mapped[Group] = relationship()


class GroupHealth(Base):
    """Last computed coordination score per group (refreshed by the hourly job and the coordination endpoint)."""

    __tablename__ = "group_health"

    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    coordination_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Extra to the brief: on_track / needs_attention / inactive at calculation time
    status: Mapped[str] = mapped_column(String(20), default="on_track")
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
