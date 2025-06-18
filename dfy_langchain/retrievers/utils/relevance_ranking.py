from __future__ import annotations

import jieba
import jieba.posseg as pseg
import numpy as np
from typing import List, Dict, Any, Tuple
from langchain_core.documents import Document
from .enhanced_tokenizer import get_enhanced_tokenizer


class RelevanceRanker:
    """
    文档相关性排序器
    
    提供多种排序策略：
    1. 关键词频率排序：根据关键词在文档中出现的频率排序
    2. 关键词位置排序：根据关键词在文档中的位置排序（越靠前越相关）
    3. 关键词覆盖度排序：根据文档覆盖查询关键词的比例排序
    4. 组合排序：综合考虑以上因素进行排序
    """
    
    def __init__(self, 
                 weight_keyword_freq: float = 0.4,
                 weight_keyword_pos: float = 0.3, 
                 weight_keyword_coverage: float = 0.3):
        """
        初始化排序器
        
        参数:
            weight_keyword_freq: 关键词频率权重
            weight_keyword_pos: 关键词位置权重
            weight_keyword_coverage: 关键词覆盖度权重
        """
        self.weight_keyword_freq = weight_keyword_freq
        self.weight_keyword_pos = weight_keyword_pos
        self.weight_keyword_coverage = weight_keyword_coverage
    
    def rank_by_keyword_frequency(self, query: str, docs: List[Document]) -> List[Document]:
        """根据关键词频率排序（使用增强分词器）"""
        try:
            # 使用增强分词器提取查询关键词
            tokenizer = get_enhanced_tokenizer()
            keyword_tuples = tokenizer.extract_keywords(query, top_k=20, min_word_len=2)
            
            # 构建加权关键词字典
            query_keywords = {}
            for word, pos, weight in keyword_tuples:
                query_keywords[word.lower()] = weight
            
            # 添加实体关键词
            person_names = tokenizer.get_person_names(query)
            organizations = tokenizer.get_organizations(query)
            locations = tokenizer.get_locations(query)
            
            # 实体关键词给予更高权重
            for entity in person_names + organizations + locations:
                query_keywords[entity.lower()] = query_keywords.get(entity.lower(), 0) + 3.0
            
            print(f"🔍 排序关键词: {list(query_keywords.keys())}")
            
            # 计算每个文档的加权关键词频率得分
            doc_scores = []
            for doc in docs:
                content = doc.page_content.lower()
                score = 0
                
                for keyword, weight in query_keywords.items():
                    # 计算关键词在文档中的出现次数
                    count = content.count(keyword)
                    # 加权计算得分
                    score += count * weight
                
                doc_scores.append((doc, score))
            
            # 按得分排序
            doc_scores.sort(key=lambda x: x[1], reverse=True)
            
            # 打印排序结果统计
            if doc_scores:
                print(f"📊 排序结果: 最高分={doc_scores[0][1]:.2f}, 最低分={doc_scores[-1][1]:.2f}")
            
            return [doc for doc, score in doc_scores]
            
        except Exception as e:
            print(f"关键词频率排序失败: {e}")
            # 回退到原始方法
            query_words = set(jieba.lcut(query))
            doc_scores = []
            for doc in docs:
                content = doc.page_content.lower()
                score = sum(content.count(word) for word in query_words)
                doc_scores.append((doc, score))
            
            doc_scores.sort(key=lambda x: x[1], reverse=True)
            return [doc for doc, score in doc_scores]
    
    def rank_by_keyword_position(self, docs: List[Document], keywords: List[str]) -> List[Document]:
        """
        根据关键词在文档中的位置排序（关键词越靠前，文档越相关）
        
        参数:
            docs: 待排序的文档列表
            keywords: 关键词列表
            
        返回:
            按关键词位置排序后的文档列表
        """
        if not keywords or not docs:
            return docs
        
        # 计算每个文档中关键词的最小位置（越小越靠前）
        doc_scores = []
        for doc in docs:
            content = doc.page_content.lower()
            
            # 找出所有关键词在文档中第一次出现的位置
            positions = []
            for keyword in keywords:
                pos = content.find(keyword.lower())
                if pos != -1:  # 如果找到了关键词
                    positions.append(pos)
            
            # 如果没有找到任何关键词，则位置设为文档长度（最大值）
            min_pos = min(positions) if positions else len(content)
            
            # 计算位置分数：越靠前分数越高（使用指数衰减）
            position_score = np.exp(-min_pos / max(1, len(content)))
            doc_scores.append((doc, position_score))
        
        # 按分数降序排序
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 返回排序后的文档列表
        return [doc for doc, _ in doc_scores]
    
    def rank_by_keyword_coverage(self, docs: List[Document], keywords: List[str]) -> List[Document]:
        """
        根据文档覆盖查询关键词的比例排序
        
        参数:
            docs: 待排序的文档列表
            keywords: 关键词列表
            
        返回:
            按关键词覆盖度排序后的文档列表
        """
        if not keywords or not docs:
            return docs
        
        # 计算每个文档覆盖的关键词比例
        doc_scores = []
        for doc in docs:
            content = doc.page_content.lower()
            
            # 计算文档中包含的关键词数量
            covered_keywords = sum(1 for keyword in keywords if keyword.lower() in content)
            
            # 计算覆盖率
            coverage_score = covered_keywords / max(1, len(keywords))
            doc_scores.append((doc, coverage_score))
        
        # 按分数降序排序
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 返回排序后的文档列表
        return [doc for doc, _ in doc_scores]
    
    def rank_documents(self, docs: List[Document], query: str) -> List[Document]:
        """
        综合多种排序策略对文档进行排序（使用增强分词器）
        
        参数:
            docs: 待排序的文档列表
            query: 查询字符串
            
        返回:
            排序后的文档列表
        """
        if not docs:
            return docs
        
        try:
            # 使用增强分词器提取关键词
            tokenizer = get_enhanced_tokenizer()
            keyword_tuples = tokenizer.extract_keywords(query, top_k=15, min_word_len=2)
            
            # 构建加权关键词字典
            weighted_keywords = {}
            for word, pos, weight in keyword_tuples:
                weighted_keywords[word.lower()] = weight
            
            # 添加实体关键词（给予更高权重）
            person_names = tokenizer.get_person_names(query)
            organizations = tokenizer.get_organizations(query)
            locations = tokenizer.get_locations(query)
            
            for entity in person_names + organizations + locations:
                weighted_keywords[entity.lower()] = weighted_keywords.get(entity.lower(), 0) + 4.0
            
            print(f"🎯 综合排序关键词: {list(weighted_keywords.keys())}")
            
            # 计算各种排序分数
            doc_scores = []
            for doc in docs:
                content = doc.page_content.lower()
                
                # 1. 加权关键词频率分数
                freq_score = 0
                total_weight = sum(weighted_keywords.values())
                for keyword, weight in weighted_keywords.items():
                    count = content.count(keyword)
                    freq_score += (count * weight) / max(1, len(content))
                freq_score = freq_score / max(1, total_weight) if total_weight > 0 else 0
                
                # 2. 关键词位置分数（考虑权重）
                weighted_positions = []
                for keyword, weight in weighted_keywords.items():
                    pos = content.find(keyword)
                    if pos != -1:
                        # 位置分数乘以权重
                        position_value = np.exp(-pos / max(1, len(content))) * weight
                        weighted_positions.append(position_value)
                
                position_score = sum(weighted_positions) / max(1, total_weight) if weighted_positions and total_weight > 0 else 0
                
                # 3. 关键词覆盖度分数
                covered_keywords = sum(weight for keyword, weight in weighted_keywords.items() if keyword in content)
                coverage_score = covered_keywords / max(1, total_weight) if total_weight > 0 else 0
                
                # 4. 组合分数
                combined_score = (
                    self.weight_keyword_freq * freq_score +
                    self.weight_keyword_pos * position_score +
                    self.weight_keyword_coverage * coverage_score
                )
                
                # 存储文档和分数
                doc_scores.append((doc, combined_score))
            
            # 按组合分数降序排序
            doc_scores.sort(key=lambda x: x[1], reverse=True)
            
            # 打印排序统计
            if doc_scores:
                print(f"📈 综合排序结果: 最高分={doc_scores[0][1]:.4f}, 最低分={doc_scores[-1][1]:.4f}")
            
            # 返回排序后的文档列表
            return [doc for doc, _ in doc_scores]
            
        except Exception as e:
            print(f"综合排序失败: {e}")
            # 回退到原始方法
            keywords = [word for word in jieba.lcut_for_search(query) if len(word) > 1]
            if not keywords:
                keywords = [query]
            
            doc_scores = []
            for doc in docs:
                content = doc.page_content.lower()
                
                freq_count = sum(content.count(keyword.lower()) for keyword in keywords)
                freq_score = freq_count / max(1, len(content))
                
                positions = []
                for keyword in keywords:
                    pos = content.find(keyword.lower())
                    if pos != -1:
                        positions.append(pos)
                min_pos = min(positions) if positions else len(content)
                position_score = np.exp(-min_pos / max(1, len(content)))
                
                covered_keywords = sum(1 for keyword in keywords if keyword.lower() in content)
                coverage_score = covered_keywords / max(1, len(keywords))
                
                combined_score = (
                    self.weight_keyword_freq * freq_score +
                    self.weight_keyword_pos * position_score +
                    self.weight_keyword_coverage * coverage_score
                )
                
                doc_scores.append((doc, combined_score))
            
            doc_scores.sort(key=lambda x: x[1], reverse=True)
            return [doc for doc, _ in doc_scores]
    
    def rank_documents_with_scores(self, docs: List[Document], query: str) -> List[Tuple[Document, Dict[str, float]]]:
        """
        综合多种排序策略对文档进行排序，并返回详细的分数信息
        
        参数:
            docs: 待排序的文档列表
            query: 查询字符串
            
        返回:
            排序后的文档列表及其详细分数
        """
        if not docs:
            return []
        
        # 提取查询中的关键词
        keywords = [word for word in jieba.lcut_for_search(query) if len(word) > 1]
        if not keywords:
            keywords = [query]  # 如果没有提取到关键词，则使用整个查询作为关键词
        
        # 计算各种排序分数
        doc_scores = []
        for doc in docs:
            content = doc.page_content.lower()
            
            # 1. 关键词频率分数
            freq_count = sum(content.count(keyword.lower()) for keyword in keywords)
            freq_score = freq_count / max(1, len(content))
            
            # 2. 关键词位置分数
            positions = []
            for keyword in keywords:
                pos = content.find(keyword.lower())
                if pos != -1:
                    positions.append(pos)
            min_pos = min(positions) if positions else len(content)
            position_score = np.exp(-min_pos / max(1, len(content)))
            
            # 3. 关键词覆盖度分数
            covered_keywords = sum(1 for keyword in keywords if keyword.lower() in content)
            coverage_score = covered_keywords / max(1, len(keywords))
            
            # 4. 组合分数
            combined_score = (
                self.weight_keyword_freq * freq_score +
                self.weight_keyword_pos * position_score +
                self.weight_keyword_coverage * coverage_score
            )
            
            # 存储文档和详细分数
            scores = {
                "frequency_score": freq_score,
                "position_score": position_score,
                "coverage_score": coverage_score,
                "combined_score": combined_score
            }
            doc_scores.append((doc, scores))
        
        # 按组合分数降序排序
        doc_scores.sort(key=lambda x: x[1]["combined_score"], reverse=True)
        
        return doc_scores