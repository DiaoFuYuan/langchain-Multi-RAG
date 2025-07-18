from __future__ import annotations


from langchain.vectorstores import VectorStore
from langchain_core.retrievers import BaseRetriever

from ..base import BaseRetrieverService


class VectorstoreRetrieverService(BaseRetrieverService):
    def do_init(
        self,
        retriever: BaseRetriever = None,
        top_k: int = 5,
    ):
        self.vs = None
        self.top_k = top_k
        self.retriever = retriever

    @staticmethod
    def from_vectorstore(
        vectorstore: VectorStore,
        top_k: int,
        score_threshold: int | float,
    ):
        retriever = vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"score_threshold": score_threshold, "k": top_k},
        )
        return VectorstoreRetrieverService(retriever=retriever, top_k=top_k)

    def get_relevant_documents(self, query: str):
        return self.retriever.invoke(query)[: self.top_k]

    def get_relevant_documents_with_scores(self, query: str):
        """获取带分数的相关文档"""
        if hasattr(self.retriever, 'get_relevant_documents_with_scores'):
            return self.retriever.get_relevant_documents_with_scores(query)[: self.top_k]
        elif hasattr(self.retriever.vectorstore, 'similarity_search_with_score'):
            # 如果检索器没有带分数的方法，直接使用向量存储的方法
            # 避免k参数重复传递
            search_kwargs = self.retriever.search_kwargs.copy()
            search_kwargs['k'] = self.top_k  # 确保使用正确的top_k值
            return self.retriever.vectorstore.similarity_search_with_score(
                query, **search_kwargs
            )
        else:
            # 如果都没有，返回不带分数的结果，分数设为0.5
            docs = self.get_relevant_documents(query)
            return [(doc, 0.5) for doc in docs]