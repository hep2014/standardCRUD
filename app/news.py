from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from app.models import Base


class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)  # JSONB под Postgres
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    cover_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author: Mapped["User"] = relationship(back_populates="news")

    comments: Mapped[list["Comment"]] = relationship(
        back_populates="news",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
