"""add mock data

Revision ID: 12bc18ee9ca0
Revises: ef0a9a6d3f22
Create Date: 2025-10-16 15:57:49.769297

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '12bc18ee9ca0'
down_revision: Union[str, Sequence[str], None] = 'ef0a9a6d3f22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Добавляем пользователей
    conn.execute(sa.text("""
        INSERT INTO users (name, email, registered_at, is_verified_author, avatar_url)
        VALUES
        ('Alice', 'alice@example.com', :now, true, 'https://picsum.photos/100'),
        ('Bob', 'bob@example.com', :now, false, NULL),
        ('Ilya', 'ilya@example.com', :now, true, 'https://picsum.photos/101');
    """), {"now": datetime.utcnow()})

    # Добавляем новости (только verified авторы)
    conn.execute(sa.text("""
        INSERT INTO news (title, content, published_at, author_id, cover_url)
        VALUES
        ('First Post', '{"body": "Hello world"}'::jsonb, :now, 1, 'https://picsum.photos/200'),
        ('Second Post', '{"body": "More content"}'::jsonb, :now, 3, NULL);
    """), {"now": datetime.utcnow()})

    # Добавляем комментарии
    conn.execute(sa.text("""
        INSERT INTO comments (text, published_at, news_id, author_id)
        VALUES
        ('Nice article!', :now, 1, 2),
        ('Subscribed!', :now, 2, 1),
        ('Waiting for more updates.', :now, 1, 3);
    """), {"now": datetime.utcnow()})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM comments;"))
    conn.execute(sa.text("DELETE FROM news;"))
    conn.execute(sa.text("DELETE FROM users;"))
