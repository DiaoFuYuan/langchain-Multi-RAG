# -*- coding: utf-8 -*-

import os
import sys
import time
from typing import List, Dict, Any, Optional, Tuple
from langchain.schema import Document
from langchain.vectorstores.base import VectorStore
from langchain.embeddings.base import Embeddings

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base import BaseRetrieverService
from .utils import EnhancedTokenizer

# 导入智能查询分解器
try:
    from .query_decomposer import IntelligentQueryDecomposer, MultiPathRetriever
    QUERY_DECOMPOSER_AVAILABLE = True
    print("✅ 智能查询分解器导入成功")
except ImportError as e:
    print(f"⚠️ 智能查询分解器导入失败: {e}")
    QUERY_DECOMPOSER_AVAILABLE = False

# 导入增强检索模块
try:
    from .hierarchical_modules.keyword_processor import KeywordProcessor
    from .hierarchical_modules.hierarchical_config import HierarchicalConfig
    ENHANCED_MODULES_AVAILABLE = True
    print("✅ 增强检索模块导入成功")
except ImportError as e:
    print(f"⚠️ 增强检索模块导入失败: {e}")
    ENHANCED_MODULES_AVAILABLE = False

class HierarchicalRetrieverService(BaseRetrieverService):
    """分层检索器服务 - 集成智能查询分解和增强检索"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.summary_vectorstore: Optional[VectorStore] = None
        self.chunk_vectorstore: Optional[VectorStore] = None
        self.summary_top_k = kwargs.get('summary_top_k', 5)
        self.chunk_top_k = kwargs.get('chunk_top_k', 10)
        self.summary_score_threshold = kwargs.get('summary_score_threshold', 0.3)
        self.chunk_score_threshold = kwargs.get('chunk_score_threshold', 0.3)
        self.context_window = kwargs.get('context_window', 4000)
        self.enable_summary_fallback = kwargs.get('enable_summary_fallback', True)
        self.enhanced_tokenizer = EnhancedTokenizer()
        
        # 智能查询分解配置
        self.enable_intelligent_decomposition = kwargs.get('enable_intelligent_decomposition', True)
        self.enable_multi_path_retrieval = kwargs.get('enable_multi_path_retrieval', True)
        self.complexity_threshold = kwargs.get('complexity_threshold', 0.3)
        
        # 增强检索配置
        self.enable_enhanced_second_layer = kwargs.get('enable_enhanced_second_layer', True)
        self.enable_entity_matching = kwargs.get('enable_entity_matching', True)
        self.enable_semantic_expansion = kwargs.get('enable_semantic_expansion', True)
        
        # 初始化智能查询分解器
        if QUERY_DECOMPOSER_AVAILABLE and self.enable_intelligent_decomposition:
            try:
                self.query_decomposer = IntelligentQueryDecomposer()
                self.multi_path_retriever = None  # 延迟初始化
                print("✅ 智能查询分解器初始化成功")
            except Exception as e:
                print(f"⚠️ 智能查询分解器初始化失败: {e}")
                self.query_decomposer = None
                self.multi_path_retriever = None
        else:
            self.query_decomposer = None
            self.multi_path_retriever = None
        
        # 初始化增强检索模块
        if ENHANCED_MODULES_AVAILABLE:
            try:
                self.config = HierarchicalConfig.create_accurate_config()
                self.keyword_processor = KeywordProcessor(self.config)
                print("✅ 增强检索模块初始化成功")
            except Exception as e:
                print(f"⚠️ 增强检索模块初始化失败: {e}")
                self.keyword_processor = None
        else:
            self.keyword_processor = None
        
    def do_init(self, **kwargs):
        """初始化检索器"""
        pass
        
    @classmethod
    def from_vectorstore(
        cls,
        vectorstore: VectorStore,
        **kwargs
    ) -> "HierarchicalRetrieverService":
        """从向量存储创建分层检索器"""
        instance = cls(**kwargs)
        
        # 检查是否存在分层结构
        # 优先使用传入的vectorstore_path，否则尝试从vectorstore获取
        vectorstore_path = kwargs.get('vectorstore_path') or getattr(vectorstore, 'persist_directory', None)
        print(f"🔍 检查分层结构，向量存储路径: {vectorstore_path}")
        
        if vectorstore_path:
            # 修正路径检测逻辑：正确构建分层向量存储路径
            # vectorstore_path通常指向 data/knowledge_base/PMS/vector_store
            # 分层结构应该在 data/knowledge_base/PMS/hierarchical_vector_store
            
            # 获取知识库根目录（去掉vector_store部分）
            if vectorstore_path.endswith('vector_store'):
                kb_root_path = os.path.dirname(vectorstore_path)
            else:
                kb_root_path = vectorstore_path
            
            # 构建分层向量存储路径
            hierarchical_base_path = os.path.join(kb_root_path, 'hierarchical_vector_store')
            summary_path = os.path.join(hierarchical_base_path, 'summary_vector_store')
            chunk_path = os.path.join(hierarchical_base_path, 'chunk_vector_store')
            
            print(f"📋 检查摘要向量存储路径: {summary_path}")
            print(f"📄 检查块向量存储路径: {chunk_path}")
            print(f"📋 摘要路径存在: {os.path.exists(summary_path)}")
            print(f"📄 块路径存在: {os.path.exists(chunk_path)}")
            
            if os.path.exists(summary_path) and os.path.exists(chunk_path):
                # 存在分层结构，设置分层向量存储
                try:
                    from langchain_community.vectorstores import FAISS
                    print(f"🔄 加载摘要向量存储: {summary_path}")
                    # 获取嵌入函数，尝试多种属性名
                    embedding_function = None
                    for attr_name in ['_embedding_function', 'embedding_function', 'embeddings']:
                        if hasattr(vectorstore, attr_name):
                            embedding_function = getattr(vectorstore, attr_name)
                            print(f"✅ 找到嵌入函数属性: {attr_name}")
                            break
                    
                    if embedding_function is None:
                        raise AttributeError("无法找到向量存储的嵌入函数")
                    
                    instance.summary_vectorstore = FAISS.load_local(
                        summary_path,
                        embedding_function,
                        allow_dangerous_deserialization=True
                    )
                    print(f"🔄 加载块向量存储: {chunk_path}")
                    instance.chunk_vectorstore = FAISS.load_local(
                        chunk_path,
                        embedding_function,
                        allow_dangerous_deserialization=True
                    )
                    print(f"✅ 成功加载分层向量存储")
                except Exception as e:
                    print(f"❌ 加载分层向量存储失败: {e}")
                    print(f"🔄 回退到普通向量存储")
                    instance.chunk_vectorstore = vectorstore
            else:
                # 不存在分层结构，使用普通向量存储
                print(f"⚠️ 分层结构不完整，使用普通向量存储")
                instance.chunk_vectorstore = vectorstore
        else:
            print(f"⚠️ 无向量存储路径，使用普通向量存储")
            instance.chunk_vectorstore = vectorstore
        
        # 初始化多路检索器
        if QUERY_DECOMPOSER_AVAILABLE and instance.enable_multi_path_retrieval:
            try:
                instance.multi_path_retriever = MultiPathRetriever(instance)
                print("✅ 多路检索器初始化成功")
            except Exception as e:
                print(f"⚠️ 多路检索器初始化失败: {e}")
                instance.multi_path_retriever = None
            
        return instance
    
    def get_relevant_documents(self, query: str) -> List[Document]:
        """获取相关文档 - 集成智能查询分解和增强检索"""
        try:
            print(f"🚀 开始智能检索，查询: '{query}'")
            
            # 1. 智能查询分析和语义理解
            enhanced_query_info = self._analyze_and_enhance_query(query)
            
            # 2. 判断检索策略
            use_intelligent_search = self._should_use_intelligent_search(query, enhanced_query_info)
            
            if use_intelligent_search and self.multi_path_retriever:
                print("🧠 使用智能多路检索")
                return self.multi_path_retriever.multi_path_search(query)
            elif self.summary_vectorstore and self.chunk_vectorstore:
                print("📊 使用增强分层检索")
                return self._enhanced_hierarchical_search(query, enhanced_query_info)
            elif self.chunk_vectorstore:
                print("📝 使用增强简单检索")
                return self._enhanced_simple_search(query, enhanced_query_info)
            else:
                print("❌ 无可用向量存储")
                return []
        except Exception as e:
            print(f"❌ 智能检索失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _analyze_and_enhance_query(self, query: str) -> Dict[str, Any]:
        """分析和增强查询"""
        enhanced_info = {
            "entities": {},
            "keywords": [],
            "query_intent": "general",
            "complexity_score": 0.0
        }
        
        try:
            # 1. 使用增强分词器提取实体和关键词
            if self.enhanced_tokenizer:
                # 提取人员姓名
                person_names = self.enhanced_tokenizer.get_person_names(query)
                if person_names:
                    enhanced_info["entities"]["persons"] = person_names
                
                # 提取组织机构
                organizations = self.enhanced_tokenizer.get_organizations(query)
                if organizations:
                    enhanced_info["entities"]["organizations"] = organizations
                
                # 提取关键词
                keywords = self.enhanced_tokenizer.extract_keywords(query, top_k=10)
                enhanced_info["keywords"] = keywords
            
            # 2. 分析查询意图
            enhanced_info["query_intent"] = self._analyze_query_intent(query, enhanced_info)
            
            # 3. 生成语义扩展
            if self.enable_semantic_expansion:
                semantic_expansions = self._generate_semantic_expansions(query, enhanced_info)
                enhanced_info["semantic_expansions"] = semantic_expansions
            
            # 4. 计算复杂度评分
            complexity_score = len(enhanced_info["entities"].get("persons", [])) * 0.2
            complexity_score += len(enhanced_info["keywords"]) * 0.1
            enhanced_info["complexity_score"] = min(complexity_score, 1.0)
            
            print(f"🔍 查询增强完成: 实体={enhanced_info['entities']}, 意图={enhanced_info['query_intent']}")
            
        except Exception as e:
            print(f"⚠️ 查询增强失败: {e}")
        
        return enhanced_info
    
    def _analyze_query_intent(self, query: str, enhanced_info: Dict) -> str:
        """分析查询意图"""
        query_lower = query.lower()
        
        # 投诉相关查询
        if any(word in query_lower for word in ['投诉', '举报', '反映', '申诉']):
            if any(word in query_lower for word in ['内容', '什么', '详情']):
                return "complaint_content"
            elif any(word in query_lower for word in ['处理', '结果', '回复']):
                return "complaint_handling"
            else:
                return "complaint_general"
        
        # 人员相关查询
        if enhanced_info.get("entities", {}).get("persons"):
            return "person_related"
        
        # 事件相关查询
        if any(word in query_lower for word in ['事件', '情况', '问题']):
            return "event_related"
        
        return "general"
    
    def _generate_semantic_expansions(self, query: str, enhanced_info: Dict) -> List[str]:
        """生成语义扩展"""
        expansions = []
        
        # 基于查询意图生成扩展
        intent = enhanced_info.get("query_intent", "general")
        
        if intent == "complaint_content":
            expansions.extend(["投诉详情", "反映内容", "举报事项", "申诉原因"])
        elif intent == "complaint_handling":
            expansions.extend(["处理结果", "回复情况", "解决方案", "调查结论"])
        elif intent == "person_related":
            expansions.extend(["相关人员", "当事人", "责任人"])
        
        # 基于实体生成扩展
        entities = enhanced_info.get("entities", {})
        for entity_type, entity_list in entities.items():
            for entity in entity_list[:2]:  # 每种实体类型取前2个
                if entity_type == "persons":
                    expansions.append(f"{entity}相关")
                    expansions.append(f"关于{entity}")
        
        return expansions[:5]  # 限制扩展数量
    
    def _should_use_intelligent_search(self, query: str, enhanced_info: Dict) -> bool:
        """判断是否使用智能搜索"""
        # 如果查询复杂度高，使用智能搜索
        if enhanced_info.get("complexity_score", 0) > self.complexity_threshold:
            return True
        
        # 如果包含人员实体，使用智能搜索
        if enhanced_info.get("entities", {}).get("persons"):
            return True
        
        # 如果是投诉相关查询，使用智能搜索
        if enhanced_info.get("query_intent", "").startswith("complaint"):
            return True
        
        return False
    
    def _enhanced_hierarchical_search(self, query: str, enhanced_info: Dict) -> List[Document]:
        """增强分层搜索"""
        try:
            print(f"🔍 开始增强分层检索，查询: '{query}'")
            
            # 检查向量存储是否可用
            if not self.summary_vectorstore:
                print("❌ 摘要向量存储不可用")
                if self.enable_summary_fallback:
                    return self._enhanced_simple_search(query, enhanced_info)
                return []
            
            if not self.chunk_vectorstore:
                print("❌ 块向量存储不可用")
                return []
            
            # 第一层：在摘要中搜索（使用增强查询）
            print(f"📋 第一层：在摘要向量存储中搜索，top_k={self.summary_top_k}")
            summary_docs = self._enhanced_summary_search(query, enhanced_info)
            
            if not summary_docs:
                print("⚠️ 摘要搜索无结果，启用回退搜索")
                if self.enable_summary_fallback:
                    return self._enhanced_simple_search(query, enhanced_info)
                return []
            
            # 提取相关文档ID（使用增强匹配）
            relevant_doc_ids = self._extract_relevant_doc_ids(summary_docs, enhanced_info)
            
            if not relevant_doc_ids:
                print("⚠️ 无相关文档ID，启用回退搜索")
                if self.enable_summary_fallback:
                    return self._enhanced_simple_search(query, enhanced_info)
                return []
            
            # 第二层：在相关文档的块中搜索（使用增强检索）
            print(f"📄 第二层：使用增强检索在块向量存储中搜索")
            chunk_docs = self._enhanced_chunk_search(query, enhanced_info, relevant_doc_ids)
            
            print(f"🎯 增强分层检索完成，最终返回文档数量: {len(chunk_docs)}")
            return chunk_docs
            
        except Exception as e:
            print(f"增强分层搜索失败: {e}")
            import traceback
            traceback.print_exc()
            if self.enable_summary_fallback:
                return self._enhanced_simple_search(query, enhanced_info)
            return []
    
    def _enhanced_summary_search(self, query: str, enhanced_info: Dict) -> List[Tuple[Document, float]]:
        """增强摘要搜索"""
        all_results = {}
        
        try:
            # 检查摘要向量存储状态
            if not hasattr(self.summary_vectorstore, 'similarity_search_with_score'):
                print("❌ 摘要向量存储不支持相似度搜索")
                return []
            
            # 1. 原始查询搜索
            print(f"🔍 执行原始查询搜索: '{query}'")
            original_results = self.summary_vectorstore.similarity_search_with_score(
                    query, k=self.summary_top_k
                )
            print(f"📋 原始查询结果数量: {len(original_results)}")
            
            for doc, score in original_results:
                doc_key = hash(doc.page_content)
                if doc_key not in all_results or all_results[doc_key][1] > score:
                    all_results[doc_key] = (doc, score)
                    print(f"✅ 原始查询匹配: score={score:.4f}, doc_id={doc.metadata.get('doc_id', 'N/A')}")
            
            # 2. 实体查询搜索
            entities = enhanced_info.get("entities", {})
            for entity_type, entity_list in entities.items():
                for entity in entity_list[:2]:  # 每种实体类型搜索前2个
                    try:
                        entity_results = self.summary_vectorstore.similarity_search_with_score(
                            entity, k=3
                        )
                        for doc, score in entity_results:
                            # 实体匹配给予更高权重
                            weighted_score = score * 0.8
                            doc_key = hash(doc.page_content)
                            if doc_key not in all_results or all_results[doc_key][1] > weighted_score:
                                all_results[doc_key] = (doc, weighted_score)
                                print(f"✅ 实体搜索匹配: '{entity}' -> score={weighted_score:.4f}")
                    except Exception as e:
                        print(f"⚠️ 实体 '{entity}' 搜索失败: {e}")
            
            # 3. 关键词查询搜索
            keywords = enhanced_info.get("keywords", [])
            for keyword, pos, weight in keywords[:3]:  # 前3个关键词
                if weight > 1.0:  # 只搜索重要关键词
                    try:
                        keyword_results = self.summary_vectorstore.similarity_search_with_score(
                            keyword, k=2
                        )
                        for doc, score in keyword_results:
                            weighted_score = score / weight  # 权重越高，分数越低（更相关）
                            doc_key = hash(doc.page_content)
                            if doc_key not in all_results or all_results[doc_key][1] > weighted_score:
                                all_results[doc_key] = (doc, weighted_score)
                                print(f"✅ 关键词搜索匹配: '{keyword}' -> score={weighted_score:.4f}")
                    except Exception as e:
                        print(f"⚠️ 关键词 '{keyword}' 搜索失败: {e}")
            
            # 排序并返回结果
            sorted_results = sorted(all_results.values(), key=lambda x: x[1])
            final_results = sorted_results[:self.summary_top_k * 2]
            
            print(f"📋 增强摘要搜索结果数量: {len(final_results)}")
            for i, (doc, score) in enumerate(final_results):
                print(f"  摘要 {i+1}: score={score:.4f}, doc_id={doc.metadata.get('doc_id', 'N/A')}, content_preview={doc.page_content[:100]}...")
            
            return final_results
            
        except Exception as e:
            print(f"❌ 增强摘要搜索失败: {e}")
            return []
            
    def _extract_relevant_doc_ids(self, summary_docs: List[Tuple[Document, float]], enhanced_info: Dict) -> set:
        """提取相关文档ID（使用增强匹配）"""
        relevant_doc_ids = set()
        
        # 1. 基于分数阈值的匹配
        for doc, score in summary_docs:
            if score >= self.summary_score_threshold:
                doc_id = doc.metadata.get('doc_id')
                if doc_id:
                    relevant_doc_ids.add(doc_id)
                    print(f"✅ 摘要通过阈值检查: doc_id={doc_id}, score={score:.4f}")
            else:
                print(f"❌ 摘要未通过阈值检查: score={score:.4f} < {self.summary_score_threshold}")
            
        # 2. 基于实体匹配的增强过滤
        if self.enable_entity_matching:
            entities = enhanced_info.get("entities", {})
            all_entities = []
            for entity_list in entities.values():
                all_entities.extend(entity_list)
            
            if all_entities:
                print(f"🔍 使用实体匹配增强过滤: {all_entities}")
                for doc, score in summary_docs:
                    doc_content = doc.page_content.lower()
                    # 检查是否包含任何实体
                    for entity in all_entities:
                        if entity.lower() in doc_content:
                            doc_id = doc.metadata.get('doc_id')
                            if doc_id:
                                relevant_doc_ids.add(doc_id)
                                print(f"✅ 实体匹配通过: doc_id={doc_id}, entity='{entity}', score={score:.4f}")
                                break
        
        # 3. 如果没有匹配的文档，降低阈值重新匹配
        if not relevant_doc_ids and summary_docs:
            print("⚠️ 无匹配文档，降低阈值重新匹配...")
            relaxed_threshold = self.summary_score_threshold * 1.5
            for doc, score in summary_docs:
                if score <= relaxed_threshold:  # 注意：分数越低越相关
                    doc_id = doc.metadata.get('doc_id')
                    if doc_id:
                        relevant_doc_ids.add(doc_id)
                        print(f"🔄 放宽阈值通过: doc_id={doc_id}, score={score:.4f}")
        
        print(f"📝 相关文档ID集合: {relevant_doc_ids}")
        return relevant_doc_ids
    
    def _enhanced_chunk_search(self, query: str, enhanced_info: Dict, relevant_doc_ids: set) -> List[Document]:
        """增强块搜索 - 精确定位包含关键字的文档块，并聚合同一实体的所有相关块"""
        try:
            print(f"📄 开始增强块搜索，相关文档ID数量: {len(relevant_doc_ids)}")
            
            # 提取查询中的关键实体和关键词
            entities = enhanced_info.get("entities", {})
            keywords = enhanced_info.get("keywords", [])
            
            # 构建搜索关键词列表
            search_terms = []
            for entity_list in entities.values():
                search_terms.extend(entity_list)
            search_terms.extend([kw[0] for kw in keywords if kw[2] > 1.0])  # 只取重要关键词
            
            print(f"🔍 搜索关键词: {search_terms}")
            
            if self.enable_enhanced_second_layer:
                print("🔧 使用实体聚合检索进行第二层检索")
                
                # 1. 执行大范围向量检索获取候选文档块
                # 大幅增加候选数量，确保不遗漏相关块
                candidate_k = max(self.chunk_top_k * 10, 100)  # 至少检索100个候选
                candidate_results = self.chunk_vectorstore.similarity_search_with_score(
                    query, k=candidate_k
                )
                
                print(f"📄 向量检索候选结果数量: {len(candidate_results)}")
                
                # 2. 实体聚合分析 - 按实体分组收集所有相关块
                entity_blocks = {}  # 实体名 -> 相关块列表
                keyword_matched_chunks = []
                other_relevant_chunks = []
                
                for doc, score in candidate_results:
                    doc_id = doc.metadata.get('doc_id', '')
                    
                    # 如果doc_id为空，尝试生成
                    if not doc_id or doc_id == 'N/A':
                        doc_id = self._generate_doc_id_for_chunk(doc, 0)
                    
                    source_doc_id = self._extract_source_doc_id(doc_id)
                    content = doc.page_content.lower()
                    
                    # 检查是否属于相关文档
                    is_relevant_doc = self._is_doc_in_relevant_set(source_doc_id, relevant_doc_ids)
                    
                    # 检查关键字匹配和实体识别
                    keyword_matches = []
                    matched_entities = []
                    keyword_score = 0
                    
                    for term in search_terms:
                        if term.lower() in content:
                            keyword_matches.append(term)
                            matched_entities.append(term)
                            # 计算关键字在文档中的位置和频次
                            positions = self._find_keyword_positions(content, term.lower())
                            keyword_score += len(positions) * 0.1  # 频次加分
                            
                            # 如果关键字在文档开头，给予额外加分
                            if positions and positions[0] < 100:
                                keyword_score += 0.2
                    
                    # 综合评分：向量相似度 + 关键字匹配 + 文档相关性
                    final_score = score
                    if keyword_matches:
                        final_score = score * 0.6 + keyword_score * 0.4  # 增加关键字匹配权重
                        
                    if is_relevant_doc:
                        final_score *= 0.7  # 相关文档给予更高优先级（分数越低越好）
                    
                    chunk_info = {
                        'doc': doc,
                        'score': final_score,
                        'vector_score': score,
                        'keyword_score': keyword_score,
                        'keyword_matches': keyword_matches,
                        'matched_entities': matched_entities,
                        'is_relevant_doc': is_relevant_doc,
                        'doc_id': doc_id,
                        'source_doc_id': source_doc_id
                    }
                    
                    # 按实体分组收集块
                    for entity in matched_entities:
                        if entity not in entity_blocks:
                            entity_blocks[entity] = []
                        entity_blocks[entity].append(chunk_info)
                    
                    if keyword_matches:
                        keyword_matched_chunks.append(chunk_info)
                        print(f"✅ 关键字匹配块: doc_id={doc_id}, 匹配词={keyword_matches}, 综合分数={final_score:.4f}")
                    elif is_relevant_doc:
                        other_relevant_chunks.append(chunk_info)
                        print(f"📋 文档相关块: doc_id={doc_id}, 向量分数={score:.4f}")
                
                # 3. 实体聚合策略 - 确保每个匹配实体的所有相关块都被包含
                final_chunks = []
                used_doc_ids = set()
                
                print(f"🎯 实体聚合分析，发现实体: {list(entity_blocks.keys())}")
                
                # 为每个匹配的实体收集所有相关块
                for entity, chunks in entity_blocks.items():
                    print(f"📊 处理实体 '{entity}': 找到 {len(chunks)} 个相关块")
                    
                    # 按分数排序，但确保同一实体的多个块都被包含
                    chunks.sort(key=lambda x: x['score'])
                    
                    # 为每个实体至少保留前N个最相关的块
                    entity_limit = min(len(chunks), max(3, self.chunk_top_k // len(entity_blocks)))
                    
                    for chunk in chunks[:entity_limit]:
                        if chunk['doc_id'] not in used_doc_ids:
                            final_chunks.append(chunk['doc'])
                            used_doc_ids.add(chunk['doc_id'])
                            print(f"  ✅ 添加实体块: {chunk['doc_id']}")
                
                # 4. 如果结果不够，补充其他关键字匹配的块
                if len(final_chunks) < self.chunk_top_k:
                    print(f"📝 结果不足({len(final_chunks)})，补充其他关键字匹配块")
                    keyword_matched_chunks.sort(key=lambda x: x['score'])
                    
                    for chunk in keyword_matched_chunks:
                        if len(final_chunks) >= self.chunk_top_k:
                            break
                        if chunk['doc_id'] not in used_doc_ids:
                            final_chunks.append(chunk['doc'])
                            used_doc_ids.add(chunk['doc_id'])
                            print(f"  ✅ 补充关键字块: {chunk['doc_id']}")
                
                # 5. 如果还是不够，补充相关文档的块
                if len(final_chunks) < self.chunk_top_k:
                    print(f"📋 结果仍不足({len(final_chunks)})，补充相关文档块")
                    other_relevant_chunks.sort(key=lambda x: x['score'])
                    
                    for chunk in other_relevant_chunks:
                        if len(final_chunks) >= self.chunk_top_k:
                            break
                        if chunk['doc_id'] not in used_doc_ids:
                            final_chunks.append(chunk['doc'])
                            used_doc_ids.add(chunk['doc_id'])
                            print(f"  ✅ 补充相关块: {chunk['doc_id']}")
                
                # 6. 为每个选中的块添加关键字高亮信息
                for i, doc in enumerate(final_chunks):
                    highlighted_content = self._highlight_keywords_in_content(
                        doc.page_content, search_terms
                    )
                    # 将高亮信息添加到metadata中
                    doc.metadata['highlighted_content'] = highlighted_content
                    doc.metadata['search_terms'] = search_terms
                
                print(f"🎯 实体聚合检索完成，返回文档块数量: {len(final_chunks)}")
                print(f"📊 实体分布: {[(entity, len(chunks)) for entity, chunks in entity_blocks.items()]}")
                return final_chunks
                
            else:
                print("⚠️ 增强检索未启用，使用标准块搜索")
                return self._standard_chunk_search(query, enhanced_info, relevant_doc_ids)
                
        except Exception as e:
            print(f"❌ 增强块搜索失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _find_keyword_positions(self, content: str, keyword: str) -> List[int]:
        """查找关键字在内容中的位置"""
        positions = []
        start = 0
        while True:
            pos = content.find(keyword, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        return positions
    
    def _highlight_keywords_in_content(self, content: str, search_terms: List[str]) -> str:
        """在内容中高亮关键字"""
        highlighted_content = content
        for term in search_terms:
            if term.lower() in content.lower():
                # 使用简单的标记方式高亮
                highlighted_content = highlighted_content.replace(
                    term, f"**{term}**"
                )
        return highlighted_content

    def _extract_source_doc_id(self, doc_id: str) -> str:
        """从块文档ID中提取源文档ID"""
        if not doc_id:
            return ""
        
        # 处理类似 "信息科（投诉）_row_28" 的格式
        if "_row_" in doc_id:
            parts = doc_id.split("_row_")
            if len(parts) >= 2:
                return parts[0]
        
        # 处理其他格式
        return doc_id
    
    def _is_doc_in_relevant_set(self, source_doc_id: str, relevant_doc_ids: set) -> bool:
        """检查文档是否在相关文档集合中"""
        if not source_doc_id:
            return False
        
        # 标准化路径格式
        normalized_source = source_doc_id.replace('\\', '/').lower()
        
        for relevant_id in relevant_doc_ids:
            normalized_relevant = relevant_id.replace('\\', '/').lower()
            
            # 1. 精确匹配
            if normalized_source == normalized_relevant:
                return True
            
            # 2. 包含匹配
            if normalized_source in normalized_relevant or normalized_relevant in normalized_source:
                return True
            
            # 3. 文件名匹配（去掉路径前缀）
            source_basename = normalized_source.split('/')[-1]
            relevant_basename = normalized_relevant.split('/')[-1]
            
            if source_basename == relevant_basename:
                return True
            
            # 4. 基础文件名匹配（去掉_row_部分）
            if '_row_' in source_basename and '_row_' in relevant_basename:
                source_base = source_basename.split('_row_')[0]
                relevant_base = relevant_basename.split('_row_')[0]
                if source_base == relevant_base:
                    return True
        
        return False
    
    def _standard_chunk_search(self, query: str, enhanced_info: Dict, relevant_doc_ids: set) -> List[Document]:
        """标准块搜索方法"""
        try:
            print("🔧 使用标准向量检索")
            enhanced_results = self.chunk_vectorstore.similarity_search_with_score(
                query, k=self.chunk_top_k * 3
            )
            
            print(f"📄 标准块搜索原始结果数量: {len(enhanced_results)}")
            
            # 过滤并排序结果
            filtered_docs = []
            high_score_docs = []
            entity_matched_docs = []
            
            # 提取实体用于匹配
            entities = enhanced_info.get("entities", {})
            all_entities = []
            for entity_list in entities.values():
                all_entities.extend(entity_list)
            
            for i, (doc, score) in enumerate(enhanced_results):
                # 检查分数阈值
                if score > self.chunk_score_threshold * 2:  # 放宽阈值
                    continue
                
                doc_id = doc.metadata.get('doc_id')
                
                # 如果文档没有doc_id，尝试生成一个
                if not doc_id:
                    doc_id = self._generate_doc_id_for_chunk(doc, i)
                
                # 1. 精确文档ID匹配
                if doc_id in relevant_doc_ids:
                    filtered_docs.append((doc, score))
                    print(f"✅ 块通过精确匹配: doc_id={doc_id}, score={score:.4f}")
                    continue
                
                # 2. 模糊文档ID匹配
                matched_id = self._fuzzy_match_doc_id(doc_id, relevant_doc_ids)
                if matched_id:
                    filtered_docs.append((doc, score))
                    print(f"✅ 块通过模糊匹配: doc_id={doc_id} → {matched_id}, score={score:.4f}")
                    continue
                
                # 3. 实体内容匹配
                if self.enable_entity_matching and all_entities:
                    doc_content = doc.page_content.lower()
                    entity_matched = False
                    for entity in all_entities:
                        if entity.lower() in doc_content:
                            entity_matched_docs.append((doc, score, entity))
                            print(f"✅ 块通过实体匹配: entity='{entity}', score={score:.4f}")
                            entity_matched = True
                            break
                    if entity_matched:
                        continue
                
                # 4. 收集高分文档
                if score <= 1.5:  # 相对较高的相似度分数
                    high_score_docs.append((doc, score, doc_id))
            
            # 合并结果
            final_docs = []
            
            # 添加精确匹配的文档
            filtered_docs.sort(key=lambda x: x[1])
            final_docs.extend([doc for doc, _ in filtered_docs[:self.chunk_top_k]])
            
            # 如果结果不够，添加实体匹配的文档
            if len(final_docs) < self.chunk_top_k and entity_matched_docs:
                entity_matched_docs.sort(key=lambda x: x[1])
                needed = self.chunk_top_k - len(final_docs)
                for doc, score, entity in entity_matched_docs[:needed]:
                    final_docs.append(doc)
                    print(f"🔄 添加实体匹配文档: entity='{entity}', score={score:.4f}")
            
            # 如果结果仍然不够，添加高分文档
            if len(final_docs) < self.chunk_top_k and high_score_docs:
                high_score_docs.sort(key=lambda x: x[1])
                needed = self.chunk_top_k - len(final_docs)
                for doc, score, doc_id in high_score_docs[:needed]:
                    final_docs.append(doc)
                    print(f"🔄 添加高分相关文档: doc_id={doc_id}, score={score:.4f}")
            
            print(f"🎯 标准块搜索最终返回文档数量: {len(final_docs)}")
            return final_docs
            
        except Exception as e:
            print(f"❌ 标准块搜索失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _generate_doc_id_for_chunk(self, doc: Document, index: int) -> str:
        """为块文档生成doc_id"""
        source = doc.metadata.get('source', f'doc_{index}')
        row = doc.metadata.get('row', index)
        
        # 对于Excel等结构化数据，使用文件名+行号作为唯一ID
        if 'row' in doc.metadata:
            base_name = source.split('/')[-1].split('.')[0] if '/' in source or '.' in source else source
            # 处理路径分隔符
            base_name = base_name.replace('\\', '/').split('/')[-1]
            return f"{base_name}_row_{row}"
        else:
            # 对于其他文档，使用文件名+索引
            base_name = source.split('/')[-1].split('.')[0] if '/' in source or '.' in source else source
            base_name = base_name.replace('\\', '/').split('/')[-1]
            return f"{base_name}_{index}"
    
    def _fuzzy_match_doc_id(self, doc_id: str, relevant_doc_ids: set) -> str:
        """模糊匹配doc_id"""
        if not doc_id or not relevant_doc_ids:
            return None
        
        # 提取基础名称（去掉路径前缀）
        base_doc_id = doc_id.replace('\\', '/').split('/')[-1]
        
        for relevant_id in relevant_doc_ids:
            base_relevant_id = relevant_id.replace('\\', '/').split('/')[-1]
            
            # 检查是否有相似的基础名称
            if base_doc_id == base_relevant_id:
                return relevant_id
            
            # 检查是否是同一文件的不同部分
            if '_row_' in base_doc_id and '_row_' in base_relevant_id:
                doc_file_part = base_doc_id.split('_row_')[0]
                relevant_file_part = base_relevant_id.split('_row_')[0]
                if doc_file_part == relevant_file_part:
                    return relevant_id
        
        return None

    def _enhanced_simple_search(self, query: str, enhanced_info: Dict) -> List[Document]:
        """增强简单搜索（回退方案）"""
        try:
            print(f"🔄 启用增强简单搜索回退方案，查询: '{query}'")
            
            if not self.chunk_vectorstore:
                print("❌ 块向量存储不存在")
                return []
            
            # 使用增强检索方法
            if self.keyword_processor and self.enable_enhanced_second_layer:
                print("🔧 使用关键词处理器进行增强检索")
                enhanced_results = self.keyword_processor.enhanced_search_with_scores(
                    query, self.chunk_vectorstore
                )
            else:
                print("🔧 使用标准向量检索")
                enhanced_results = self.chunk_vectorstore.similarity_search_with_score(
                    query, k=self.chunk_top_k * 2
                )
            
            print(f"📄 增强简单搜索结果数量: {len(enhanced_results)}")
            
            # 过滤结果
            filtered_docs = []
            entities = enhanced_info.get("entities", {})
            all_entities = []
            for entity_list in entities.values():
                all_entities.extend(entity_list)
            
            for i, (doc, score) in enumerate(enhanced_results):
                # 基本分数过滤
                if score <= self.chunk_score_threshold * 1.5:  # 放宽阈值
                    filtered_docs.append(doc)
                    print(f"✅ 增强简单搜索通过: score={score:.4f}, doc_id={doc.metadata.get('doc_id', 'N/A')}")
                # 实体匹配过滤
                elif self.enable_entity_matching and all_entities:
                    doc_content = doc.page_content.lower()
                    for entity in all_entities:
                        if entity.lower() in doc_content:
                            filtered_docs.append(doc)
                            print(f"✅ 实体匹配通过: entity='{entity}', score={score:.4f}")
                            break
            
            final_docs = filtered_docs[:self.chunk_top_k]
            print(f"🎯 增强简单搜索最终返回文档数量: {len(final_docs)}")
            return final_docs
            
        except Exception as e:
            print(f"增强简单搜索失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _simple_search(self, query: str) -> List[Document]:
        """简单搜索（回退方案）"""
        try:
            print(f"🔄 启用简单搜索回退方案，查询: '{query}'")
            if self.chunk_vectorstore:
                try:
                    docs = self.chunk_vectorstore.similarity_search_with_score(
                        query, k=self.chunk_top_k
                    )
                except Exception as e:
                    print(f"❌ 简单搜索向量存储搜索失败: {e}")
                    return []
                print(f"📄 简单搜索结果数量: {len(docs)}")
                
                filtered_docs = []
                for i, (doc, score) in enumerate(docs):
                    if score >= self.chunk_score_threshold:
                        filtered_docs.append(doc)
                        print(f"✅ 简单搜索通过: score={score:.4f}, doc_id={doc.metadata.get('doc_id', 'N/A')}, content_preview={doc.page_content[:50]}...")
                    else:
                        print(f"❌ 简单搜索未通过: score={score:.4f} < {self.chunk_score_threshold}")
                
                print(f"🎯 简单搜索最终返回文档数量: {len(filtered_docs)}")
                return filtered_docs
            else:
                print("❌ 块向量存储不存在")
            return []
        except Exception as e:
            print(f"简单搜索失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _is_same_document_group(self, doc_id: str, relevant_doc_ids: set) -> bool:
        """检查文档是否属于同一文档组（更宽松的匹配）"""
        if not doc_id or not relevant_doc_ids:
            return False
        
        # 提取基础名称（去掉路径前缀）
        base_doc_id = doc_id.replace('\\', '/').split('/')[-1]
        
        # 提取文件名部分（去掉行号）
        if '_row_' in base_doc_id:
            doc_file_part = base_doc_id.split('_row_')[0]
            try:
                doc_row = int(base_doc_id.split('_row_')[1])
            except (ValueError, IndexError):
                return False
        else:
            return False
        
        # 检查是否有同一文件的其他行
        for relevant_id in relevant_doc_ids:
            base_relevant_id = relevant_id.replace('\\', '/').split('/')[-1]
            
            if '_row_' in base_relevant_id:
                relevant_file_part = base_relevant_id.split('_row_')[0]
                try:
                    relevant_row = int(base_relevant_id.split('_row_')[1])
                except (ValueError, IndexError):
                    continue
                
                # 如果是同一个文件，且行号相近（差距在5行以内），认为是相关的
                if (doc_file_part == relevant_file_part and 
                    abs(doc_row - relevant_row) <= 5):
                    print(f"🔗 发现同组文档: {doc_id} 与 {relevant_id} (行号差距: {abs(doc_row - relevant_row)})")
                    return True
        
        return False


class HierarchicalIndexBuilder:
    """分层索引构建器"""
    
    def __init__(self, embeddings: Embeddings):
        self.embeddings = embeddings
        self.enhanced_tokenizer = EnhancedTokenizer()
    
    def build_hierarchical_index(
        self,
        documents: List[Document],
        vectorstore_path: str,
        **kwargs
    ) -> Tuple[VectorStore, VectorStore]:
        """构建分层索引 - 仅使用FAISS"""
        try:
            from langchain_community.vectorstores import FAISS
            
            print("🔧 使用FAISS构建分层索引...")
            print(f"📄 输入文档数量: {len(documents)}")
            
            # 检查文档是否为空
            if not documents:
                raise ValueError("文档列表为空，无法构建分层索引")
            
            # 创建摘要文档
            summary_docs = self._create_summary_documents(documents)
            print(f"📋 生成摘要文档数量: {len(summary_docs)}")
            
            # 检查摘要文档是否为空
            if not summary_docs:
                raise ValueError("摘要文档列表为空，无法构建分层索引")
            
            # 构建摘要向量存储
            print("📋 构建摘要向量存储...")
            summary_vectorstore = FAISS.from_documents(
                documents=summary_docs,
                embedding=self.embeddings
            )
            
            # 构建块向量存储
            print("📄 构建块向量存储...")
            chunk_vectorstore = FAISS.from_documents(
                documents=documents,
                embedding=self.embeddings
            )
            
            # 保存向量存储到磁盘
            summary_path = os.path.join(vectorstore_path, '..', 'hierarchical_vector_store', 'summary_vector_store')
            chunk_path = os.path.join(vectorstore_path, '..', 'hierarchical_vector_store', 'chunk_vector_store')
            
            os.makedirs(os.path.dirname(summary_path), exist_ok=True)
            os.makedirs(os.path.dirname(chunk_path), exist_ok=True)
            
            print(f"💾 保存摘要向量存储到: {summary_path}")
            summary_vectorstore.save_local(summary_path)
            
            print(f"💾 保存块向量存储到: {chunk_path}")
            chunk_vectorstore.save_local(chunk_path)
            
            print(f"✅ 分层索引已保存到: {os.path.dirname(summary_path)}")
            
            return summary_vectorstore, chunk_vectorstore
            
        except Exception as e:
            print(f"❌ 构建分层索引失败: {e}")
            raise
    
    def _create_summary_documents(self, documents: List[Document]) -> List[Document]:
        """创建摘要文档（支持智能合并相似文档）"""
        print(f"🔍 开始创建摘要文档，输入文档数量: {len(documents)}")
        
        if not documents:
            print("⚠️ 输入文档列表为空")
            return []
        
        summary_docs = []
        doc_groups = {}
        
        # 第一步：按文档ID分组
        for i, doc in enumerate(documents):
            doc_id = doc.metadata.get('doc_id')
            if not doc_id:
                # 如果没有doc_id，为每个文档创建唯一ID
                source = doc.metadata.get('source', f'doc_{i}')
                row = doc.metadata.get('row', i)
                
                # 对于Excel等结构化数据，使用文件名+行号作为唯一ID
                if 'row' in doc.metadata:
                    base_name = source.split('/')[-1].split('.')[0] if '/' in source or '.' in source else source
                    doc_id = f"{base_name}_row_{row}"
                else:
                    # 对于其他文档，使用文件名+索引
                    doc_id = f"{source.split('/')[-1].split('.')[0] if '/' in source or '.' in source else source}_{i}"
                
                print(f"⚠️ 文档 {i} 缺少doc_id，使用默认ID: {doc_id}")
            
            if doc_id not in doc_groups:
                doc_groups[doc_id] = []
            doc_groups[doc_id].append(doc)
        
        print(f"📊 初始文档分组结果: {len(doc_groups)} 个组")
        
        # 第二步：检测并合并相似文档
        merged_groups = self._merge_similar_documents(doc_groups)
        print(f"📊 合并后文档分组结果: {len(merged_groups)} 个组")
        
        # 第三步：为每个文档组创建摘要
        for group_id, doc_list in merged_groups.items():
            try:
                # 合并文档内容
                combined_content = '\n'.join([doc.page_content for doc in doc_list if doc.page_content])
                
                if not combined_content.strip():
                    print(f"⚠️ 文档组 {group_id} 内容为空，跳过")
                    continue
                
                # 创建智能摘要
                summary = self._create_intelligent_summary(combined_content, doc_list)
                
                # 提取关键词
                try:
                    keywords = self.enhanced_tokenizer.extract_keywords(combined_content)
                except Exception as e:
                    print(f"⚠️ 关键词提取失败: {e}，使用空关键词")
                    keywords = []
                
                # 收集所有源文件信息
                sources = list(set([doc.metadata.get('source', 'unknown') for doc in doc_list]))
                
                # 创建摘要文档
                summary_doc = Document(
                    page_content=summary,
                    metadata={
                        'doc_id': group_id,
                        'type': 'summary',
                        'keywords': str(keywords),
                        'chunk_count': len(doc_list),
                        'sources': sources,  # 多个源文件
                        'source': sources[0] if sources else 'unknown',  # 主要源文件
                        'merged_docs': len([doc_id for doc_id in doc_groups.keys() if doc_id.startswith(group_id.split('_merged')[0])])
                    }
                )
                summary_docs.append(summary_doc)
                print(f"✅ 创建摘要文档: {group_id} (内容长度: {len(summary)}, 合并了 {len(doc_list)} 个块)")
                
            except Exception as e:
                print(f"❌ 创建摘要文档失败 {group_id}: {e}")
                continue
        
        print(f"📋 最终生成摘要文档数量: {len(summary_docs)}")
        return summary_docs
    
    def _merge_similar_documents(self, doc_groups: dict) -> dict:
        """合并相似文档"""
        print("🔄 开始检测并合并相似文档...")
        
        merged_groups = {}
        processed_groups = set()
        
        group_items = list(doc_groups.items())
        
        for i, (doc_id1, docs1) in enumerate(group_items):
            if doc_id1 in processed_groups:
                continue
                
            # 当前组作为基础组
            current_group_id = doc_id1
            current_docs = docs1.copy()
            merged_doc_ids = [doc_id1]
            
            # 检查是否与其他组相似
            for j, (doc_id2, docs2) in enumerate(group_items[i+1:], i+1):
                if doc_id2 in processed_groups:
                    continue
                    
                if self._are_documents_similar(docs1, docs2, doc_id1, doc_id2):
                    print(f"🔗 合并相似文档: {doc_id1} + {doc_id2}")
                    current_docs.extend(docs2)
                    merged_doc_ids.append(doc_id2)
                    processed_groups.add(doc_id2)
            
            # 如果合并了多个文档，更新组ID
            if len(merged_doc_ids) > 1:
                current_group_id = f"{doc_id1}_merged_{len(merged_doc_ids)}"
                print(f"📋 创建合并组: {current_group_id} (包含: {', '.join(merged_doc_ids)})")
            
            merged_groups[current_group_id] = current_docs
            processed_groups.add(doc_id1)
        
        return merged_groups
    
    def _are_documents_similar(self, docs1: List[Document], docs2: List[Document], 
                              doc_id1: str, doc_id2: str) -> bool:
        """判断两组文档是否相似"""
        
        # 1. 检查文件名相似性（处理"前件作废"等情况）
        if self._check_filename_similarity(doc_id1, doc_id2):
            return True
        
        # 2. 检查内容相似性
        content1 = ' '.join([doc.page_content for doc in docs1 if doc.page_content])
        content2 = ' '.join([doc.page_content for doc in docs2 if doc.page_content])
        
        if self._check_content_similarity(content1, content2):
            return True
        
        # 3. 检查主题相似性
        if self._check_topic_similarity(content1, content2):
            return True
            
        return False
    
    def _check_filename_similarity(self, doc_id1: str, doc_id2: str) -> bool:
        """检查文件名相似性"""
        # 提取基础文件名（去掉路径和扩展名）
        name1 = doc_id1.split('/')[-1].split('.')[0].lower()
        name2 = doc_id2.split('/')[-1].split('.')[0].lower()
        
        # 移除常见的版本标识词
        version_keywords = ['前件作废', '以此件为准', '修订版', '最新版', '更新版', 'v1', 'v2', 'v3', 
                           '第一版', '第二版', '第三版', '初稿', '终稿', '正式版']
        
        for keyword in version_keywords:
            name1 = name1.replace(keyword, '').strip()
            name2 = name2.replace(keyword, '').strip()
        
        # 移除括号内容（通常是版本说明）
        import re
        name1 = re.sub(r'[（(].*?[）)]', '', name1).strip()
        name2 = re.sub(r'[（(].*?[）)]', '', name2).strip()
        
        # 计算相似度
        similarity = self._calculate_string_similarity(name1, name2)
        
        if similarity > 0.8:  # 80%以上相似度认为是同一文档的不同版本
            print(f"📝 检测到文件名相似: '{name1}' vs '{name2}' (相似度: {similarity:.2f})")
            return True
            
        return False
    
    def _check_content_similarity(self, content1: str, content2: str) -> bool:
        """检查内容相似性"""
        if not content1 or not content2:
            return False
            
        # 简化的内容相似性检查
        # 提取前200字符进行比较
        sample1 = content1[:200].lower()
        sample2 = content2[:200].lower()
        
        similarity = self._calculate_string_similarity(sample1, sample2)
        
        if similarity > 0.7:  # 70%以上相似度
            print(f"📄 检测到内容相似 (相似度: {similarity:.2f})")
            return True
            
        return False
    
    def _check_topic_similarity(self, content1: str, content2: str) -> bool:
        """检查主题相似性"""
        try:
            # 提取关键词进行主题比较
            keywords1 = set(self.enhanced_tokenizer.extract_keywords(content1)[:10])
            keywords2 = set(self.enhanced_tokenizer.extract_keywords(content2)[:10])
            
            if keywords1 and keywords2:
                # 计算关键词重叠度
                intersection = keywords1.intersection(keywords2)
                union = keywords1.union(keywords2)
                
                if union:
                    similarity = len(intersection) / len(union)
                    if similarity > 0.5:  # 50%以上关键词重叠
                        print(f"🏷️ 检测到主题相似 (关键词重叠度: {similarity:.2f})")
                        print(f"   共同关键词: {list(intersection)}")
                        return True
        except Exception as e:
            print(f"⚠️ 主题相似性检查失败: {e}")
            
        return False
    
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """计算字符串相似度（简化版编辑距离）"""
        if not str1 or not str2:
            return 0.0
            
        # 使用简化的Jaccard相似度
        set1 = set(str1)
        set2 = set(str2)
        
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _create_intelligent_summary(self, combined_content: str, doc_list: List[Document]) -> str:
        """创建智能摘要，确保重要信息不丢失"""
        # 如果内容较短，直接返回
        if len(combined_content) <= 500:
            return combined_content
        
        # 检查是否为投诉类文档
        is_complaint_doc = any('投诉' in doc.metadata.get('source', '') for doc in doc_list)
        
        if is_complaint_doc:
            # 对于投诉类文档，使用专门的摘要生成逻辑
            return self._create_complaint_summary(combined_content, doc_list)
        
        # 对于其他类型文档，使用通用摘要逻辑
        lines = combined_content.split('\n')
        
        # 提取重要信息
        important_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 优先保留包含关键信息的行
            if any(keyword in line for keyword in ['通报', '通知', '事件', '情况', '要求', '措施', '处理']):
                important_lines.append(line)
            elif len(line) > 20:  # 保留较长的描述性内容
                important_lines.append(line)
                
            # 限制摘要长度
            if len('\n'.join(important_lines)) > 400:
                break
        
        summary = '\n'.join(important_lines)
        
        # 如果合并了多个文档，添加说明
        if len(doc_list) > 1:
            sources = list(set([doc.metadata.get('source', '').split('/')[-1] for doc in doc_list]))
            summary += f"\n\n[合并文档: {', '.join(sources[:3])}{'等' if len(sources) > 3 else ''}]"
        
        return summary
    
    def _create_complaint_summary(self, combined_content: str, doc_list: List[Document]) -> str:
        """为投诉类文档创建专门的摘要"""
        # 提取关键信息
        people_names = set()
        companies = set()
        problem_types = set()
        locations = set()
        complaint_contents = []
        
        lines = combined_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 提取人员姓名
            if line.startswith('提供方姓名:'):
                name = line.split(':', 1)[1].strip()
                if name and name != '':
                    people_names.add(name)
            
            # 提取企业名称
            elif line.startswith('企业名称:'):
                company = line.split(':', 1)[1].strip()
                if company and company != '':
                    companies.add(company)
            
            # 提取问题类别
            elif line.startswith('问题类别:'):
                problem = line.split(':', 1)[1].strip()
                if problem and problem != '':
                    problem_types.add(problem)
            
            # 提取事发地
            elif line.startswith('事发地:'):
                location = line.split(':', 1)[1].strip()
                if location and location != '':
                    locations.add(location)
            
            # 提取具体问题描述
            elif line.startswith('具体问题:'):
                content = line.split(':', 1)[1].strip()
                if content and content != '' and len(content) > 10:
                    complaint_contents.append(content[:200] + '...' if len(content) > 200 else content)
        
        # 构建结构化摘要
        summary_parts = []
        
        # 添加人员信息（最重要）
        if people_names:
            summary_parts.append(f"投诉人员: {', '.join(people_names)}")
        
        # 添加企业信息
        if companies:
            company_list = list(companies)[:3]  # 只取前3个
            summary_parts.append(f"涉及企业: {', '.join(company_list)}")
        
        # 添加问题类型
        if problem_types:
            problem_list = list(problem_types)[:3]  # 只取前3个
            summary_parts.append(f"问题类型: {', '.join(problem_list)}")
        
        # 添加事发地
        if locations:
            summary_parts.append(f"事发地区: {', '.join(locations)}")
        
        # 添加投诉内容示例
        if complaint_contents:
            summary_parts.append(f"投诉内容示例: {complaint_contents[0]}")
        
        # 添加统计信息
        summary_parts.append(f"投诉记录数量: {len(doc_list)}")
        
        # 如果没有提取到关键信息，使用原始内容的前部分
        if not summary_parts:
            summary_parts.append(combined_content[:400] + '...' if len(combined_content) > 400 else combined_content)
        
        return '\n'.join(summary_parts)