from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class FormSizeMiddleware(BaseHTTPMiddleware):
    """
    中间件用于设置表单数据的大小限制
    解决Starlette默认max_part_size=1MB的限制
    """
    
    def __init__(self, app, max_part_size: int = 1024 * 1024 * 1024):  # 默认1GB
        super().__init__(app)
        self.max_part_size = max_part_size
    
    async def dispatch(self, request: Request, call_next):
        # 如果是包含文件的POST请求，预先调用form()方法设置大小限制
        if (
            request.method == "POST" 
            and request.headers.get("content-type", "").startswith("multipart/form-data")
        ):
            try:
                # 预先解析表单数据，设置自定义的max_part_size
                await request.form(
                    max_files=1000,
                    max_fields=1000, 
                    max_part_size=self.max_part_size
                )
            except Exception:
                # 如果解析失败，让后续处理器处理错误
                pass
        
        response = await call_next(request)
        return response