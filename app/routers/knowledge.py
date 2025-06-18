from fastapi import APIRouter, Depends, HTTPException, Request, Body, File, UploadFile, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
import os
from pathlib import Path
import json
import shutil
import datetime
from typing import List, Optional, Dict, Any
import urllib.parse
import mimetypes

# 导入服务层
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.document_metadata_service import DocumentMetadataService
from app.services.file_utils_service import FileUtilsService
from app.services.vector_service import VectorService
from app.services.model_config_service import ModelConfigService
from app.database import get_db
from sqlalchemy.orm import Session

# 创建路由
router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"],
    responses={404: {"description": "Not found"}},
)

# 获取模板目录的绝对路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# 依赖注入服务实例
def get_kb_service() -> KnowledgeBaseService:
    return KnowledgeBaseService()

def get_metadata_service() -> DocumentMetadataService:
    return DocumentMetadataService()

def get_file_utils_service() -> FileUtilsService:
    return FileUtilsService()

def get_vector_service() -> VectorService:
    return VectorService()

@router.get("/knowledge_base", response_class=HTMLResponse)
async def get_knowledge_base(request: Request):
    """
    显示知识库管理页面
    """
    return templates.TemplateResponse("knowledge/knowledge_base.html", {"request": request})

@router.get("/test_api", response_class=HTMLResponse)
async def test_api_page(request: Request):
    """
    API测试页面
    """
    return templates.TemplateResponse("knowledge/test_api.html", {"request": request})

@router.get("/api/knowledge_bases", response_class=JSONResponse)
async def get_knowledge_bases(
    tab: str = "personal", 
    page: int = 1, 
    page_size: int = 10, 
    search: str = "",
    refresh: bool = False,
    kb_service: KnowledgeBaseService = Depends(get_kb_service),
    db: Session = Depends(get_db)
):
    """
    获取知识库列表
    """
    try:
        # 加载知识库
        knowledge_bases = kb_service.load_knowledge_bases()
        
        # 应用搜索过滤
        if search:
            search_lower = search.lower()
            knowledge_bases = [
                kb for kb in knowledge_bases
                if search_lower in kb.get("name", "").lower()
                or search_lower in kb.get("description", "").lower()
            ]
        
        # 为每个知识库添加文档数量和embedding模型名称
        for kb in knowledge_bases:
            kb["document_count"] = kb_service.count_knowledge_base_documents(kb.get("name", ""))
            
            # 获取embedding模型名称
            embedding_model_id = kb.get("embedding_model_id")
            if embedding_model_id:
                try:
                    model_config = ModelConfigService.get_model_config_by_id(db, embedding_model_id)
                    if model_config:
                        kb["embedding_model_name"] = f"{model_config.model_name} ({model_config.provider_name})"
                    else:
                        kb["embedding_model_name"] = "模型配置已删除"
                except Exception as e:
                    kb["embedding_model_name"] = "获取模型信息失败"
            else:
                kb["embedding_model_name"] = kb.get("embedding_model", "未配置")
        
        # 分页处理
        total = len(knowledge_bases)
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        
        paginated_kbs = knowledge_bases[start_index:end_index]
        
        # 修复返回格式，符合前端期望
        return JSONResponse(content={
            "success": True,
            "data": {
                "knowledge_bases": paginated_kbs,
                "total": total
            },
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size
            }
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"获取知识库列表失败: {str(e)}"
            }
        )

@router.post("/api/knowledge_bases", response_class=JSONResponse)
async def create_knowledge_base_new(
    data: dict = Body(...),
    kb_service: KnowledgeBaseService = Depends(get_kb_service)
):
    """
    创建新的知识库
    """
    try:
        name = data.get("name", "").strip()
        description = data.get("description", "").strip()
        embedding_model = data.get("embedding_model", "gte_Qwen2-15B-instruct")
        embedding_model_id = data.get("embedding_model_id")
        
        if not name:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "知识库名称不能为空"
                }
            )
        
        if not embedding_model_id:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "请选择嵌入模型"
                }
            )
        
        # 调用服务层创建知识库
        result = kb_service.create_knowledge_base(name, description, embedding_model, embedding_model_id)
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            return JSONResponse(
                status_code=400,
                content=result
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"创建知识库失败: {str(e)}"
            }
        )

@router.delete("/api/knowledge_bases/{kb_id}", response_class=JSONResponse)
async def delete_knowledge_base_by_id(
    kb_id: int,
    kb_service: KnowledgeBaseService = Depends(get_kb_service)
):
    """
    删除知识库
    """
    try:
        result = kb_service.delete_knowledge_base(kb_id)
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            return JSONResponse(
                status_code=404 if "不存在" in result["message"] else 500,
                content=result
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"删除知识库失败: {str(e)}"
            }
        )

@router.get("/api/knowledge_bases/{kb_id}", response_class=JSONResponse)
async def get_knowledge_base_by_id(
    kb_id: int,
    kb_service: KnowledgeBaseService = Depends(get_kb_service)
):
    """
    根据ID获取知识库信息
    """
    try:
        kb = kb_service.get_knowledge_base_by_id(kb_id)
        
        if kb:
            return JSONResponse(content={
                "success": True,
                "data": kb
            })
        else:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": f"知识库 (ID: {kb_id}) 不存在"
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"获取知识库信息失败: {str(e)}"
            }
        )

@router.put("/api/knowledge_bases/{kb_id}", response_class=JSONResponse)
async def update_knowledge_base(
    kb_id: int, 
    data: dict = Body(...),
    kb_service: KnowledgeBaseService = Depends(get_kb_service)
):
    """
    更新知识库信息
    """
    try:
        name = data.get("name", "").strip()
        description = data.get("description", "").strip()
        
        if not name:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "知识库名称不能为空"
                }
            )
        
        result = kb_service.update_knowledge_base(kb_id, name, description)
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            return JSONResponse(
                status_code=404 if "不存在" in result["message"] else 400,
                content=result
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"更新知识库失败: {str(e)}"
            }
        )

@router.post("/api/documents/upload", response_class=JSONResponse)
async def upload_documents(
    kb_name: str = Form(...), 
    files: List[UploadFile] = File(...),
    metadata_service: DocumentMetadataService = Depends(get_metadata_service),
    file_utils_service: FileUtilsService = Depends(get_file_utils_service)
):
    """
    上传文档到知识库
    """
    try:
        if not kb_name.strip():
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "知识库名称不能为空"
                }
            )
        
        if not files:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "请选择要上传的文件"
                }
            )
        
        # 处理文件上传逻辑
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        KNOWLEDGE_BASE_DIR = BASE_DIR / "data" / "knowledge_base"
        
        # 确保知识库目录存在
        kb_dir = KNOWLEDGE_BASE_DIR / kb_name
        content_dir = kb_dir / "content"
        os.makedirs(content_dir, exist_ok=True)
        
        uploaded_files = []
        failed_files = []
        
        # 加载现有元数据
        metadata = metadata_service.load_documents_metadata(kb_name)
        
        for file in files:
            try:
                if not file.filename:
                    failed_files.append({"filename": "未知文件", "error": "文件名为空"})
                    continue
                
                # 验证文件名
                validation = file_utils_service.validate_filename(file.filename)
                if not validation["valid"]:
                    failed_files.append({"filename": file.filename, "error": validation["message"]})
                    continue
                
                # 检查文件类型
                if not file_utils_service.is_supported_file_type(file.filename):
                    failed_files.append({"filename": file.filename, "error": "不支持的文件类型"})
                    continue
                
                # 读取文件内容
                file_content = await file.read()
                
                # 检查文件大小
                if len(file_content) > 1024 * 1024 * 1024:  # 1GB
                    failed_files.append({"filename": file.filename, "error": "文件大小超过1GB"})
                    continue
                
                # 保存文件
                file_path = content_dir / file.filename
                
                # 如果文件已存在，生成新名称
                if file_path.exists():
                    base_name, ext = os.path.splitext(file.filename)
                    counter = 1
                    while file_path.exists():
                        new_filename = f"{base_name}_{counter}{ext}"
                        file_path = content_dir / new_filename
                        counter += 1
                    file.filename = file_path.name
                
                with open(file_path, "wb") as f:
                    f.write(file_content)
                
                # 生成文档ID
                doc_id = f"doc_{int(datetime.datetime.now().timestamp() * 1000)}"
                
                # 创建文档元数据
                doc_metadata = {
                    "filename": file.filename,
                    "file_size": len(file_content),
                    "size_str": file_utils_service.format_file_size(len(file_content)),
                    "file_type": file_utils_service.get_file_extension(file.filename),
                    "file_type_text": file_utils_service.get_file_type(file.filename),
                    "upload_time": datetime.datetime.now().isoformat(),
                    "has_vector": False,
                    "vector_status": "waiting",
                    "problem_status": "正常"
                }
                
                # 添加到元数据
                metadata["documents"][doc_id] = doc_metadata
                
                uploaded_files.append({
                    "id": doc_id,
                    "filename": file.filename,
                    "size": doc_metadata["size_str"]
                })
                
            except Exception as e:
                failed_files.append({"filename": file.filename, "error": str(e)})
        
        # 保存元数据
        metadata_service.save_documents_metadata(kb_name, metadata)
        
        return JSONResponse(content={
            "success": True,
            "message": f"成功上传 {len(uploaded_files)} 个文件",
            "data": {
                "uploaded": uploaded_files,
                "failed": failed_files,
                "total_uploaded": len(uploaded_files),
                "total_failed": len(failed_files)
            }
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"上传文件失败: {str(e)}"
            }
        )

@router.get("/document_viewer", response_class=HTMLResponse)
async def get_document_viewer(request: Request):
    """
    显示文档查看器页面
    """
    return templates.TemplateResponse("knowledge/document_viewer.html", {"request": request})

@router.get("/api/documents", response_class=JSONResponse)
async def get_documents(
    kb_name: str, 
    page: int = 1, 
    limit: int = 10, 
    search: Optional[str] = None,
    metadata_service: DocumentMetadataService = Depends(get_metadata_service)
):
    """
    获取文档列表
    """
    try:
        if not kb_name.strip():
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "知识库名称不能为空"
                }
            )
        
        result = metadata_service.list_documents(kb_name, page, limit, search)
        return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"获取文档列表失败: {str(e)}"
            }
        )

@router.get("/api/documents/{doc_id}/download", response_class=FileResponse)
async def download_document(
    kb_name: str, 
    doc_id: str,
    metadata_service: DocumentMetadataService = Depends(get_metadata_service)
):
    """
    下载文档
    """
    try:
        # 获取文档元数据
        doc_metadata = metadata_service.get_document_metadata(kb_name, doc_id)
        
        if not doc_metadata:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        filename = doc_metadata.get("filename")
        if not filename:
            raise HTTPException(status_code=404, detail="文档文件名缺失")
        
        # 构建文件路径
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        KNOWLEDGE_BASE_DIR = BASE_DIR / "data" / "knowledge_base"
        file_path = KNOWLEDGE_BASE_DIR / kb_name / "content" / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文档文件不存在")
        
        # 获取MIME类型
        mime_type = FileUtilsService.get_mime_type(filename)
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type=mime_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载文档失败: {str(e)}")

@router.delete("/api/documents/{doc_id}", response_class=JSONResponse)
async def delete_document(
    kb_name: str, 
    doc_id: str,
    metadata_service: DocumentMetadataService = Depends(get_metadata_service),
    vector_service: VectorService = Depends(get_vector_service)
):
    """
    删除文档
    """
    try:
        # 获取文档元数据
        doc_metadata = metadata_service.get_document_metadata(kb_name, doc_id)
        
        if not doc_metadata:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "文档不存在"
                }
            )
        
        filename = doc_metadata.get("filename")
        
        # 删除物理文件
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        KNOWLEDGE_BASE_DIR = BASE_DIR / "data" / "knowledge_base"
        file_path = KNOWLEDGE_BASE_DIR / kb_name / "content" / filename
        
        if file_path.exists():
            file_path.unlink()
        
        # 删除向量数据
        vector_service.delete_document_vectors(kb_name, doc_id)
        
        # 删除元数据
        if metadata_service.delete_document_metadata(kb_name, doc_id):
            return JSONResponse(content={
                "success": True,
                "message": f"文档 '{filename}' 删除成功"
            })
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "删除文档元数据失败"
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"删除文档失败: {str(e)}"
            }
        )

@router.get("/api/check_vector_store", response_class=JSONResponse)
async def check_vector_store(
    kb_name: str, 
    doc_id: str,
    vector_service: VectorService = Depends(get_vector_service)
):
    """
    检查文档的向量库状态
    """
    try:
        exists = vector_service.check_vector_store_exists(kb_name, doc_id)
        
        return JSONResponse(content={
            "success": True,
            "exists": exists
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"检查向量库状态失败: {str(e)}"
            }
        )

@router.put("/api/documents/{doc_id}/metadata", response_class=JSONResponse)
async def update_document_metadata_api(
    doc_id: str,
    kb_name: str,
    has_vector: bool = Body(..., embed=True),
    vector_service: VectorService = Depends(get_vector_service)
):
    """
    更新文档元数据
    """
    try:
        result = vector_service.update_document_vector_status(kb_name, doc_id, has_vector)
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            return JSONResponse(
                status_code=404 if "不存在" in result["message"] else 500,
                content=result
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"更新文档元数据失败: {str(e)}"
            }
        )

@router.post("/api/documents/{doc_id}/vectorize", response_class=JSONResponse)
async def vectorize_document(
    doc_id: str, 
    kb_name: str = Body(..., embed=True),
    vector_service: VectorService = Depends(get_vector_service)
):
    """
    将指定文档转换为向量并存储
    """
    try:
        result = vector_service.vectorize_document(kb_name, doc_id)
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            status_code = 404 if "不存在" in result["message"] else 500
            return JSONResponse(
                status_code=status_code,
                content=result
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"向量化文档失败: {str(e)}"
            }
        )

@router.get("/documents/{kb_id}", response_class=HTMLResponse)
async def view_knowledge_base_documents(
    request: Request, 
    kb_id: int,
    kb_service: KnowledgeBaseService = Depends(get_kb_service)
):
    """
    查看知识库中的文档列表页面
    """
    try:
        # 根据ID获取知识库信息
        kb = kb_service.get_knowledge_base_by_id(kb_id)
        
        # 如果找不到知识库，抛出404错误
        if not kb:
            raise HTTPException(
                status_code=404, 
                detail=f"知识库 (ID: {kb_id}) 不存在"
            )
        
        # 传递知识库信息到模板
        return templates.TemplateResponse(
            "knowledge/document_viewer.html",
            {
                "request": request,
                "kb_id": kb_id,
                "kb_name": kb.get("name", ""),
                "kb_info": kb
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"查看知识库文档失败: {str(e)}"
        )