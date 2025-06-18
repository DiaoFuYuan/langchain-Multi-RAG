import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class KnowledgeBaseService:
    """知识库管理服务"""
    
    def __init__(self):
        # 获取项目根目录
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.knowledge_base_dir = self.base_dir / "data" / "knowledge_base"
        self.knowledge_bases_file = self.knowledge_base_dir / "knowledge_bases.json"
        
        # 确保知识库目录存在
        os.makedirs(self.knowledge_base_dir, exist_ok=True)
        
        # 初始化知识库管理文件
        if not self.knowledge_bases_file.exists():
            self._initialize_knowledge_bases_file()
    
    def _initialize_knowledge_bases_file(self) -> None:
        """初始化知识库管理文件"""
        try:
            with open(self.knowledge_bases_file, "w", encoding="utf-8") as f:
                json.dump({"knowledge_bases": []}, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"初始化知识库管理文件失败: {str(e)}")
    
    def load_knowledge_bases(self) -> List[Dict[str, Any]]:
        """
        加载所有知识库信息
        
        Returns:
            知识库列表
        """
        if self.knowledge_bases_file.exists():
            try:
                with open(self.knowledge_bases_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("knowledge_bases", [])
            except Exception as e:
                logger.error(f"加载知识库管理文件失败: {str(e)}")
                return []
        return []
    
    def save_knowledge_bases(self, knowledge_bases: List[Dict[str, Any]]) -> bool:
        """
        保存所有知识库信息
        
        Args:
            knowledge_bases: 知识库列表
            
        Returns:
            是否保存成功
        """
        try:
            with open(self.knowledge_bases_file, "w", encoding="utf-8") as f:
                json.dump({"knowledge_bases": knowledge_bases}, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logger.error(f"保存知识库管理文件失败: {str(e)}")
            return False
    
    def count_knowledge_base_documents(self, kb_name: str) -> int:
        """
        统计知识库中的文档数量
        
        Args:
            kb_name: 知识库名称
            
        Returns:
            文档数量
        """
        try:
            from .document_metadata_service import DocumentMetadataService
            metadata_service = DocumentMetadataService()
            metadata = metadata_service.load_documents_metadata(kb_name)
            return len(metadata.get("documents", {}))
        except Exception as e:
            logger.error(f"统计知识库文档数量失败: {str(e)}")
            return 0
    
    def create_knowledge_base(self, name: str, description: str = "", embedding_model: str = "gte_Qwen2-15B-instruct", embedding_model_id: Optional[int] = None) -> Dict[str, Any]:
        """
        创建新的知识库
        
        Args:
            name: 知识库名称
            description: 知识库描述
            embedding_model: 嵌入模型名称（兼容性保留）
            embedding_model_id: 嵌入模型配置ID
            
        Returns:
            创建结果
        """
        try:
            # 加载现有知识库
            knowledge_bases = self.load_knowledge_bases()
            
            # 检查知识库名称是否已存在
            if any(kb.get("name") == name for kb in knowledge_bases):
                return {
                    "success": False,
                    "message": f"知识库名称 '{name}' 已存在"
                }
            
            # 生成新的ID
            new_id = max([kb.get("id", 0) for kb in knowledge_bases], default=0) + 1
            
            # 创建知识库目录
            kb_dir = self.knowledge_base_dir / name
            os.makedirs(kb_dir, exist_ok=True)
            
            # 创建新知识库配置
            new_kb = {
                "id": new_id,
                "name": name,
                "description": description,
                "create_time": datetime.now().isoformat(),
                "embedding_model": embedding_model,
                "embedding_model_id": embedding_model_id,
                "status": "active"
            }
            
            # 添加到列表并保存
            knowledge_bases.append(new_kb)
            
            if self.save_knowledge_bases(knowledge_bases):
                return {
                    "success": True,
                    "message": f"知识库 '{name}' 创建成功",
                    "data": new_kb
                }
            else:
                return {
                    "success": False,
                    "message": "保存知识库配置失败"
                }
                
        except Exception as e:
            logger.error(f"创建知识库失败: {str(e)}")
            return {
                "success": False,
                "message": f"创建知识库失败: {str(e)}"
            }
    
    def delete_knowledge_base(self, kb_id: int) -> Dict[str, Any]:
        """
        删除知识库
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            删除结果
        """
        try:
            import shutil
            
            # 加载现有知识库
            knowledge_bases = self.load_knowledge_bases()
            
            # 查找要删除的知识库
            kb_to_delete = None
            for kb in knowledge_bases:
                if kb.get("id") == kb_id:
                    kb_to_delete = kb
                    break
            
            if not kb_to_delete:
                return {
                    "success": False,
                    "message": f"知识库 (ID: {kb_id}) 不存在"
                }
            
            kb_name = kb_to_delete.get("name")
            
            # 删除知识库目录
            kb_dir = self.knowledge_base_dir / kb_name
            if kb_dir.exists():
                shutil.rmtree(kb_dir)
            
            # 从列表中移除
            knowledge_bases = [kb for kb in knowledge_bases if kb.get("id") != kb_id]
            
            # 保存更新后的列表
            if self.save_knowledge_bases(knowledge_bases):
                return {
                    "success": True,
                    "message": f"知识库 '{kb_name}' 删除成功"
                }
            else:
                return {
                    "success": False,
                    "message": "保存知识库配置失败"
                }
                
        except Exception as e:
            logger.error(f"删除知识库失败: {str(e)}")
            return {
                "success": False,
                "message": f"删除知识库失败: {str(e)}"
            }
    
    def update_knowledge_base(self, kb_id: int, name: str, description: str) -> Dict[str, Any]:
        """
        更新知识库信息
        
        Args:
            kb_id: 知识库ID
            name: 新名称
            description: 新描述
            
        Returns:
            更新结果
        """
        try:
            # 加载现有知识库
            knowledge_bases = self.load_knowledge_bases()
            
            # 查找要更新的知识库
            kb_to_update = None
            kb_index = -1
            for i, kb in enumerate(knowledge_bases):
                if kb.get("id") == kb_id:
                    kb_to_update = kb
                    kb_index = i
                    break
            
            if not kb_to_update:
                return {
                    "success": False,
                    "message": f"知识库 (ID: {kb_id}) 不存在"
                }
            
            old_name = kb_to_update.get("name")
            
            # 如果名称发生变化，需要重命名目录
            if old_name != name:
                # 检查新名称是否已存在
                if any(kb.get("name") == name and kb.get("id") != kb_id for kb in knowledge_bases):
                    return {
                        "success": False,
                        "message": f"知识库名称 '{name}' 已存在"
                    }
                
                # 重命名目录
                old_dir = self.knowledge_base_dir / old_name
                new_dir = self.knowledge_base_dir / name
                
                if old_dir.exists():
                    old_dir.rename(new_dir)
            
            # 更新知识库信息
            knowledge_bases[kb_index].update({
                "name": name,
                "description": description
            })
            
            # 保存更新后的列表
            if self.save_knowledge_bases(knowledge_bases):
                return {
                    "success": True,
                    "message": f"知识库更新成功",
                    "data": knowledge_bases[kb_index]
                }
            else:
                return {
                    "success": False,
                    "message": "保存知识库配置失败"
                }
                
        except Exception as e:
            logger.error(f"更新知识库失败: {str(e)}")
            return {
                "success": False,
                "message": f"更新知识库失败: {str(e)}"
            }
    
    def get_knowledge_base_by_id(self, kb_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取知识库信息
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            知识库信息或None
        """
        knowledge_bases = self.load_knowledge_bases()
        for kb in knowledge_bases:
            if kb.get("id") == kb_id:
                return kb
        return None