from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.db.db import SessionLocal
from app.models.comment import Comment
from app.models.news import News
from app.models.user import User
from app.auth.deps import (
    get_current_user,
    resolve_news,
    resolve_comment,
    require_owner_comment,
)

router = APIRouter(prefix="/api", tags=["Comments"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def comment_to_dict(c: Comment) -> dict:
    return {
        "id": c.id,
        "text": c.text,
        "published_at": c.published_at.isoformat(),
        "news_id": c.news_id,
        "author_id": c.author_id,
    }

@router.get("/news/{news_id}/comments", dependencies=[Depends(get_current_user)])
def list_comments_for_news(news_id: int, db: Session = Depends(get_db)):
    if not db.get(News, news_id):
        raise HTTPException(404, "News not found")
    comments = db.query(Comment).filter(Comment.news_id == news_id).order_by(Comment.published_at).all()
    return [comment_to_dict(c) for c in comments]

@router.get("/comments/{comment_id}", dependencies=[Depends(get_current_user)])
def get_comment(comment_id: int, db: Session = Depends(get_db)):
    c = db.get(Comment, comment_id)
    if not c:
        raise HTTPException(404, "Comment not found")
    return comment_to_dict(c)

@router.post("/news/{news_id}/comments/create", dependencies=[Depends(get_current_user)])
def create_comment_for_news(
    news_id: int,
    text: str = Body(...),
    author_id: int = Body(...),
    db: Session = Depends(get_db),
):
    if not db.get(News, news_id):
        raise HTTPException(404, "News not found")
    if not db.get(User, author_id):
        raise HTTPException(404, "User not found")
    c = Comment(text=text, news_id=news_id, author_id=author_id)
    db.add(c)
    db.commit()
    db.refresh(c)
    return comment_to_dict(c)

@router.put("/comments/{comment_id}/update", dependencies=[Depends(require_owner_comment)])
def update_comment(comment_id: int, text: str = Body(...), db: Session = Depends(get_db)):
    c = db.get(Comment, comment_id)
    if not c:
        raise HTTPException(404, "Comment not found")
    c.text = text
    db.commit()
    db.refresh(c)
    return comment_to_dict(c)

@router.delete("/comments/{comment_id}/delete", status_code=204, dependencies=[Depends(require_owner_comment)])
def delete_comment(comment_id: int, db: Session = Depends(get_db)):
    c = db.get(Comment, comment_id)
    if not c:
        raise HTTPException(404, "Comment not found")
    db.delete(c)
    db.commit()
    return None