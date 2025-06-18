from fastapi import APIRouter
# from app.routers import auth, home, chat, knowledge, document_upload_new  # 注释掉auth导入
from app.routers import home, chat, knowledge, document_upload_new

router = APIRouter()

# router.include_router(auth.router)  # 注释掉auth路由
router.include_router(home.router)
router.include_router(chat.router)
router.include_router(knowledge.router)
router.include_router(document_upload_new.router)