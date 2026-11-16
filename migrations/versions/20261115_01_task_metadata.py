"""Create or upgrade the CloudTask schema with task metadata.

Revision ID: 20261115_01
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261115_01"
down_revision = None
branch_labels = None
depends_on = None


def _table_exists(bind, table_name):
    return inspect(bind).has_table(table_name)


def _columns(bind, table_name):
    return {column["name"] for column in inspect(bind).get_columns(table_name)}


def upgrade():
    bind = op.get_bind()

    if not _table_exists(bind, "user"):
        op.create_table(
            "user",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
        )
        op.create_index("ix_user_email", "user", ["email"], unique=False)

    if not _table_exists(bind, "task"):
        op.create_table(
            "task",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("completed", sa.Boolean(), nullable=False),
            sa.Column("priority", sa.String(length=10), nullable=False),
            sa.Column("category", sa.String(length=80), nullable=False),
            sa.Column("due_date", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_task_user_id", "task", ["user_id"], unique=False)
        return

    existing_columns = _columns(bind, "task")
    additions = []
    if "priority" not in existing_columns:
        additions.append(sa.Column("priority", sa.String(length=10), nullable=False, server_default="medium"))
    if "category" not in existing_columns:
        additions.append(sa.Column("category", sa.String(length=80), nullable=False, server_default="Other"))
    if "due_date" not in existing_columns:
        additions.append(sa.Column("due_date", sa.Date(), nullable=True))
    if additions:
        with op.batch_alter_table("task") as batch_op:
            for column in additions:
                batch_op.add_column(column)


def downgrade():
    bind = op.get_bind()
    if not _table_exists(bind, "task"):
        return
    existing_columns = _columns(bind, "task")
    removable = [name for name in ("due_date", "category", "priority") if name in existing_columns]
    if removable:
        with op.batch_alter_table("task") as batch_op:
            for column in removable:
                batch_op.drop_column(column)
