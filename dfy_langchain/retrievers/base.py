from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import List, Tuple, Optional

from langchain.schema import Document
from langchain.vectorstores import VectorStore


class BaseRetrieverService(metaclass=ABCMeta):
    """基础检索器服务抽象类
    
    提供检索器的基础接口和通用功能。
    """
    
    def __init__(self, **kwargs):
        self.do_init(**kwargs)

    @abstractmethod
    def do_init(self, **kwargs):
        """初始化检索器
        
        Args:
            **kwargs: 初始化参数
        """
        pass

    @classmethod
    @abstractmethod
    def from_vectorstore(
        cls,
        vectorstore: VectorStore,
        top_k: int = 10,
        score_threshold: float = 0.0,
        **kwargs
    ) -> 'BaseRetrieverService':
        """从向量存储创建检索器
        
        Args:
            vectorstore: 向量存储
            top_k: 返回文档数量
            score_threshold: 分数阈值
            **kwargs: 其他参数
            
        Returns:
            检索器实例
        """
        pass

    @abstractmethod
    def get_relevant_documents(self, query: str) -> List[Document]:
        """获取相关文档
        
        Args:
            query: 查询字符串
            
        Returns:
            相关文档列表
        """
        pass

    def get_relevant_documents_with_scores(self, query: str) -> List[Tuple[Document, float]]:
        """获取带分数的相关文档
        
        Args:
            query: 查询字符串
            
        Returns:
            (文档, 分数) 元组列表
        """
        # 默认实现：返回不带分数的结果，分数设为0.5
        docs = self.get_relevant_documents(query)
        return [(doc, 0.5) for doc in docs]


# 为了向后兼容，提供 BaseRetriever 别名
BaseRetriever = BaseRetrieverService