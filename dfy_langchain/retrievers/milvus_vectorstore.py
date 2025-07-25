import warnings

from langchain.vectorstores import VectorStore
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import VectorStoreRetriever

from .base import BaseRetrieverService

from langchain.docstore.document import Document
from langchain_core.callbacks.manager import (
        AsyncCallbackManagerForRetrieverRun,
        CallbackManagerForRetrieverRun
)

from typing import List

class MilvusRetriever(VectorStoreRetriever):
    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        if self.search_type == "similarity":
            docs = self.vectorstore.similarity_search(query, **self.search_kwargs)
        elif self.search_type == "similarity_score_threshold":
            docs_and_similarities = self.vectorstore.similarity_search_with_score(query, **self.search_kwargs)
            score_threshold = self.search_kwargs.get("score_threshold", None)
            
            if any(
                similarity < 0.0 or similarity > 1.0
                for _, similarity in docs_and_similarities
            ):
                warnings.warn(
                    "Relevance scores must be between"
                    f" 0 and 1, got {docs_and_similarities}"
                )

            if score_threshold is not None:  # can be 0, but not None
                docs_and_similarities = [
                doc
                for doc, similarity in docs_and_similarities
                if similarity >= score_threshold
            ]
            if len(docs_and_similarities) == 0:
                warnings.warn(
                    "No relevant docs were retrieved using the relevance score"
                    f" threshold {score_threshold}"
                )
            return docs_and_similarities
        elif self.search_type == "mmr":
            docs = self.vectorstore.max_marginal_relevance_search(
                query, **self.search_kwargs
            )
        else:
            raise ValueError(f"search_type of {self.search_type} not allowed.")
        return docs

    async def _aget_relevant_documents(
        self, query: str, *, run_manager: AsyncCallbackManagerForRetrieverRun
    ) -> List[Document]:
        if self.search_type == "similarity":
            docs = await self.vectorstore.asimilarity_search(
                query, **self.search_kwargs
            )
        elif self.search_type == "similarity_score_threshold":
            docs_and_similarities = (
                await self.vectorstore.asimilarity_search_with_score(query, **self.search_kwargs)
            )
            score_threshold = self.search_kwargs.get("score_threshold", None)
            
            if any(
                similarity < 0.0 or similarity > 1.0
                for _, similarity in docs_and_similarities
            ):
                warnings.warn(
                    "Relevance scores must be between"
                    f" 0 and 1, got {docs_and_similarities}"
                )

            if score_threshold is not None:  # can be 0, but not None
                docs_and_similarities = [
                (doc, similarity)
                for doc, similarity in docs_and_similarities
                if similarity >= score_threshold
            ]
            if len(docs_and_similarities) == 0:
                warnings.warn(
                    "No relevant docs were retrieved using the relevance score"
                    f" threshold {score_threshold}"
                )
            return docs_and_similarities
        elif self.search_type == "mmr":
            docs = await self.vectorstore.amax_marginal_relevance_search(
                query, **self.search_kwargs
            )
        else:
            raise ValueError(f"search_type of {self.search_type} not allowed.")
        return docs 

class MilvusVectorstoreRetrieverService(BaseRetrieverService):
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
        score_threshold: float,
    ):
        retriever = MilvusRetriever(vectorstore=vectorstore, 
                                    search_type="similarity_score_threshold",
                                    search_kwargs={"score_threshold": score_threshold, "k": top_k}
                                    )
        
        return MilvusVectorstoreRetrieverService(retriever=retriever, top_k=top_k)

    def get_relevant_documents(self, query: str):
        return self.retriever.get_relevant_documents(query)[: self.top_k]

    def get_relevant_documents_with_scores(self, query: str):
        """获取带分数的相关文档"""
        if hasattr(self.retriever, 'get_relevant_documents_with_scores'):
            return self.retriever.get_relevant_documents_with_scores(query)[: self.top_k]
        elif hasattr(self.retriever.vectorstore, 'similarity_search_with_score'):
            # 如果检索器没有带分数的方法，直接使用向量存储的方法
            return self.retriever.vectorstore.similarity_search_with_score(
                query, k=self.top_k, **self.retriever.search_kwargs
            )
        else:
            # 如果都没有，返回不带分数的结果，分数设为0.5
            docs = self.get_relevant_documents(query)
            return [(doc, 0.5) for doc in docs]