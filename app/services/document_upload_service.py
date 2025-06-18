import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Tuple, Dict, Any, List, Optional
import hashlib
import asyncio
import sys
import logging
import threading
import time
from queue import Queue, Empty

# 跨平台文件锁支持
if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentProcessingQueue:
    """文档处理队列管理器"""
    
    def __init__(self):
        self.queue = Queue()
        self.processing = False
        self.current_task = None
        self.processed_count = 0
        self.failed_count = 0
        self.worker_thread = None
        
    def add_task(self, task: Dict[str, Any]):
        """添加处理任务到队列"""
        self.queue.put(task)
        logger.info(f"添加任务到队列: {task['filename']}")
        
        # 如果没有工作线程在运行，启动一个
        if not self.processing:
            self.start_worker()
    
    def start_worker(self):
        """启动工作线程"""
        if self.worker_thread and self.worker_thread.is_alive():
            return
            
        self.processing = True
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        logger.info("文档处理工作线程已启动")
    
    def _process_queue(self):
        """处理队列中的任务"""
        while self.processing:
            try:
                # 获取任务，超时1秒
                task = self.queue.get(timeout=1)
                self.current_task = task
                
                logger.info(f"开始处理文档: {task['filename']}")
                
                # 处理文档
                success = self._process_single_document(task)
                
                if success:
                    self.processed_count += 1
                    logger.info(f"文档处理成功: {task['filename']}")
                else:
                    self.failed_count += 1
                    logger.error(f"文档处理失败: {task['filename']}")
                
                self.queue.task_done()
                self.current_task = None
                
            except Empty:
                # 队列为空，继续等待
                continue
            except Exception as e:
                logger.error(f"处理队列任务时发生错误: {str(e)}")
                if self.current_task:
                    self.failed_count += 1
                    self.queue.task_done()
                    self.current_task = None
        
        logger.info("文档处理工作线程已停止")
    
    def _process_single_document(self, task: Dict[str, Any]) -> bool:
        """处理单个文档"""
        try:
            file_path = Path(task['file_path'])
            vector_store_dir = Path(task['vector_store_dir'])
            doc_id = task['doc_id']
            metadata_file = Path(task['metadata_file'])
            kb_name = task.get('kb_name')
            
            # 更新状态为处理中
            self._update_document_status(metadata_file, doc_id, "processing", False)
            
            # 确保向量存储目录存在
            vector_store_dir.mkdir(parents=True, exist_ok=True)
            
            # 动态导入RAG管道
            dfy_path = str(Path(__file__).parent.parent.parent / "dfy_langchain")
            if dfy_path not in sys.path:
                sys.path.append(dfy_path)
            
            from dfy_langchain.rag_pipeline import RAGPipeline
            
            # 获取知识库的embedding配置
            embedding_config = None
            embedding_config_id = None
            use_local_embedding = True  # 默认使用本地embedding
            
            if kb_name:
                try:
                    # 获取知识库配置
                    from app.services.knowledge_base_service import KnowledgeBaseService
                    kb_service = KnowledgeBaseService()
                    knowledge_bases = kb_service.load_knowledge_bases()
                    
                    kb_config = None
                    for kb in knowledge_bases:
                        if kb.get("name") == kb_name:
                            kb_config = kb
                            break
                    
                    if kb_config:
                        embedding_model_id = kb_config.get("embedding_model_id")
                        if embedding_model_id:
                            # 从数据库获取embedding模型配置
                            from app.database import get_db
                            from app.services.model_config_service import ModelConfigService
                            
                            db = next(get_db())
                            try:
                                model_config = ModelConfigService.get_model_config_by_id(db, embedding_model_id)
                                if model_config:
                                    embedding_config = {
                                        "id": model_config.id,
                                        "provider": model_config.provider,
                                        "model_name": model_config.model_name,
                                        "api_key": model_config.api_key,
                                        "endpoint": model_config.endpoint,
                                        "model_type": model_config.model_type
                                    }
                                    embedding_config_id = embedding_model_id
                                    use_local_embedding = False
                                    logger.info(f"✅ 使用知识库配置的embedding模型: {model_config.model_name} (provider: {model_config.provider})")
                                else:
                                    logger.warning(f"未找到embedding模型配置 (ID: {embedding_model_id})，使用本地模型")
                            finally:
                                db.close()
                        else:
                            logger.warning(f"知识库 '{kb_name}' 未配置embedding模型，使用本地模型")
                    else:
                        logger.warning(f"未找到知识库 '{kb_name}' 的配置，使用本地模型")
                        
                except Exception as e:
                    logger.error(f"获取embedding配置失败: {e}，使用本地模型")
            
            # 创建RAG管道实例，使用配置的embedding模型
            if embedding_config:
                rag_pipeline = RAGPipeline(
                    file_path=str(file_path),
                    vector_store_path=str(vector_store_dir),
                    embedding_config=embedding_config,
                    use_local_embedding=False
                )
            else:
                rag_pipeline = RAGPipeline(
                    file_path=str(file_path),
                    vector_store_path=str(vector_store_dir),
                    use_local_embedding=True
                )
            
            # 🚀 优先使用普通向量化处理，确保基础向量存储创建成功
            try:
                logger.info(f"开始向量化处理文档: {task['filename']}")
                result = rag_pipeline.load_single_document(str(file_path))
                
                # 如果普通向量化成功，再尝试分层索引优化
                if result:
                    logger.info(f"基础向量化成功，尝试分层索引优化: {task['filename']}")
                    try:
                        hierarchical_result = self._process_with_hierarchical_index(task, embedding_config, use_local_embedding)
                        if hierarchical_result:
                            logger.info(f"分层索引优化成功: {task['filename']}")
                        else:
                            logger.info(f"分层索引优化跳过，基础向量化已完成: {task['filename']}")
                    except Exception as hierarchical_error:
                        logger.warning(f"分层索引优化失败，但基础向量化已完成: {hierarchical_error}")
                else:
                    logger.error(f"向量化处理失败: {task['filename']}")
            finally:
                # 显存清理：删除RAG管道实例并强制垃圾回收
                del rag_pipeline
                
                # 清理PyTorch缓存
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        torch.cuda.synchronize()
                        logger.info(f"已清理GPU缓存，文档: {task['filename']}")
                except Exception as cache_error:
                    logger.warning(f"清理GPU缓存时出现警告: {str(cache_error)}")
                
                # 强制Python垃圾回收
                import gc
                gc.collect()
            
            if result:
                # 更新文档状态为完成
                self._update_document_status(metadata_file, doc_id, "completed", True)
                logger.info(f"文档处理成功并已清理显存: {task['filename']}")
                logger.info(f"文档向量化成功: {task['filename']}")
                
                return True
            else:
                # 处理失败
                self._update_document_status(metadata_file, doc_id, "error", False, "向量化处理失败")
                logger.error(f"文档向量化失败: {task['filename']}")
                return False
            
        except Exception as e:
            logger.error(f"处理文档失败: {str(e)}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            
            # 即使出错也要尝试清理显存
            try:
                import torch
                import gc
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                gc.collect()
                logger.info(f"错误处理后已清理显存: {task.get('filename', 'unknown')}")
            except Exception as cleanup_error:
                logger.warning(f"错误处理后清理显存失败: {str(cleanup_error)}")
            
            # 更新状态为错误
            self._update_document_status(metadata_file, doc_id, "error", False, str(e))
            
            return False
    
    def _update_document_status(self, metadata_file: Path, doc_id: str, status: str, has_vector: bool, error_message: str = None):
        """更新文档状态"""
        try:
            if metadata_file.exists():
                with metadata_file.open("r", encoding="utf-8") as f:
                    metadata = json.load(f)
            else:
                metadata = {"documents": {}}
            
            if doc_id in metadata["documents"]:
                metadata["documents"][doc_id]["vector_status"] = status
                metadata["documents"][doc_id]["has_vector"] = has_vector
                
                if status == "completed":
                    metadata["documents"][doc_id]["vector_time"] = datetime.now().isoformat()
                elif status == "error" and error_message:
                    metadata["documents"][doc_id]["error_message"] = error_message
                
                with metadata_file.open("w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                    
        except Exception as e:
            logger.error(f"更新文档状态失败: {str(e)}")
    
    def _get_kb_paths(self, kb_name: str) -> Dict[str, Path]:
        """获取知识库相关路径"""
        data_dir = Path("data/knowledge_base")
        kb_dir = data_dir / kb_name
        return {
            "kb_dir": kb_dir,
            "content_dir": kb_dir / "content",
            "vector_store_dir": kb_dir / "vector_store",
            "metadata_file": kb_dir / "content" / "documents_metadata.json"
        }
    
    def _process_with_hierarchical_index(self, task: Dict[str, Any], embedding_config: Dict = None, use_local_embedding: bool = True) -> bool:
        """使用分层索引处理文档"""
        try:
            kb_name = task.get('kb_name')
            file_path = Path(task['file_path'])
            
            logger.info(f"开始分层索引处理: {file_path.name}")
            
            # 动态导入分层索引服务
            dfy_path = str(Path(__file__).parent.parent.parent / "dfy_langchain")
            if dfy_path not in sys.path:
                sys.path.append(dfy_path)
            
            from dfy_langchain.retrievers.services.auto_hierarchical_rebuild import trigger_auto_rebuild
            
            # 触发分层索引重建（包含新文档）
            result = trigger_auto_rebuild(kb_name)
            
            if result["success"]:
                logger.info(f"分层索引处理成功: {file_path.name}")
                return True
            else:
                logger.error(f"分层索引处理失败: {result.get('message', 'unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"分层索引处理异常: {str(e)}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False
    
    def _trigger_hierarchical_rebuild_if_needed(self, kb_name: str):
        """触发分层索引自动重建（如果需要）"""
        try:
            # 动态导入自动重建服务
            dfy_path = str(Path(__file__).parent.parent.parent / "dfy_langchain")
            if dfy_path not in sys.path:
                sys.path.append(dfy_path)
            
            from dfy_langchain.retrievers.services.auto_hierarchical_rebuild import trigger_auto_rebuild
            
            # 触发自动重建
            result = trigger_auto_rebuild(kb_name)
            
            if result["success"]:
                if result["action"] == "rebuilt":
                    logger.info(f"知识库 {kb_name} 分层索引已自动重建")
                elif result["action"] == "no_rebuild_needed":
                    logger.info(f"知识库 {kb_name} 无需重建分层索引: {result['message']}")
            else:
                logger.warning(f"知识库 {kb_name} 自动重建分层索引失败: {result['message']}")
                
        except Exception as e:
            logger.warning(f"触发分层索引自动重建失败: {str(e)}")
            # 这是一个非关键功能，失败不应影响主流程
    
    def get_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return {
            "queue_size": self.queue.qsize(),
            "processing": self.processing,
            "current_task": self.current_task,
            "processed_count": self.processed_count,
            "failed_count": self.failed_count
        }
    
    def stop(self):
        """停止处理队列"""
        self.processing = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)

# 全局队列实例
processing_queue = DocumentProcessingQueue()

class DocumentUploadService:
    """文档上传和向量化服务"""
    
    def __init__(self):
        self.data_dir = Path("data/knowledge_base")
    
    def _lock_file(self, file_handle, exclusive=False):
        """跨平台文件锁"""
        if sys.platform == "win32":
            # Windows 使用 msvcrt
            try:
                if exclusive:
                    msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, 1)
            except IOError:
                raise Exception("无法获取文件锁")
        else:
            # Unix/Linux 使用 fcntl
            lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            fcntl.flock(file_handle.fileno(), lock_type)
    
    def _unlock_file(self, file_handle):
        """跨平台文件解锁"""
        if sys.platform == "win32":
            # Windows 使用 msvcrt
            try:
                msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            except IOError:
                pass  # 忽略解锁错误
        else:
            # Unix/Linux 使用 fcntl
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
    
    def _get_kb_paths(self, kb_name: str) -> Dict[str, Path]:
        """获取知识库相关路径"""
        kb_dir = self.data_dir / kb_name
        return {
            "kb_dir": kb_dir,
            "content_dir": kb_dir / "content",
            "vector_store_dir": kb_dir / "vector_store",
            "metadata_file": kb_dir / "content" / "documents_metadata.json"
        }
    
    def _ensure_directories(self, paths: Dict[str, Path]) -> None:
        """确保目录存在"""
        paths["content_dir"].mkdir(parents=True, exist_ok=True)
        paths["vector_store_dir"].mkdir(parents=True, exist_ok=True)
    
    def _load_metadata(self, metadata_file: Path) -> Dict[str, Any]:
        """加载文档元数据（带文件锁）"""
        if not metadata_file.exists():
            return {"documents": {}}
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with metadata_file.open("r", encoding="utf-8") as f:
                    # 获取共享锁（读锁）
                    self._lock_file(f, False)
                    try:
                        content = f.read()
                        if content.strip():
                            return json.loads(content)
                        else:
                            return {"documents": {}}
                    finally:
                        self._unlock_file(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.warning(f"元数据文件读取失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    logger.warning("元数据文件格式错误，创建新的元数据")
                    return {"documents": {}}
                time.sleep(0.1)  # 短暂等待后重试
            except Exception as e:
                logger.error(f"读取元数据文件时发生未知错误: {str(e)}")
                if attempt == max_retries - 1:
                    return {"documents": {}}
                time.sleep(0.1)
        
        return {"documents": {}}
    
    def _save_metadata(self, metadata_file: Path, metadata: Dict[str, Any]) -> None:
        """保存文档元数据（带文件锁和原子写入）"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 确保目录存在
                metadata_file.parent.mkdir(parents=True, exist_ok=True)
                
                # 使用临时文件进行原子写入
                temp_file = metadata_file.with_suffix('.tmp')
                
                with temp_file.open("w", encoding="utf-8") as f:
                    # 获取排他锁（写锁）
                    self._lock_file(f, True)
                    try:
                        json.dump(metadata, f, ensure_ascii=False, indent=2)
                        f.flush()
                        os.fsync(f.fileno())  # 强制写入磁盘
                    finally:
                        self._unlock_file(f)
                
                # 原子性地替换原文件
                temp_file.replace(metadata_file)
                logger.info(f"元数据保存成功: {metadata_file}")
                return
                
            except Exception as e:
                logger.error(f"保存元数据文件失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    raise Exception(f"保存元数据文件失败: {str(e)}")
                time.sleep(0.1)  # 短暂等待后重试
                
                # 清理临时文件
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except:
                        pass
    
    def _safe_update_metadata(self, metadata_file: Path, doc_id: str, doc_metadata: Dict[str, Any]) -> None:
        """安全地更新元数据（防止并发冲突）"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # 重新加载最新的元数据
                current_metadata = self._load_metadata(metadata_file)
                
                # 添加新文档
                current_metadata["documents"][doc_id] = doc_metadata
                
                # 保存更新后的元数据
                self._save_metadata(metadata_file, current_metadata)
                logger.info(f"文档元数据更新成功: {doc_id}")
                return
                
            except Exception as e:
                logger.error(f"更新元数据失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    raise Exception(f"更新元数据失败: {str(e)}")
                time.sleep(0.2)  # 等待更长时间后重试
    
    def _get_file_hash(self, file_path: Path) -> str:
        """获取文件的MD5哈希值"""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def _format_file_size(self, size_in_bytes: int) -> str:
        """格式化文件大小"""
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_in_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.2f} {units[unit_index]}"
    
    def _get_file_type_text(self, file_ext: str) -> str:
        """根据文件扩展名获取文件类型文本"""
        type_map = {
            'txt': '文本文件',
            'pdf': 'PDF文档',
            'doc': 'Word文档',
            'docx': 'Word文档',
            'xls': 'Excel表格',
            'xlsx': 'Excel表格',
            'ppt': 'PowerPoint',
            'pptx': 'PowerPoint',
            'csv': 'CSV文件',
            'json': 'JSON文件',
            'xml': 'XML文件',
            'html': 'HTML文件',
            'htm': 'HTML文件',
            'jpg': '图片',
            'jpeg': '图片',
            'png': '图片',
            'gif': '图片'
        }
        return type_map.get(file_ext.lower(), f'{file_ext}文件')
    
    async def upload_and_vectorize(self, file_content: bytes, filename: str, kb_name: str) -> Dict[str, Any]:
        """上传文档并添加到处理队列"""
        try:
            # 获取路径信息
            paths = self._get_kb_paths(kb_name)
            self._ensure_directories(paths)
            
            # 保存原始文件
            file_path = paths["content_dir"] / filename
            with file_path.open("wb") as f:
                f.write(file_content)
            
            logger.info(f"文件保存成功: {file_path}")
            
            # 生成文档ID（使用更精确的时间戳避免冲突）
            timestamp = int(datetime.now().timestamp() * 1000)  # 毫秒级时间戳
            doc_id = f"doc_{timestamp}"
            
            # 获取文件信息
            file_size = os.path.getsize(file_path)
            file_ext = filename.split(".")[-1].lower() if "." in filename else "unknown"
            
            # 根据文件类型选择不同的分块大小
            if file_ext == "excel":
                chunk_size = 3000
                chunk_overlap = 0
            else:
                chunk_size = 1500  # 增加块大小，减少块数量
                chunk_overlap = 150  # 保持10%的重叠率
            
            # 初始化文档元数据
            doc_metadata = {
                "filename": filename,
                "file_size": file_size,
                "size_str": self._format_file_size(file_size),
                "file_type": file_ext,
                "file_type_text": self._get_file_type_text(file_ext),
                "upload_time": datetime.now().isoformat(),
                "has_vector": False,
                "vector_status": "waiting",
                "problem_status": "正常",
                "file_hash": self._get_file_hash(file_path)
            }
            
            # 使用安全的元数据更新方法
            self._safe_update_metadata(paths["metadata_file"], doc_id, doc_metadata)
            
            # 添加到处理队列
            task = {
                "doc_id": doc_id,
                "filename": filename,
                "file_path": str(file_path),
                "vector_store_dir": str(paths["vector_store_dir"]),
                "metadata_file": str(paths["metadata_file"]),
                "kb_name": kb_name
            }
            
            processing_queue.add_task(task)
            
            return {
                "success": True,
                "message": "文档上传成功，已添加到处理队列",
                "data": {
                    "doc_id": doc_id,
                    "filename": filename,
                    "has_vector": False,
                    "vector_status": "waiting",
                    "queue_position": processing_queue.queue.qsize()
                }
            }
            
        except Exception as e:
            logger.error(f"上传文档失败: {str(e)}")
            raise Exception(f"上传文档失败: {str(e)}")
    
    def get_processing_status(self) -> Dict[str, Any]:
        """获取处理队列状态"""
        return processing_queue.get_status()
    
    def get_documents(self, kb_name: str, page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """获取文档列表"""
        try:
            paths = self._get_kb_paths(kb_name)
            
            if not paths["metadata_file"].exists():
                return {
                    "success": True,
                    "data": [],
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": 0,
                        "total_pages": 0
                    }
                }
            
            metadata = self._load_metadata(paths["metadata_file"])
            
            # 转换为列表并排序
            documents = [{
                "id": doc_id,
                **doc_data
            } for doc_id, doc_data in metadata["documents"].items()]
            documents.sort(key=lambda x: x["upload_time"], reverse=True)
            
            # 计算分页
            total = len(documents)
            total_pages = (total + limit - 1) // limit
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            
            return {
                "success": True,
                "data": documents[start_idx:end_idx],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "total_pages": total_pages
                }
            }
            
        except Exception as e:
            logger.error(f"获取文档列表失败: {str(e)}")
            raise Exception(f"获取文档列表失败: {str(e)}")
    
    def delete_document(self, doc_id: str, kb_name: str) -> Dict[str, Any]:
        """删除文档"""
        try:
            paths = self._get_kb_paths(kb_name)
            
            if not paths["metadata_file"].exists():
                raise Exception("找不到文档元数据")
            
            metadata = self._load_metadata(paths["metadata_file"])
            
            if doc_id not in metadata["documents"]:
                raise Exception("找不到指定的文档")
            
            # 删除原始文件
            file_path = paths["content_dir"] / metadata["documents"][doc_id]["filename"]
            if file_path.exists():
                file_path.unlink()
            
            # 从元数据中删除
            del metadata["documents"][doc_id]
            self._save_metadata(paths["metadata_file"], metadata)
            
            return {
                "success": True,
                "message": "文档删除成功"
            }
            
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            raise Exception(f"删除文档失败: {str(e)}")