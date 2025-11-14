"""auth_core

Revision ID: 78b8a6bbf783
Revises: 12bc18ee9ca0
Create Date: 2025-10-16 18:54:20.866384

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78b8a6bbf783'
down_revision: Union[str, Sequence[str], None] = '12bc18ee9ca0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=512), nullable=True))
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("refresh_hash", sa.String(length=512), nullable=False),  # храним ХЭШ refresh-токена
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
    )

def downgrade() -> None:
    op.drop_table("refresh_sessions")
    op.drop_column("users", "is_admin")
    op.drop_column("users", "password_hash")
