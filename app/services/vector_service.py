import os
import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import shutil

logger = logging.getLogger(__name__)

class VectorService:
    """向量化服务"""
    
    def __init__(self):
        # 获取项目根目录
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.knowledge_base_dir = self.base_dir / "data" / "knowledge_base"
    
    def check_vector_store_exists(self, kb_name: str, doc_id: str) -> bool:
        """
        检查文档的向量库是否存在
        
        Args:
            kb_name: 知识库名称
            doc_id: 文档ID
            
        Returns:
            向量库是否存在
        """
        try:
            vector_store_path = self.knowledge_base_dir / kb_name / "vector_store"
            index_path = vector_store_path / doc_id
            
            return vector_store_path.exists() and index_path.exists()
        except Exception as e:
            logger.error(f"检查向量库状态失败: {str(e)}")
            return False
    
    def update_document_vector_status(self, kb_name: str, doc_id: str, has_vector: bool) -> Dict[str, Any]:
        """
        更新文档的向量状态
        
        Args:
            kb_name: 知识库名称
            doc_id: 文档ID
            has_vector: 是否已生成向量
            
        Returns:
            更新结果
        """
        try:
            from .document_metadata_service import DocumentMetadataService
            
            metadata_service = DocumentMetadataService()
            
            # 加载现有元数据
            metadata = metadata_service.load_documents_metadata(kb_name)
            
            if doc_id not in metadata["documents"]:
                return {
                    "success": False,
                    "message": f"文档 '{doc_id}' 不存在"
                }
            
            # 更新向量状态
            metadata["documents"][doc_id]["has_vector"] = has_vector
            metadata["documents"][doc_id]["vector_status"] = "completed" if has_vector else "waiting"
            
            # 保存更新后的元数据
            if metadata_service.save_documents_metadata(kb_name, metadata):
                return {
                    "success": True,
                    "message": "文档向量状态已更新"
                }
            else:
                return {
                    "success": False,
                    "message": "保存文档元数据失败"
                }
                
        except Exception as e:
            logger.error(f"更新文档向量状态失败: {str(e)}")
            return {
                "success": False,
                "message": f"更新文档向量状态失败: {str(e)}"
            }
    
    def vectorize_document(self, kb_name: str, doc_identifier: str) -> Dict[str, Any]:
        """
        将指定文档转换为向量并存储
        
        Args:
            kb_name: 知识库名称
            doc_identifier: 文档标识符（可以是doc_id或filename）
            
        Returns:
            处理结果
        """
        try:
            from .document_metadata_service import DocumentMetadataService
            from .knowledge_base_service import KnowledgeBaseService
            
            logger.info(f"尝试向量化文档: {doc_identifier}, 知识库: {kb_name}")
            
            # 验证知识库是否存在
            kb_dir = self.knowledge_base_dir / kb_name
            if not kb_dir.exists():
                return {
                    "success": False,
                    "message": f"知识库 '{kb_name}' 不存在"
                }
            
            metadata_service = DocumentMetadataService()
            kb_service = KnowledgeBaseService()
            
            # 加载文档元数据
            all_metadata = metadata_service.load_documents_metadata(kb_name)
            documents = all_metadata.get("documents", {})
            
            # 查找文档：先按doc_id查找，如果找不到则按filename查找
            doc_id = None
            doc_info = None
            
            # 首先尝试作为doc_id查找
            if doc_identifier in documents:
                doc_id = doc_identifier
                doc_info = documents[doc_identifier]
            else:
                # 如果不是doc_id，则按filename查找
                for did, dinfo in documents.items():
                    if dinfo.get("filename") == doc_identifier:
                        doc_id = did
                        doc_info = dinfo
                        break
            
            # 检查文档是否存在
            if not doc_id or not doc_info:
                return {
                    "success": False,
                    "message": f"文档 '{doc_identifier}' 不存在"
                }
            
            # 获取文档信息（已在前面获取）
            filename = doc_info.get("filename")
            
            if not filename:
                return {
                    "success": False,
                    "message": f"文档 '{doc_id}' 元数据不完整"
                }
            
            # 构建文件路径
            file_path = kb_dir / "content" / filename
            
            if not file_path.exists():
                return {
                    "success": False,
                    "message": f"文件 '{filename}' 不存在"
                }
            
            # 获取知识库配置
            knowledge_bases = kb_service.load_knowledge_bases()
            kb_config = None
            
            for kb in knowledge_bases:
                if kb.get("name") == kb_name:
                    kb_config = kb
                    break
            
            if not kb_config:
                return {
                    "success": False,
                    "message": f"找不到知识库 '{kb_name}' 的配置"
                }
            
            # 使用配置的embedding模型进行向量化
            try:
                # 获取embedding模型配置
                embedding_model_id = kb_config.get("embedding_model_id")
                if not embedding_model_id:
                    logger.warning(f"知识库 '{kb_name}' 未配置embedding模型，尝试使用默认模型")
                    embedding_config = None
                else:
                    from app.database import get_db
                    from app.services.model_config_service import ModelConfigService
                    
                    db = next(get_db())
                    try:
                        model_config = ModelConfigService.get_model_config_by_id(db, embedding_model_id)
                        if not model_config:
                            logger.error(f"找不到embedding模型配置 (ID: {embedding_model_id})")
                            doc_info["has_vector"] = False
                            doc_info["vector_status"] = "error"
                            doc_info["error_message"] = "找不到embedding模型配置"
                            metadata_service.save_documents_metadata(kb_name, all_metadata)
                            return {
                                "success": False,
                                "message": "找不到embedding模型配置"
                            }
                        
                        embedding_config = {
                            "id": model_config.id,
                            "provider": model_config.provider,
                            "model_name": model_config.model_name,
                            "api_key": model_config.api_key,
                            "endpoint": model_config.endpoint,
                            "model_type": model_config.model_type
                        }
                    finally:
                        db.close()
                
                # 初始化RAG pipeline进行向量化
                from dfy_langchain.rag_pipeline import RAGPipeline
                
                # 执行向量化处理
                vector_store_path = kb_dir / "vector_store"  # 修正路径，移除doc_id子目录
                vector_store_path.mkdir(parents=True, exist_ok=True)
                
                # 使用配置的embedding模型初始化RAG pipeline
                if embedding_config:
                    logger.info(f"使用远程embedding模型: {embedding_config['model_name']} (provider: {embedding_config['provider']})")
                    rag_pipeline = RAGPipeline(
                        file_path=str(file_path),
                        vector_store_path=str(vector_store_path),
                        embedding_config=embedding_config,
                        use_local_embedding=False
                    )
                else:
                    # 使用本地embedding模型作为fallback
                    logger.info("未找到embedding模型配置，使用本地模型")
                    rag_pipeline = RAGPipeline(
                        file_path=str(file_path),
                        vector_store_path=str(vector_store_path),
                        use_local_embedding=True
                    )
                
                # 实际执行向量化处理
                success = rag_pipeline.load_single_document(str(file_path))
                
                if not success:
                    raise Exception("RAG Pipeline向量化处理失败")
                
                # 验证向量文件是否成功创建
                index_file = vector_store_path / "index.faiss"
                pkl_file = vector_store_path / "index.pkl"
                
                if not (index_file.exists() and pkl_file.exists()):
                    raise Exception(f"向量文件创建失败: index.faiss={index_file.exists()}, index.pkl={pkl_file.exists()}")
                
                logger.info(f"文档 '{filename}' 向量化处理完成")
                logger.info(f"向量文件保存在: {vector_store_path}")
                
                # 更新元数据
                doc_info["has_vector"] = True
                doc_info["vector_status"] = "completed"
                doc_info["vector_time"] = datetime.datetime.now().isoformat()
                doc_info["embedding_model_id"] = embedding_model_id
                
                # 保存元数据
                if metadata_service.save_documents_metadata(kb_name, all_metadata):
                    return {
                        "success": True,
                        "message": f"文档 '{filename}' 向量化成功",
                        "data": {
                            "doc_id": doc_id,
                            "has_vector": True,
                            "vector_status": "completed",
                            "embedding_model_id": embedding_model_id
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": "保存文档元数据失败"
                    }
                    
            except Exception as vector_error:
                logger.error(f"向量化处理失败: {str(vector_error)}")
                
                # 更新元数据标记为错误
                doc_info["has_vector"] = False
                doc_info["vector_status"] = "error"
                doc_info["vector_time"] = datetime.datetime.now().isoformat()
                doc_info["error_message"] = str(vector_error)
                
                metadata_service.save_documents_metadata(kb_name, all_metadata)
                
                return {
                    "success": False,
                    "message": f"向量化处理失败: {str(vector_error)}"
                }
                
        except Exception as e:
            logger.error(f"处理文档失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                "success": False,
                "message": f"处理文档失败: {str(e)}"
            }
    
    def delete_document_vectors(self, kb_name: str, doc_id: str) -> bool:
        """
        删除文档的向量数据
        
        Args:
            kb_name: 知识库名称
            doc_id: 文档ID
            
        Returns:
            是否删除成功
        """
        try:
            vector_store_path = self.knowledge_base_dir / kb_name / "vector_store"
            doc_vector_path = vector_store_path / doc_id
            
            if doc_vector_path.exists():
                if doc_vector_path.is_dir():
                    shutil.rmtree(doc_vector_path)
                else:
                    doc_vector_path.unlink()
                logger.info(f"已删除文档 {doc_id} 的向量数据")
            
            return True
            
        except Exception as e:
            logger.error(f"删除文档向量数据失败: {str(e)}")
            return False
    
    def get_vector_store_info(self, kb_name: str) -> Dict[str, Any]:
        """
        获取向量库信息
        
        Args:
            kb_name: 知识库名称
            
        Returns:
            向量库信息
        """
        try:
            vector_store_path = self.knowledge_base_dir / kb_name / "vector_store"
            
            if not vector_store_path.exists():
                return {
                    "exists": False,
                    "message": "向量库不存在"
                }
            
            # 统计向量文件数量
            vector_files = []
            if vector_store_path.is_dir():
                for item in vector_store_path.iterdir():
                    if item.is_file() or item.is_dir():
                        vector_files.append(item.name)
            
            return {
                "exists": True,
                "path": str(vector_store_path),
                "vector_count": len(vector_files),
                "vector_files": vector_files
            }
            
        except Exception as e:
            logger.error(f"获取向量库信息失败: {str(e)}")
            return {
                "exists": False,
                "message": f"获取向量库信息失败: {str(e)}"
            }