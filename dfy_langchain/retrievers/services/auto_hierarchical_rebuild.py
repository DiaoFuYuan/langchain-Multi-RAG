#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动分层索引重建服务

在文件上传后自动检查知识库规模，如果满足条件则自动重建分层索引。
确保新文档能够被分层检索发现。
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoHierarchicalRebuildService:
    """自动分层索引重建服务"""
    
    def __init__(self):
        """初始化服务"""
        self.threshold_docs = 0    # 分层索引阈值 (设为0，所有知识库都自动构建分层索引)
        self.min_groups = 0        # 最小文档组数 (设为0，所有知识库都可以构建)
        
        # 确保可以导入RAG相关模块
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        if parent_dir not in sys.path:
            sys.path.append(parent_dir)
    
    def should_rebuild_hierarchical_index(self, kb_name: str) -> Dict[str, Any]:
        """
        检查是否需要重建分层索引
        
        Args:
            kb_name: 知识库名称
            
        Returns:
            包含检查结果的字典
        """
        try:
            # 加载知识库向量存储
            vectorstore = self._load_vectorstore(kb_name)
            if not vectorstore:
                return {
                    "should_rebuild": False,
                    "reason": "无法加载知识库向量存储",
                    "doc_count": 0,
                    "group_count": 0
                }
            
            # 分析文档规模和结构
            analysis = self._analyze_knowledge_base(vectorstore)
            
            # 检查是否满足分层索引条件（只要有文档就可以构建分层索引）
            should_rebuild = (
                analysis["doc_count"] > 0 and
                analysis["doc_count"] >= self.threshold_docs and 
                analysis["group_count"] >= self.min_groups
            )
            
            # 检查当前分层索引是否存在且完整
            hierarchical_exists = self._check_hierarchical_index_exists(kb_name)
            
            # 检查是否需要更新（新文档数量）
            needs_update = self._check_needs_update(kb_name, analysis["doc_count"])
            
            return {
                "should_rebuild": should_rebuild,
                "reason": self._get_rebuild_reason(should_rebuild, hierarchical_exists, needs_update, analysis),
                "doc_count": analysis["doc_count"],
                "group_count": analysis["group_count"],
                "hierarchical_exists": hierarchical_exists,
                "needs_update": needs_update,
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"检查分层索引重建需求失败: {str(e)}")
            return {
                "should_rebuild": False,
                "reason": f"检查失败: {str(e)}",
                "doc_count": 0,
                "group_count": 0
            }
    
    def auto_rebuild_if_needed(self, kb_name: str) -> Dict[str, Any]:
        """
        自动检查并重建分层索引（如果需要）
        
        Args:
            kb_name: 知识库名称
            
        Returns:
            重建结果
        """
        try:
            # 检查是否需要重建
            check_result = self.should_rebuild_hierarchical_index(kb_name)
            
            if not check_result["should_rebuild"]:
                logger.info(f"知识库 {kb_name} 不需要重建分层索引: {check_result['reason']}")
                return {
                    "success": True,
                    "action": "no_rebuild_needed",
                    "message": check_result["reason"],
                    "check_result": check_result
                }
            
            # 执行重建
            logger.info(f"开始为知识库 {kb_name} 重建分层索引...")
            rebuild_result = self._rebuild_hierarchical_index(kb_name)
            
            if rebuild_result["success"]:
                # 更新重建记录
                self._update_rebuild_record(kb_name, check_result["doc_count"])
                
                logger.info(f"知识库 {kb_name} 分层索引重建成功")
                return {
                    "success": True,
                    "action": "rebuilt",
                    "message": "分层索引重建成功",
                    "check_result": check_result,
                    "rebuild_result": rebuild_result
                }
            else:
                logger.error(f"知识库 {kb_name} 分层索引重建失败: {rebuild_result['message']}")
                return {
                    "success": False,
                    "action": "rebuild_failed",
                    "message": f"分层索引重建失败: {rebuild_result['message']}",
                    "check_result": check_result,
                    "rebuild_result": rebuild_result
                }
                
        except Exception as e:
            logger.error(f"自动重建分层索引失败: {str(e)}")
            return {
                "success": False,
                "action": "error",
                "message": f"自动重建失败: {str(e)}"
            }
    
    def _load_vectorstore(self, kb_name: str):
        """加载知识库向量存储"""
        try:
            from rag_retrievers import KnowledgeBaseManager, RetrieverServiceFactory
            
            factory = RetrieverServiceFactory()
            kb_manager = KnowledgeBaseManager(factory)
            
            # 动态从配置文件获取知识库ID
            kb_id = self._get_kb_id_by_name(kb_name)
            if not kb_id:
                logger.error(f"无法找到知识库 '{kb_name}' 的ID")
                return None
            
            vectorstore = kb_manager.load_faiss_vectorstore(str(kb_id))
            
            return vectorstore
            
        except Exception as e:
            logger.error(f"加载向量存储失败: {str(e)}")
            return None
    
    def _get_kb_id_by_name(self, kb_name: str) -> Optional[int]:
        """根据知识库名称获取ID"""
        try:
            import json
            # 使用绝对路径 - 从dfy_langchain/retrievers/services/向上4级到项目根目录
            base_path = Path(__file__).parent.parent.parent.parent / "data" / "knowledge_base"
            config_file = base_path / "knowledge_bases.json"
            
            logger.info(f"🔍 查找知识库配置文件: {config_file}")
            logger.info(f"🔍 配置文件是否存在: {config_file.exists()}")
            
            if not config_file.exists():
                logger.error(f"知识库配置文件不存在: {config_file}")
                return None
            
            with config_file.open("r", encoding="utf-8") as f:
                config = json.load(f)
            
            for kb in config.get("knowledge_bases", []):
                if kb.get("name") == kb_name:
                    return kb.get("id")
            
            logger.error(f"未找到名称为 '{kb_name}' 的知识库")
            return None
            
        except Exception as e:
            logger.error(f"获取知识库ID失败: {str(e)}")
            return None
    
    def _analyze_knowledge_base(self, vectorstore) -> Dict[str, Any]:
        """分析知识库结构"""
        try:
            doc_count = 0
            doc_groups = {}
            content_lengths = []
            
            if hasattr(vectorstore, 'docstore') and hasattr(vectorstore.docstore, '_dict'):
                docs = vectorstore.docstore._dict.values()
                doc_count = len(docs)
                
                for doc in docs:
                    source = doc.metadata.get('source', 'unknown')
                    if source not in doc_groups:
                        doc_groups[source] = []
                    doc_groups[source].append(doc)
                    content_lengths.append(len(doc.page_content))
            
            # 计算统计信息
            avg_content_length = sum(content_lengths) / len(content_lengths) if content_lengths else 0
            
            return {
                "doc_count": doc_count,
                "group_count": len(doc_groups),
                "avg_content_length": avg_content_length,
                "doc_groups": doc_groups
            }
            
        except Exception as e:
            logger.error(f"分析知识库结构失败: {str(e)}")
            return {
                "doc_count": 0,
                "group_count": 0,
                "avg_content_length": 0,
                "doc_groups": {}
            }
    
    def _check_hierarchical_index_exists(self, kb_name: str) -> bool:
        """检查分层索引是否存在且完整"""
        try:
            # 使用绝对路径
            base_path = Path(__file__).parent.parent.parent / "data" / "knowledge_base"
            hierarchical_path = base_path / kb_name / "hierarchical_vector_store"
            summary_path = hierarchical_path / "summary_vector_store"
            chunk_path = hierarchical_path / "chunk_vector_store"
            
            # 检查必要文件是否存在
            required_files = ["index.faiss", "index.pkl"]
            
            summary_complete = all(
                (summary_path / f).exists() for f in required_files
            ) if summary_path.exists() else False
            
            chunk_complete = all(
                (chunk_path / f).exists() for f in required_files
            ) if chunk_path.exists() else False
            
            return summary_complete and chunk_complete
            
        except Exception as e:
            logger.error(f"检查分层索引存在性失败: {str(e)}")
            return False
    
    def _check_needs_update(self, kb_name: str, current_doc_count: int) -> bool:
        """检查是否需要更新（基于文档数量变化）"""
        try:
            # 读取上次重建记录，使用绝对路径
            base_path = Path(__file__).parent.parent.parent / "data" / "knowledge_base"
            record_file = base_path / kb_name / "hierarchical_rebuild_record.json"
            
            if not record_file.exists():
                return True  # 没有记录，需要构建
            
            with record_file.open("r", encoding="utf-8") as f:
                record = json.load(f)
            
            last_doc_count = record.get("doc_count", 0)
            
            # 如果文档数量变化超过10%，则需要更新
            change_threshold = max(10, last_doc_count * 0.1)
            needs_update = abs(current_doc_count - last_doc_count) >= change_threshold
            
            return needs_update
            
        except Exception as e:
            logger.error(f"检查更新需求失败: {str(e)}")
            return True  # 出错时默认需要更新
    
    def _get_rebuild_reason(self, should_rebuild: bool, hierarchical_exists: bool, 
                           needs_update: bool, analysis: Dict[str, Any]) -> str:
        """获取重建原因说明"""
        if not should_rebuild:
            if analysis["doc_count"] == 0:
                return "知识库中没有文档，无需构建分层索引"
            elif analysis["doc_count"] < self.threshold_docs:
                return f"文档数量({analysis['doc_count']})未达到分层索引阈值({self.threshold_docs})"
            elif analysis["group_count"] < self.min_groups:
                return f"文档组数量({analysis['group_count']})未达到最小要求({self.min_groups})"
            else:
                return "不满足分层索引构建条件"
        
        if not hierarchical_exists:
            return "分层索引不存在，需要创建"
        elif needs_update:
            return "文档数量发生变化，需要更新分层索引"
        else:
            return "分层索引需要重建"
    
    def _rebuild_hierarchical_index(self, kb_name: str) -> Dict[str, Any]:
        """重建分层索引"""
        try:
            start_time = time.time()
            
            # 加载向量存储
            vectorstore = self._load_vectorstore(kb_name)
            if not vectorstore:
                return {
                    "success": False,
                    "message": "无法加载知识库向量存储"
                }
            
            # 获取知识库的嵌入模型配置
            embeddings = self._get_kb_embeddings(kb_name)
            if not embeddings:
                return {
                    "success": False,
                    "message": "无法获取知识库的嵌入模型配置"
                }
            
            # 创建分层索引构建器
            from ..hierarchical_retriever import HierarchicalIndexBuilder
            
            builder = HierarchicalIndexBuilder(
                embeddings=embeddings
            )
            
            # 获取向量存储中的所有文档
            try:
                # 从FAISS向量存储获取所有文档
                all_docs = []
                
                if hasattr(vectorstore, 'docstore') and hasattr(vectorstore.docstore, '_dict'):
                    # FAISS向量存储的正确获取方法
                    doc_dict = vectorstore.docstore._dict
                    all_docs = list(doc_dict.values())
                    logger.info(f"从FAISS向量存储获取到 {len(all_docs)} 个文档")
                    
                    # 调试信息：显示文档的基本信息
                    if all_docs:
                        sample_doc = all_docs[0]
                        logger.info(f"示例文档元数据: {sample_doc.metadata}")
                        logger.info(f"示例文档内容长度: {len(sample_doc.page_content)}")
                    
                elif hasattr(vectorstore, 'similarity_search'):
                    # 备用方法：通过搜索获取文档
                    logger.warning("使用备用方法获取文档")
                    try:
                        # 使用一个通用查询来获取文档
                        all_docs = vectorstore.similarity_search("", k=1000)  # 获取尽可能多的文档
                        logger.info(f"通过搜索获取到 {len(all_docs)} 个文档")
                    except Exception as search_error:
                        logger.error(f"搜索方法也失败: {search_error}")
                        all_docs = []
                else:
                    logger.warning("无法从向量存储获取文档，使用空文档列表")
                    all_docs = []
                
                logger.info(f"最终获取到 {len(all_docs)} 个文档")
                
                # 构建分层索引，使用绝对路径
                base_path = Path(__file__).parent.parent.parent.parent / "data" / "knowledge_base"
                vectorstore_path = str(base_path / kb_name / "vector_store")
                
                summary_vs, chunk_vs = builder.build_hierarchical_index(
                    documents=all_docs,
                    vectorstore_path=vectorstore_path
                )
                
            except Exception as doc_error:
                logger.error(f"获取文档或构建索引失败: {doc_error}")
                raise doc_error
            
            build_time = time.time() - start_time
            
            # 构建输出目录路径
            base_path = Path(__file__).parent.parent.parent.parent / "data" / "knowledge_base"
            output_dir = str(base_path / kb_name / "hierarchical_vector_store")
            
            if summary_vs and chunk_vs:
                return {
                    "success": True,
                    "message": "分层索引重建成功",
                    "build_time": build_time,
                    "output_dir": output_dir
                }
            else:
                return {
                    "success": False,
                    "message": "分层索引构建器返回空结果"
                }
                
        except Exception as e:
            logger.error(f"重建分层索引失败: {str(e)}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"重建失败: {str(e)}"
            }
    
    def _get_kb_embeddings(self, kb_name: str):
        """获取知识库的嵌入模型"""
        try:
            # 获取知识库ID
            kb_id = self._get_kb_id_by_name(kb_name)
            if not kb_id:
                logger.warning(f"未找到知识库 {kb_name} 的ID，使用默认嵌入模型")
                return self._get_default_embeddings()
            
            # 动态导入知识库管理器
            from rag_retrievers import KnowledgeBaseManager, RetrieverServiceFactory
            
            # 创建临时工厂和管理器
            temp_factory = RetrieverServiceFactory()
            temp_manager = KnowledgeBaseManager(temp_factory)
            
            # 获取知识库的嵌入配置
            embedding_config = temp_manager.get_embedding_config_for_kb(str(kb_id))
            
            if embedding_config:
                logger.info(f"使用知识库 {kb_name} 配置的嵌入模型: {embedding_config['model_name']}")
                # 创建使用该配置的工厂
                factory_with_config = RetrieverServiceFactory(embedding_config)
                return factory_with_config.embeddings
            else:
                logger.warning(f"知识库 {kb_name} 未配置嵌入模型，使用默认模型")
                return self._get_default_embeddings()
                
        except Exception as e:
            logger.error(f"获取知识库嵌入模型失败: {e}")
            return self._get_default_embeddings()
    
    def _get_default_embeddings(self):
        """获取默认嵌入模型"""
        try:
            from rag_retrievers import RetrieverServiceFactory
            factory = RetrieverServiceFactory()
            return factory.embeddings
        except Exception as e:
            logger.error(f"获取默认嵌入模型失败: {e}")
            return None
    
    def _update_rebuild_record(self, kb_name: str, doc_count: int):
        """更新重建记录"""
        try:
            record = {
                "kb_name": kb_name,
                "doc_count": doc_count,
                "last_rebuild_time": time.time(),
                "last_rebuild_datetime": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 使用绝对路径
            base_path = Path(__file__).parent.parent.parent / "data" / "knowledge_base"
            record_file = base_path / kb_name / "hierarchical_rebuild_record.json"
            record_file.parent.mkdir(parents=True, exist_ok=True)
            
            with record_file.open("w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
                
            logger.info(f"已更新重建记录: {record_file}")
            
        except Exception as e:
            logger.error(f"更新重建记录失败: {str(e)}")

# 全局服务实例
auto_rebuild_service = AutoHierarchicalRebuildService()

def trigger_auto_rebuild(kb_name: str) -> Dict[str, Any]:
    """
    触发自动重建（供外部调用）
    
    Args:
        kb_name: 知识库名称
        
    Returns:
        重建结果
    """
    return auto_rebuild_service.auto_rebuild_if_needed(kb_name)