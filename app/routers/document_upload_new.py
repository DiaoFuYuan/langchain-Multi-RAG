from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from app.services.document_upload_service import DocumentUploadService
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# 创建文档上传服务实例
upload_service = DocumentUploadService()

@router.post("/knowledge/api/documents/upload-with-vectorization")
async def upload_document_with_vectorization(
    file: UploadFile = File(...), 
    kb_name: str = Form(...)
):
    """
    上传文档并进行向量化处理
    """
    try:
        # 验证知识库名称
        if not kb_name or not kb_name.strip():
            raise HTTPException(status_code=400, detail="知识库名称不能为空")
        
        # 验证文件
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        # 读取文件内容
        file_content = await file.read()
        
        # 验证文件大小（限制为1GB）
        max_size = 1024 * 1024 * 1024  # 1GB
        if len(file_content) > max_size:
            raise HTTPException(status_code=400, detail="文件大小不能超过1GB")
        
        # 验证文件类型
        allowed_extensions = {
            'txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 
            'ppt', 'pptx', 'csv', 'json', 'xml', 'html', 'htm'
        }
        file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型: {file_ext}。支持的类型: {', '.join(allowed_extensions)}"
            )
        
        logger.info(f"开始上传文件: {file.filename} 到知识库: {kb_name}")
        
        # 调用服务进行上传和向量化
        result = await upload_service.upload_and_vectorize(
            file_content=file_content,
            filename=file.filename,
            kb_name=kb_name.strip()
        )
        
        # 上传成功后清除分层索引状态缓存，确保状态能及时更新
        if result.get("success", False):
            _clear_hierarchical_status_cache(kb_name.strip())
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传文档失败: {str(e)}")

@router.get("/knowledge/api/documents/list")
async def get_documents_list(kb_name: str, page: int = 1, limit: int = 10):
    """
    获取文档列表
    """
    try:
        # 验证参数
        if not kb_name or not kb_name.strip():
            raise HTTPException(status_code=400, detail="知识库名称不能为空")
        
        if page < 1:
            page = 1
        
        if limit < 1 or limit > 100:
            limit = 10
        
        # 调用服务获取文档列表
        result = upload_service.get_documents(
            kb_name=kb_name.strip(),
            page=page,
            limit=limit
        )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")

@router.delete("/knowledge/api/documents/delete/{doc_id}")
async def delete_document_by_id(doc_id: str, kb_name: str):
    """
    删除指定文档
    """
    try:
        # 验证参数
        if not kb_name or not kb_name.strip():
            raise HTTPException(status_code=400, detail="知识库名称不能为空")
        
        if not doc_id or not doc_id.strip():
            raise HTTPException(status_code=400, detail="文档ID不能为空")
        
        # 调用服务删除文档
        result = upload_service.delete_document(
            doc_id=doc_id.strip(),
            kb_name=kb_name.strip()
        )
        
        # 删除成功后清除分层索引状态缓存，确保状态能及时更新
        if result.get("success", False):
            _clear_hierarchical_status_cache(kb_name.strip())
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")

@router.get("/knowledge/api/documents/status/{doc_id}")
async def get_document_status(doc_id: str, kb_name: str):
    """
    获取文档的向量化状态
    """
    try:
        # 验证参数
        if not kb_name or not kb_name.strip():
            raise HTTPException(status_code=400, detail="知识库名称不能为空")
        
        if not doc_id or not doc_id.strip():
            raise HTTPException(status_code=400, detail="文档ID不能为空")
        
        # 获取文档列表并查找指定文档
        documents_result = upload_service.get_documents(kb_name=kb_name.strip(), page=1, limit=1000)
        
        if not documents_result["success"]:
            raise HTTPException(status_code=500, detail="获取文档状态失败")
        
        # 查找指定文档
        target_doc = None
        for doc in documents_result["data"]:
            if doc["id"] == doc_id.strip():
                target_doc = doc
                break
        
        if not target_doc:
            raise HTTPException(status_code=404, detail="找不到指定的文档")
        
        return JSONResponse(content={
            "success": True,
            "data": {
                "doc_id": target_doc["id"],
                "filename": target_doc["filename"],
                "has_vector": target_doc.get("has_vector", False),
                "vector_status": target_doc.get("vector_status", "unknown"),
                "error_message": target_doc.get("error_message", None)
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文档状态失败: {str(e)}")

@router.post("/knowledge/api/documents/re-vectorize/{doc_id}")
async def re_vectorize_document(doc_id: str, kb_name: str):
    """
    重新向量化指定文档
    """
    try:
        # 验证参数
        if not kb_name or not kb_name.strip():
            raise HTTPException(status_code=400, detail="知识库名称不能为空")
        
        if not doc_id or not doc_id.strip():
            raise HTTPException(status_code=400, detail="文档ID不能为空")
        
        # 获取文档信息
        documents_result = upload_service.get_documents(kb_name=kb_name.strip(), page=1, limit=1000)
        
        if not documents_result["success"]:
            raise HTTPException(status_code=500, detail="获取文档信息失败")
        
        # 查找指定文档
        target_doc = None
        for doc in documents_result["data"]:
            if doc["id"] == doc_id.strip():
                target_doc = doc
                break
        
        if not target_doc:
            raise HTTPException(status_code=404, detail="找不到指定的文档")
        
        # 获取文件路径
        from pathlib import Path
        paths = upload_service._get_kb_paths(kb_name.strip())
        file_path = paths["content_dir"] / target_doc["filename"]
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="原始文件不存在")
        
        # 更新状态为等待处理
        metadata = upload_service._load_metadata(paths["metadata_file"])
        if doc_id.strip() in metadata["documents"]:
            metadata["documents"][doc_id.strip()]["vector_status"] = "waiting"
            metadata["documents"][doc_id.strip()]["has_vector"] = False
            # 清除之前的错误信息
            if "error_message" in metadata["documents"][doc_id.strip()]:
                del metadata["documents"][doc_id.strip()]["error_message"]
            upload_service._save_metadata(paths["metadata_file"], metadata)
        
        # 添加到处理队列进行重新向量化
        from app.services.document_upload_service import processing_queue
        
        task = {
            "doc_id": doc_id.strip(),
            "filename": target_doc["filename"],
            "file_path": str(file_path),
            "vector_store_dir": str(paths["vector_store_dir"]),
            "metadata_file": str(paths["metadata_file"]),
            "kb_name": kb_name.strip()
        }
        
        processing_queue.add_task(task)
        
        return JSONResponse(content={
            "success": True,
            "message": "文档已添加到重新处理队列",
            "data": {
                "doc_id": doc_id.strip(),
                "vector_status": "waiting",
                "queue_position": processing_queue.queue.qsize()
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新向量化文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"重新向量化文档失败: {str(e)}")

@router.get("/knowledge/api/documents/processing-status")
async def get_processing_status():
    """
    获取文档处理队列状态
    """
    try:
        status = upload_service.get_processing_status()
        
        return JSONResponse(content={
            "success": True,
            "data": status
        })
        
    except Exception as e:
        logger.error(f"获取处理状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取处理状态失败: {str(e)}")

@router.get("/knowledge/api/documents/hierarchical-status")
async def get_hierarchical_index_status(kb_name: str):
    """
    获取知识库的普通索引和分层索引状态（实时检查文件系统）
    """
    try:
        from pathlib import Path
        import json
        from datetime import datetime
        
        # 验证参数
        if not kb_name or not kb_name.strip():
            raise HTTPException(status_code=400, detail="知识库名称不能为空")
        
        kb_name = kb_name.strip()
        base_dir = Path(__file__).parent.parent.parent
        
        logger.info(f"实时检测知识库 '{kb_name}' 的分层索引状态")
        
        # 实时检测索引状态（不依赖缓存）
        vector_store_path = base_dir / "data" / "knowledge_base" / kb_name / "vector_store"
        normal_index_exists = (
            vector_store_path.exists() and 
            (vector_store_path / "index.faiss").exists() and 
            (vector_store_path / "index.pkl").exists()
        )
        
        hierarchical_store_path = base_dir / "data" / "knowledge_base" / kb_name / "hierarchical_vector_store"
        summary_path = hierarchical_store_path / "summary_vector_store"
        chunk_path = hierarchical_store_path / "chunk_vector_store"
        
        hierarchical_index_exists = (
            hierarchical_store_path.exists() and
            summary_path.exists() and
            chunk_path.exists() and
            (summary_path / "index.faiss").exists() and
            (summary_path / "index.pkl").exists() and
            (chunk_path / "index.faiss").exists() and
            (chunk_path / "index.pkl").exists()
        )
        
        # 获取文档统计信息
        doc_count = 0
        group_count = 0
        should_rebuild = False
        reason = "未知"
        
        # 首先尝试从重建记录获取基础信息（更可靠）
        rebuild_record_file = base_dir / "data" / "knowledge_base" / kb_name / "hierarchical_rebuild_record.json"
        if rebuild_record_file.exists():
            try:
                with open(rebuild_record_file, "r", encoding="utf-8") as f:
                    record = json.load(f)
                doc_count = record.get("doc_count", 0)
                group_count = max(1, doc_count // 10) if doc_count > 0 else 1
                logger.info(f"从重建记录获取文档统计: doc_count={doc_count}, group_count={group_count}")
            except Exception as e:
                logger.warning(f"读取重建记录失败: {str(e)}")
        
        # 如果没有重建记录，尝试从元数据文件获取文档数量
        if doc_count == 0:
            metadata_file = base_dir / "data" / "knowledge_base" / kb_name / "content" / "documents_metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                        doc_count = len(metadata.get("documents", {}))
                        group_count = 1 if doc_count > 0 else 0
                        logger.info(f"从元数据文件获取文档统计: doc_count={doc_count}")
                except Exception as e:
                    logger.warning(f"读取元数据文件失败: {str(e)}")
        
        # 确定状态和推荐
        if doc_count == 0:
            reason = "知识库不存在或无文档"
        elif not normal_index_exists:
            reason = "普通索引不存在"
        elif hierarchical_index_exists:
            reason = "分层索引已存在且完整"
            # 检查是否需要重建（如果有新文档）
            if normal_index_exists:
                try:
                    # 比较索引文件的修改时间
                    normal_index_time = (vector_store_path / "index.faiss").stat().st_mtime
                    hierarchical_index_time = min(
                        (summary_path / "index.faiss").stat().st_mtime,
                        (chunk_path / "index.faiss").stat().st_mtime
                    )
                    if normal_index_time > hierarchical_index_time:
                        should_rebuild = True
                        reason = "分层索引需要重建（有新文档）"
                except:
                    pass
        else:
            if doc_count > 0:
                should_rebuild = True
                reason = "建议建立分层索引以提升检索性能"
            else:
                reason = "无需分层索引"
        
        # 构建状态数据
        status_data = {
            "doc_count": doc_count,
            "group_count": group_count,
            "normal_index_exists": normal_index_exists,
            "hierarchical_index_exists": hierarchical_index_exists,
            "should_rebuild": should_rebuild,
            "reason": reason,
            "retriever_recommendation": "hierarchical" if hierarchical_index_exists else "vectorstore",
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info(f"知识库 '{kb_name}' 状态检测完成: doc_count={doc_count}, hierarchical_exists={hierarchical_index_exists}")
        
        return JSONResponse(content={
            "success": True,
            "data": {
                "kb_name": kb_name,
                **status_data
            }
        })
        
    except Exception as e:
        logger.error(f"获取分层索引状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取分层索引状态失败: {str(e)}")

@router.get("/knowledge/api/documents/hierarchical-status-realtime")
async def get_realtime_hierarchical_status(kb_name: str):
    """
    实时获取分层索引状态（不使用任何缓存）
    """
    try:
        from pathlib import Path
        import json
        from datetime import datetime
        
        # 验证参数
        if not kb_name or not kb_name.strip():
            raise HTTPException(status_code=400, detail="知识库名称不能为空")
        
        kb_name = kb_name.strip()
        base_dir = Path(__file__).parent.parent.parent
        
        # 实时检查文件系统
        vector_store_path = base_dir / "data" / "knowledge_base" / kb_name / "vector_store"
        hierarchical_store_path = base_dir / "data" / "knowledge_base" / kb_name / "hierarchical_vector_store"
        
        # 检查普通索引
        normal_index_exists = (
            vector_store_path.exists() and 
            (vector_store_path / "index.faiss").exists() and 
            (vector_store_path / "index.pkl").exists()
        )
        
        # 检查分层索引
        summary_path = hierarchical_store_path / "summary_vector_store"
        chunk_path = hierarchical_store_path / "chunk_vector_store"
        
        hierarchical_index_exists = (
            hierarchical_store_path.exists() and
            summary_path.exists() and
            chunk_path.exists() and
            (summary_path / "index.faiss").exists() and
            (summary_path / "index.pkl").exists() and
            (chunk_path / "index.faiss").exists() and
            (chunk_path / "index.pkl").exists()
        )
        
        # 获取文档数量
        doc_count = 0
        
        # 从元数据文件获取文档数量
        metadata_file = base_dir / "data" / "knowledge_base" / kb_name / "content" / "documents_metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    doc_count = len(metadata.get("documents", {}))
            except Exception as e:
                logger.warning(f"读取元数据文件失败: {str(e)}")
        
        return JSONResponse(content={
            "success": True,
            "data": {
                "kb_name": kb_name,
                "doc_count": doc_count,
                "normal_index_exists": normal_index_exists,
                "hierarchical_index_exists": hierarchical_index_exists,
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"获取实时分层索引状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取实时分层索引状态失败: {str(e)}")

def _should_refresh_status(cached_status: dict) -> bool:
    """
    判断是否需要刷新状态缓存
    """
    try:
        from datetime import datetime, timedelta
        
        last_updated_str = cached_status.get("last_updated")
        if not last_updated_str:
            return True
        
        last_updated = datetime.fromisoformat(last_updated_str)
        # 缓存1分钟有效（文档上传场景需要更快的状态更新）
        return datetime.now() - last_updated > timedelta(minutes=1)
    except:
        return True

def _clear_hierarchical_status_cache(kb_name: str):
    """
    清除指定知识库的分层索引状态缓存
    """
    try:
        import json
        from pathlib import Path
        
        base_dir = Path(__file__).parent.parent.parent
        knowledge_bases_file = base_dir / "data" / "knowledge_base" / "knowledge_bases.json"
        
        if not knowledge_bases_file.exists():
            return
        
        with open(knowledge_bases_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 查找并清除指定知识库的缓存状态
        for kb in data.get("knowledge_bases", []):
            if kb.get("name") == kb_name:
                if "hierarchical_status" in kb:
                    del kb["hierarchical_status"]
                    logger.info(f"已清除知识库 '{kb_name}' 的分层索引状态缓存")
                break
        
        # 保存更新后的配置
        with open(knowledge_bases_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
    except Exception as e:
        logger.warning(f"清除分层索引状态缓存失败: {str(e)}")

@router.post("/knowledge/api/documents/rebuild-hierarchical-index")
async def rebuild_hierarchical_index(kb_name: str = Form(...)):
    """
    手动触发分层索引重建
    """
    try:
        # 验证参数
        if not kb_name or not kb_name.strip():
            raise HTTPException(status_code=400, detail="知识库名称不能为空")
        
        # 动态导入自动重建服务
        import sys
        from pathlib import Path
        
        dfy_path = str(Path(__file__).parent.parent.parent / "dfy_langchain")
        if dfy_path not in sys.path:
            sys.path.append(dfy_path)
        
        from dfy_langchain.retrievers.services.auto_hierarchical_rebuild import trigger_auto_rebuild
        
        logger.info(f"手动触发知识库 {kb_name.strip()} 的分层索引重建")
        
        # 触发重建
        result = trigger_auto_rebuild(kb_name.strip())
        
        # 重建完成后，清除缓存状态以便下次重新检测
        if result["success"]:
            try:
                import json
                knowledge_bases_file = Path(__file__).parent.parent.parent / "data" / "knowledge_base" / "knowledge_bases.json"
                
                if knowledge_bases_file.exists():
                    with open(knowledge_bases_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    # 查找并更新知识库状态
                    for kb in data.get("knowledge_bases", []):
                        if kb.get("name") == kb_name.strip():
                            # 清除缓存状态，强制下次重新检测
                            if "hierarchical_status" in kb:
                                del kb["hierarchical_status"]
                            break
                    
                    # 保存更新后的配置
                    with open(knowledge_bases_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                logger.warning(f"清除索引状态缓存失败: {str(e)}")
        
        return JSONResponse(content={
            "success": result["success"],
            "message": result.get("message", "重建完成"),
            "data": {
                "action": result.get("action", "unknown"),
                "kb_name": kb_name.strip()
            }
        })
        
    except Exception as e:
        logger.error(f"手动重建分层索引失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"手动重建分层索引失败: {str(e)}")