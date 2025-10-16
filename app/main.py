from fastapi import FastAPI
from app.routers.user_router import router as users_router
from app.routers.news_router import router as news_router
from app.routers.comment_router import router as comments_router

app = FastAPI(title="Новости")

app.include_router(users_router)
app.include_router(news_router)
app.include_router(comments_router)