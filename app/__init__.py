from app.db.db import Base
from app.models.user import User
from app.models.news import News
from app.models.comment import Comment

__all__ = ["Base", "User", "News", "Comment"]