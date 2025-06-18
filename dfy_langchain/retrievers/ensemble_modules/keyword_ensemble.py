from __future__ import annotations

import jieba
import jieba.posseg as pseg
import re
from ..utils.enhanced_tokenizer import get_enhanced_tokenizer
from langchain.retrievers import EnsembleRetriever
from langchain.vectorstores import VectorStore
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from ..base import BaseRetrieverService
from ..utils.relevance_ranking import RelevanceRanker


class KeywordEnsembleRetrieverService(BaseRetrieverService):
    """
    关键词匹配预筛选 + 组合检索的检索器服务
    
    流程：
    1. 使用jieba分词对查询进行处理，提取关键词
    2. 使用关键词在文档中进行匹配，筛选出包含关键词的文档
    3. 对筛选出的文档进行向量检索和BM25检索，并组合结果
    4. 增强返回结果，添加上下文信息
    5. 使用相关性排序对结果进行重新排序
    """
    
    def do_init(
        self,
        retriever: BaseRetriever = None,
        vectorstore: VectorStore = None,
        top_k: int = 5,
        keyword_match_threshold: int = 1,  # 至少包含多少个关键词才算匹配
        context_window: int = 50,  # 上下文窗口大小（字符数）
        enable_ranking: bool = True,  # 是否启用相关性排序
        weight_keyword_freq: float = 0.4,  # 关键词频率权重
        weight_keyword_pos: float = 0.3,  # 关键词位置权重
        weight_keyword_coverage: float = 0.3,  # 关键词覆盖度权重
    ):
        self.vs = vectorstore
        self.top_k = top_k
        self.retriever = retriever
        self.keyword_match_threshold = keyword_match_threshold
        self.context_window = context_window
        self.enable_ranking = enable_ranking
        self.all_docs = list(vectorstore.docstore._dict.values()) if vectorstore else []
        # 创建文档ID到原始文档的映射，用于后续获取上下文
        self.doc_id_map = {doc.metadata.get('source', ''): doc for doc in self.all_docs}
        # 创建相关性排序器
        self.ranker = RelevanceRanker(
            weight_keyword_freq=weight_keyword_freq,
            weight_keyword_pos=weight_keyword_pos,
            weight_keyword_coverage=weight_keyword_coverage
        )
    
    @staticmethod
    def from_vectorstore(
        vectorstore: VectorStore,
        top_k: int,
        score_threshold: int | float,
        keyword_match_threshold: int = 1,
        context_window: int = 100,
        enable_ranking: bool = True,
        weight_keyword_freq: float = 0.4,
        weight_keyword_pos: float = 0.3,
        weight_keyword_coverage: float = 0.3,
    ):
        # 创建FAISS检索器
        faiss_retriever = vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"score_threshold": score_threshold, "k": top_k},
        )
        
        # 获取所有文档
        all_docs = list(vectorstore.docstore._dict.values())
        
        # 创建BM25检索器
        bm25_retriever = BM25Retriever.from_documents(
            all_docs,
            preprocess_func=jieba.lcut_for_search,
        )
        bm25_retriever.k = top_k
        
        # 创建组合检索器
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, faiss_retriever], weights=[0.5, 0.5]
        )
        
        return KeywordEnsembleRetrieverService(
            retriever=ensemble_retriever, 
            vectorstore=vectorstore,
            top_k=top_k,
            keyword_match_threshold=keyword_match_threshold,
            context_window=context_window,
            enable_ranking=enable_ranking,
            weight_keyword_freq=weight_keyword_freq,
            weight_keyword_pos=weight_keyword_pos,
            weight_keyword_coverage=weight_keyword_coverage
        )
    
    def _extract_keywords(self, query: str, top_n: int = 5):
        """使用增强分词器提取关键词"""
        try:
            # 获取增强分词器
            tokenizer = get_enhanced_tokenizer()
            
            # 提取关键词（只返回词汇，不包含权重）
            keyword_tuples = tokenizer.extract_keywords(query, top_k=20, min_word_len=2)
            keywords = [word for word, pos, weight in keyword_tuples]
            
            # 添加专门实体
            person_names = tokenizer.get_person_names(query)
            organizations = tokenizer.get_organizations(query)
            locations = tokenizer.get_locations(query)
            
            # 合并所有关键词
            all_keywords = keywords + person_names + organizations + locations
            
            # 去重并保持顺序
            unique_keywords = []
            seen = set()
            for keyword in all_keywords:
                if keyword not in seen:
                    unique_keywords.append(keyword)
                    seen.add(keyword)
            
            print(f"🎯 提取的关键词: {unique_keywords}")
            final_keywords = unique_keywords[:top_n] if top_n and unique_keywords else unique_keywords
            return final_keywords if final_keywords else [query]
            
        except Exception as e:
            print(f"关键词提取失败: {e}")
            # 回退到原始jieba分词
            words = jieba.lcut_for_search(query)
            keywords = [word for word in words if len(word) > 1]
            return keywords[:top_n] if top_n else keywords
    
    def _filter_docs_by_keywords(self, keywords, docs, threshold=1):
        """根据关键词筛选文档"""
        if not keywords:
            return docs
        
        filtered_docs = []
        for doc in docs:
            content = doc.page_content.lower()
            # 计算文档中包含的关键词数量
            match_count = sum(1 for keyword in keywords if keyword.lower() in content)
            if match_count >= threshold:
                filtered_docs.append(doc)
        
        return filtered_docs
    
    def _enrich_context(self, doc: Document, keywords: list) -> Document:
        """
        增强文档上下文，添加关键词周围的上下文信息
        """
        # 如果context_window为0，则禁用上下文增强，直接返回原文档
        if self.context_window <= 0:
            return doc
            
        source = doc.metadata.get('source', '')
        content = doc.page_content
        
        # 如果内容已经很短，直接返回原文档
        if len(content) <= self.context_window * 3:
            return doc
        
        # 查找所有关键词在文本中的位置
        positions = []
        for keyword in keywords:
            # 找到所有关键词出现的位置
            for match in re.finditer(re.escape(keyword.lower()), content.lower()):
                positions.append((match.start(), match.end()))
        
        if not positions:
            return doc
        
        # 按位置排序
        positions.sort()
        
        # 合并重叠或接近的位置
        merged_positions = []
        current_start, current_end = positions[0]
        
        for start, end in positions[1:]:
            # 如果当前位置与上一个位置的距离小于上下文窗口的2倍，合并它们
            if start <= current_end + self.context_window * 2:
                current_end = max(current_end, end)
            else:
                merged_positions.append((current_start, current_end))
                current_start, current_end = start, end
        
        merged_positions.append((current_start, current_end))
        
        # 为每个合并后的位置提取上下文
        contexts = []
        for start, end in merged_positions:
            # 扩展上下文窗口
            context_start = max(0, start - self.context_window)
            context_end = min(len(content), end + self.context_window)
            
            # 提取上下文
            context = content[context_start:context_end]
            
            # 添加省略号表示上下文被截断
            prefix = "..." if context_start > 0 else ""
            suffix = "..." if context_end < len(content) else ""
            
            contexts.append(f"{prefix}{context}{suffix}")
        
        # 合并所有上下文
        enriched_content = "\n...\n".join(contexts)
        
        # 创建新的文档，包含原始元数据和增强的内容
        enriched_doc = Document(
            page_content=enriched_content,
            metadata={
                **doc.metadata,
                "original_content": content[:100] + "..." if len(content) > 100 else content,
                "context_enriched": True
            }
        )
        
        return enriched_doc
    
    def get_relevant_documents(self, query: str):
        """
        先使用关键词匹配筛选文档，然后对筛选出的文档进行组合检索，最后增强上下文并进行相关性排序
        """
        # 提取关键词
        keywords = self._extract_keywords(query)
        
        if not keywords:
            # 如果没有提取到关键词，直接使用组合检索
            results = self.retriever.get_relevant_documents(query)[:self.top_k]
            
            # 为结果增加上下文（如果启用）
            if self.context_window > 0:
                enriched_results = [self._enrich_context(doc, [query]) for doc in results]
            else:
                enriched_results = results
            
            # 如果启用了相关性排序，则对结果进行排序
            if self.enable_ranking:
                return self.ranker.rank_documents(enriched_results, query)
            else:
                return enriched_results
        
        # 使用关键词筛选文档
        filtered_docs = self._filter_docs_by_keywords(
            keywords, 
            self.all_docs, 
            self.keyword_match_threshold
        )
        
        if not filtered_docs:
            # 如果没有筛选出文档，直接使用组合检索
            results = self.retriever.get_relevant_documents(query)[:self.top_k]
            
            # 为结果增加上下文（如果启用）
            if self.context_window > 0:
                enriched_results = [self._enrich_context(doc, [query]) for doc in results]
            else:
                enriched_results = results
            
            # 如果启用了相关性排序，则对结果进行排序
            if self.enable_ranking:
                return self.ranker.rank_documents(enriched_results, query)
            else:
                return enriched_results
        
        # 创建一个临时的向量存储，只包含筛选出的文档
        filtered_vectorstore = self.vs.from_documents(
            filtered_docs,
            self.vs.embedding_function,
        )
        
        # 对筛选出的文档创建检索器
        filtered_faiss_retriever = filtered_vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"score_threshold": 0.0, "k": self.top_k * 2},  # 设置较低的阈值，确保能够返回结果
        )
        
        # 创建BM25检索器
        filtered_bm25_retriever = BM25Retriever.from_documents(
            filtered_docs,
            preprocess_func=jieba.lcut_for_search,
        )
        filtered_bm25_retriever.k = self.top_k * 2
        
        # 创建组合检索器
        filtered_ensemble_retriever = EnsembleRetriever(
            retrievers=[filtered_bm25_retriever, filtered_faiss_retriever], 
            weights=[0.5, 0.5]
        )
        
        # 使用组合检索器进行检索
        results = filtered_ensemble_retriever.get_relevant_documents(query)
        
        # 为每个结果增强上下文（如果启用）
        if self.context_window > 0:
            enriched_results = [self._enrich_context(doc, keywords) for doc in results[:self.top_k * 2]]
        else:
            enriched_results = results[:self.top_k * 2]
        
        # 如果启用了相关性排序，则对结果进行排序
        if self.enable_ranking:
            ranked_results = self.ranker.rank_documents(enriched_results, query)
            return ranked_results[:self.top_k]
        else:
            return enriched_results[:self.top_k]
    
    def get_relevant_documents_with_scores(self, query: str):
        """
        获取相关文档及其相关性分数
        """
        # 提取关键词
        keywords = self._extract_keywords(query)
        
        if not keywords:
            # 如果没有提取到关键词，直接使用组合检索
            results = self.retriever.get_relevant_documents(query)[:self.top_k]
            
            # 为结果增加上下文（如果启用）
            if self.context_window > 0:
                enriched_results = [self._enrich_context(doc, [query]) for doc in results]
            else:
                enriched_results = results
            
            # 计算相关性分数
            return self.ranker.rank_documents_with_scores(enriched_results, query)
        
        # 使用关键词筛选文档
        filtered_docs = self._filter_docs_by_keywords(
            keywords, 
            self.all_docs, 
            self.keyword_match_threshold
        )
        
        if not filtered_docs:
            # 如果没有筛选出文档，直接使用组合检索
            results = self.retriever.get_relevant_documents(query)[:self.top_k]
            
            # 为结果增加上下文（如果启用）
            if self.context_window > 0:
                enriched_results = [self._enrich_context(doc, [query]) for doc in results]
            else:
                enriched_results = results
            
            # 计算相关性分数
            return self.ranker.rank_documents_with_scores(enriched_results, query)
        
        # 创建一个临时的向量存储，只包含筛选出的文档
        filtered_vectorstore = self.vs.from_documents(
            filtered_docs,
            self.vs.embedding_function,
        )
        
        # 对筛选出的文档创建检索器
        filtered_faiss_retriever = filtered_vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"score_threshold": 0.0, "k": self.top_k * 2},  # 设置较低的阈值，确保能够返回结果
        )
        
        # 创建BM25检索器
        filtered_bm25_retriever = BM25Retriever.from_documents(
            filtered_docs,
            preprocess_func=jieba.lcut_for_search,
        )
        filtered_bm25_retriever.k = self.top_k * 2
        
        # 创建组合检索器
        filtered_ensemble_retriever = EnsembleRetriever(
            retrievers=[filtered_bm25_retriever, filtered_faiss_retriever], 
            weights=[0.5, 0.5]
        )
        
        # 使用组合检索器进行检索
        results = filtered_ensemble_retriever.invoke(query)
        
        # 为每个结果增强上下文（如果启用）
        if self.context_window > 0:
            enriched_results = [self._enrich_context(doc, keywords) for doc in results[:self.top_k * 2]]
        else:
            enriched_results = results[:self.top_k * 2]
        
        # 计算相关性分数并排序
        scored_results = self.ranker.rank_documents_with_scores(enriched_results, query)
        
        return scored_results[:self.top_k]