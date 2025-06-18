import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class DocumentMetadataService:
    """文档元数据管理服务"""
    
    def __init__(self):
        # 获取项目根目录
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.knowledge_base_dir = self.base_dir / "data" / "knowledge_base"
        self.documents_metadata_file = "documents_metadata.json"
    
    def load_documents_metadata(self, kb_name: str) -> Dict[str, Any]:
        """
        加载知识库文档元数据
        
        Args:
            kb_name: 知识库名称
            
        Returns:
            包含文档元数据的字典
        """
        metadata_file = self.knowledge_base_dir / kb_name / "content" / self.documents_metadata_file
        
        # 确保content目录存在
        content_dir = self.knowledge_base_dir / kb_name / "content"
        os.makedirs(content_dir, exist_ok=True)
        
        # 如果元数据文件不存在，创建一个空的元数据文件
        if not metadata_file.exists():
            metadata = {"documents": {}}
            self.save_documents_metadata(kb_name, metadata)
            return metadata
        
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载文档元数据失败: {str(e)}")
            # 如果加载失败，返回空元数据
            return {"documents": {}}
    
    def save_documents_metadata(self, kb_name: str, metadata: Dict[str, Any]) -> bool:
        """
        保存知识库文档元数据
        
        Args:
            kb_name: 知识库名称
            metadata: 要保存的元数据字典
            
        Returns:
            是否保存成功
        """
        try:
            metadata_file = self.knowledge_base_dir / kb_name / "content" / self.documents_metadata_file
            
            # 确保content目录存在
            content_dir = self.knowledge_base_dir / kb_name / "content"
            os.makedirs(content_dir, exist_ok=True)
            
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logger.error(f"保存文档元数据失败: {str(e)}")
            return False
    
    def update_document_metadata(self, kb_name: str, doc_id: str, metadata: Dict[str, Any]) -> bool:
        """
        更新单个文档的元数据
        
        Args:
            kb_name: 知识库名称
            doc_id: 文档ID
            metadata: 文档元数据
            
        Returns:
            是否更新成功
        """
        try:
            # 加载现有元数据
            all_metadata = self.load_documents_metadata(kb_name)
            
            # 更新指定文档的元数据
            all_metadata["documents"][doc_id] = metadata
            
            # 保存更新后的元数据
            return self.save_documents_metadata(kb_name, all_metadata)
        except Exception as e:
            logger.error(f"更新文档元数据失败: {str(e)}")
            return False
    
    def delete_document_metadata(self, kb_name: str, doc_id: str) -> bool:
        """
        删除单个文档的元数据
        
        Args:
            kb_name: 知识库名称
            doc_id: 文档ID
            
        Returns:
            是否删除成功
        """
        try:
            # 加载现有元数据
            all_metadata = self.load_documents_metadata(kb_name)
            
            # 如果文档ID存在于元数据中，删除它
            if doc_id in all_metadata["documents"]:
                del all_metadata["documents"][doc_id]
                
                # 保存更新后的元数据
                return self.save_documents_metadata(kb_name, all_metadata)
            
            return True  # 如果文档不存在于元数据中，视为删除成功
        except Exception as e:
            logger.error(f"删除文档元数据失败: {str(e)}")
            return False
    
    def get_document_metadata(self, kb_name: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个文档的元数据
        
        Args:
            kb_name: 知识库名称
            doc_id: 文档ID
            
        Returns:
            文档元数据或None
        """
        try:
            all_metadata = self.load_documents_metadata(kb_name)
            return all_metadata["documents"].get(doc_id)
        except Exception as e:
            logger.error(f"获取文档元数据失败: {str(e)}")
            return None
    
    def list_documents(self, kb_name: str, page: int = 1, limit: int = 10, search: Optional[str] = None) -> Dict[str, Any]:
        """
        获取文档列表
        
        Args:
            kb_name: 知识库名称
            page: 页码
            limit: 每页数量
            search: 搜索关键词
            
        Returns:
            文档列表和分页信息
        """
        try:
            # 加载元数据
            metadata = self.load_documents_metadata(kb_name)
            documents = metadata.get("documents", {})
            
            # 将文档转换为列表格式
            doc_list = []
            for doc_id, doc_info in documents.items():
                doc_data = doc_info.copy()
                doc_data["id"] = doc_id
                doc_list.append(doc_data)
            
            # 应用搜索过滤
            if search:
                search_lower = search.lower()
                doc_list = [
                    doc for doc in doc_list
                    if search_lower in doc.get("filename", "").lower()
                    or search_lower in doc.get("file_type_text", "").lower()
                ]
            
            # 按上传时间排序（最新的在前）
            doc_list.sort(key=lambda x: x.get("upload_time", ""), reverse=True)
            
            # 分页处理
            total = len(doc_list)
            start_index = (page - 1) * limit
            end_index = start_index + limit
            
            paginated_docs = doc_list[start_index:end_index]
            
            return {
                "success": True,
                "data": paginated_docs,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit
                }
            }
            
        except Exception as e:
            logger.error(f"获取文档列表失败: {str(e)}")
            return {
                "success": False,
                "message": f"获取文档列表失败: {str(e)}",
                "data": [],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": 0,
                    "pages": 0
                }
            }
    
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