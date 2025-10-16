from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.db.db import SessionLocal
from app.models.user import User

router = APIRouter(prefix="/api/users", tags=["Users"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def user_to_dict(u: User) -> dict:
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "registered_at": u.registered_at.isoformat(),
        "is_verified_author": u.is_verified_author,
        "avatar_url": u.avatar_url,
    }

@router.get("/list")
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id).all()
    return [user_to_dict(u) for u in users]

@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    return user_to_dict(u)

@router.post("/create")
def create_user(
    name: str = Body(...),
    email: str = Body(...),
    is_verified_author: bool = Body(False),
    avatar_url: str | None = Body(None),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "Email already exists")
    u = User(name=name, email=email, is_verified_author=is_verified_author, avatar_url=avatar_url)
    db.add(u)
    db.commit()
    db.refresh(u)
    return user_to_dict(u)

@router.put("/{user_id}/update")
def update_user(
    user_id: int,
    name: str = Body(...),
    is_verified_author: bool = Body(...),
    avatar_url: str | None = Body(None),
    db: Session = Depends(get_db),
):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    u.name = name
    u.is_verified_author = is_verified_author
    u.avatar_url = avatar_url
    db.commit()
    db.refresh(u)
    return user_to_dict(u)

@router.delete("/{user_id}/delete", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    db.delete(u)
    db.commit()
    return None