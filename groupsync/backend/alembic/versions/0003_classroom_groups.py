"""classroom-style groups: group codes, teacher links, group health

Revision ID: 0003
Revises: 0002
"""
import secrets
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Same alphabet as app.services.group_code (no 0/O/1/I/L); copied so the migration never changes with the app
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def _code() -> str:
    return "GS-" + "".join(secrets.choice(ALPHABET) for _ in range(6))


def upgrade() -> None:
    with op.batch_alter_table("groups", schema=None) as batch_op:
        batch_op.add_column(sa.Column("group_code", sa.String(length=12), nullable=True))
        batch_op.add_column(sa.Column("created_by", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("status", sa.String(length=20), server_default="active", nullable=False))
        batch_op.add_column(sa.Column("join_enabled", sa.Boolean(), server_default=sa.true(), nullable=False))
        batch_op.alter_column("project_id", existing_type=sa.Integer(), nullable=True)
        batch_op.create_foreign_key("fk_groups_created_by", "users", ["created_by"], ["id"])

    # Existing groups need a code before the column can become NOT NULL + unique
    bind = op.get_bind()
    used: set[str] = set()
    for (group_id,) in bind.execute(sa.text("SELECT id FROM groups")).fetchall():
        code = _code()
        while code in used:
            code = _code()
        used.add(code)
        bind.execute(sa.text("UPDATE groups SET group_code = :c WHERE id = :i"), {"c": code, "i": group_id})

    with op.batch_alter_table("groups", schema=None) as batch_op:
        batch_op.alter_column("group_code", existing_type=sa.String(length=12), nullable=False)
        batch_op.create_index(batch_op.f("ix_groups_group_code"), ["group_code"], unique=True)

    op.create_table(
        "teacher_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("teacher_id", "group_id", name="uq_teacher_group"),
    )
    with op.batch_alter_table("teacher_groups", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_teacher_groups_group_id"), ["group_id"], unique=True)
        batch_op.create_index(batch_op.f("ix_teacher_groups_teacher_id"), ["teacher_id"], unique=False)

    # Groups that teachers created inside their projects stay on those teachers' dashboards
    bind.execute(
        sa.text(
            "INSERT INTO teacher_groups (teacher_id, group_id) "
            "SELECT p.teacher_id, g.id FROM groups g JOIN projects p ON p.id = g.project_id"
        )
    )

    op.create_table(
        "group_health",
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("coordination_score", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("group_id"),
    )


def downgrade() -> None:
    op.drop_table("group_health")
    op.drop_table("teacher_groups")
    with op.batch_alter_table("groups", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_groups_group_code"))
        batch_op.drop_constraint("fk_groups_created_by", type_="foreignkey")
        batch_op.drop_column("join_enabled")
        batch_op.drop_column("status")
        batch_op.drop_column("created_by")
        batch_op.drop_column("group_code")
        # project_id is left nullable: groups created without a project could not satisfy NOT NULL again
