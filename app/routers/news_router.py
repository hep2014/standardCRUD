from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.db.db import SessionLocal
from app.models.news import News
from app.models.user import User
from app.auth.deps import get_current_user, require_verified_author, require_owner_news
from app.cache.redis_cache import cache_get, cache_set, cache_delete

router = APIRouter(prefix="/api/news", tags=["News"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def news_to_dict(n: News) -> dict:
    return {
        "id": n.id,
        "title": n.title,
        "content": n.content,
        "published_at": n.published_at.isoformat(),
        "author_id": n.author_id,
        "cover_url": n.cover_url,
    }

@router.get("/list", dependencies=[Depends(get_current_user)])
def list_news(db: Session = Depends(get_db)):
    items = db.query(News).order_by(News.published_at.desc(), News.id.desc()).all()
    return [news_to_dict(n) for n in items]

@router.get("/{news_id}", dependencies=[Depends(get_current_user)])
def get_news(news_id: int, db: Session = Depends(get_db)):
    cache_key = f"news:{news_id}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    n = db.get(News, news_id)
    if not n:
        raise HTTPException(404, "News not found")
    result = news_to_dict(n)

    cache_set(cache_key, result, ttl=300)  # 5 минут
    return result

@router.post("/create", dependencies=[Depends(require_verified_author)])
def create_news(
    title: str = Body(...),
    content: dict = Body(...),
    author_id: int = Body(...),
    cover_url: str | None = Body(None),
    db: Session = Depends(get_db),
):
    author = db.get(User, author_id)
    if not author:
        raise HTTPException(404, "Author not found")
    if not author.is_verified_author:
        raise HTTPException(403, "Only verified authors can create news")
    n = News(title=title, content=content, author_id=author_id, cover_url=cover_url)
    db.add(n)
    db.commit()
    db.refresh(n)
    cache_set(f"news:{n.id}", news_to_dict(n), ttl=300)
    return news_to_dict(n)


@router.put("/{news_id}/update", dependencies=[Depends(require_owner_news)])
def update_news(
    news_id: int,
    title: str = Body(...),
    content: dict = Body(...),
    cover_url: str | None = Body(None),
    db: Session = Depends(get_db),
):
    n = db.get(News, news_id)
    if not n:
        raise HTTPException(404, "News not found")
    n.title = title
    n.content = content
    n.cover_url = cover_url
    db.commit()
    db.refresh(n)
    cache_delete(f"news:{news_id}")
    return news_to_dict(n)

@router.delete("/{news_id}/delete", status_code=204, dependencies=[Depends(require_owner_news)])
def delete_news(news_id: int, db: Session = Depends(get_db)):
    n = db.get(News, news_id)
    if not n:
        raise HTTPException(404, "News not found")
    db.delete(n)
    db.commit()
    cache_delete(f"news:{news_id}")
    return None
