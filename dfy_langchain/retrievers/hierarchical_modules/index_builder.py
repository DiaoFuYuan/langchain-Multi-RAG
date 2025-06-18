# -*- coding: utf-8 -*-
"""
分层索引构建器

用于构建分层检索索引，包括摘要索引和文档块索引。
"""

import os
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Any

from langchain.schema import Document
from langchain.vectorstores.base import VectorStore
from langchain_community.vectorstores import FAISS
from langchain.embeddings.base import Embeddings

logger = logging.getLogger(__name__)


class HierarchicalIndexBuilder:
    """分层索引构建器"""
    
    def __init__(self, embeddings: Embeddings, summarizer: Optional[Any] = None):
        """初始化索引构建器
        
        Args:
            embeddings: 嵌入模型
            summarizer: 摘要生成器（可选）
        """
        self.embeddings = embeddings
        self.summarizer = summarizer
        
    def build_hierarchical_index(
        self,
        vectorstore: VectorStore,
        output_dir: str
    ) -> Tuple[VectorStore, VectorStore]:
        """构建分层索引
        
        Args:
            vectorstore: 原始向量存储
            output_dir: 输出目录
            
        Returns:
            (摘要向量存储, 块向量存储) 元组
        """
        try:
            logger.info(f"开始构建分层索引，输出目录: {output_dir}")
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 获取所有文档
            docs = self._get_all_documents(vectorstore)
            logger.info(f"获取到 {len(docs)} 个文档")
            
            # 按文档分组
            doc_groups = self._group_documents_by_source(docs)
            logger.info(f"文档分组完成，共 {len(doc_groups)} 个文档组")
            
            # 构建摘要索引
            summary_docs = self._build_summary_documents(doc_groups)
            summary_vectorstore = self._create_summary_vectorstore(summary_docs, output_dir)
            
            # 构建块索引
            chunk_vectorstore = self._create_chunk_vectorstore(docs, output_dir)
            
            logger.info("分层索引构建完成")
            return summary_vectorstore, chunk_vectorstore
            
        except Exception as e:
            logger.error(f"构建分层索引失败: {e}")
            raise
    
    def _get_all_documents(self, vectorstore: VectorStore) -> List[Document]:
        """获取向量存储中的所有文档"""
        try:
            if hasattr(vectorstore, 'docstore') and hasattr(vectorstore.docstore, '_dict'):
                # FAISS向量存储
                return list(vectorstore.docstore._dict.values())
            else:
                # 其他类型的向量存储，尝试通过搜索获取
                # 这是一个简化的实现，实际可能需要更复杂的逻辑
                return vectorstore.similarity_search("", k=10000)
        except Exception as e:
            logger.warning(f"获取文档失败，使用空列表: {e}")
            return []
    
    def _group_documents_by_source(self, docs: List[Document]) -> dict:
        """按文档源分组"""
        groups = {}
        for doc in docs:
            source = doc.metadata.get('source', 'unknown')
            if source not in groups:
                groups[source] = []
            groups[source].append(doc)
        return groups
    
    def _build_summary_documents(self, doc_groups: dict) -> List[Document]:
        """构建摘要文档"""
        summary_docs = []
        
        for source, docs in doc_groups.items():
            # 合并文档内容
            combined_content = "\n\n".join([doc.page_content for doc in docs])
            
            # 生成摘要（如果有摘要器）
            if self.summarizer:
                try:
                    summary_content = self.summarizer.summarize(combined_content)
                except Exception as e:
                    logger.warning(f"摘要生成失败，使用原始内容: {e}")
                    summary_content = combined_content[:1000] + "..." if len(combined_content) > 1000 else combined_content
            else:
                # 简单截取前1000字符作为摘要
                summary_content = combined_content[:1000] + "..." if len(combined_content) > 1000 else combined_content
            
            # 创建摘要文档
            summary_doc = Document(
                page_content=summary_content,
                metadata={
                    'source': source,
                    'type': 'summary',
                    'chunk_count': len(docs)
                }
            )
            summary_docs.append(summary_doc)
        
        return summary_docs
    
    def _create_summary_vectorstore(self, summary_docs: List[Document], output_dir: str) -> VectorStore:
        """创建摘要向量存储"""
        summary_path = os.path.join(output_dir, "summary_vector_store")
        
        if summary_docs:
            summary_vectorstore = FAISS.from_documents(summary_docs, self.embeddings)
            summary_vectorstore.save_local(summary_path)
            logger.info(f"摘要向量存储已保存到: {summary_path}")
        else:
            # 创建空的向量存储
            summary_vectorstore = FAISS.from_texts(["empty"], self.embeddings)
            summary_vectorstore.save_local(summary_path)
            logger.warning("创建了空的摘要向量存储")
        
        return summary_vectorstore
    
    def _create_chunk_vectorstore(self, docs: List[Document], output_dir: str) -> VectorStore:
        """创建块向量存储"""
        chunk_path = os.path.join(output_dir, "chunk_vector_store")
        
        if docs:
            chunk_vectorstore = FAISS.from_documents(docs, self.embeddings)
            chunk_vectorstore.save_local(chunk_path)
            logger.info(f"块向量存储已保存到: {chunk_path}")
        else:
            # 创建空的向量存储
            chunk_vectorstore = FAISS.from_texts(["empty"], self.embeddings)
            chunk_vectorstore.save_local(chunk_path)
            logger.warning("创建了空的块向量存储")
        
        return chunk_vectorstore