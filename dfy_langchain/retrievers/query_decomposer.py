#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能查询分解器
实现复杂查询的智能分解、实体提取和多路检索策略
现在真正使用数据库中配置的AI大模型进行智能分析
"""

import json
import re
import os
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from langchain_core.documents import Document

# 导入AI查询分析器
try:
    from .ai_query_analyzer import get_ai_query_analyzer, AIQueryAnalyzer
    AI_ANALYZER_AVAILABLE = True
    print("✅ AI查询分析器导入成功")
except ImportError as e:
    print(f"⚠️ AI查询分析器导入失败: {e}")
    AI_ANALYZER_AVAILABLE = False

class IntelligentQueryDecomposer:
    """智能查询分解器 - 集成AI大模型分析"""
    
    def __init__(self, knowledge_path: Optional[str] = None, model_config_id: Optional[int] = None):
        """
        初始化查询分解器
        
        Args:
            knowledge_path: 先验知识库路径
            model_config_id: 数据库中的AI模型配置ID
        """
        self.knowledge_path = knowledge_path or self._get_default_knowledge_path()
        self.prior_knowledge = self._load_prior_knowledge()
        self.model_config_id = model_config_id
        
        # 初始化AI查询分析器
        if AI_ANALYZER_AVAILABLE:
            try:
                self.ai_analyzer = get_ai_query_analyzer(model_config_id)
                if self.ai_analyzer.is_available():
                    print(f"✅ AI查询分析器初始化成功: {self.ai_analyzer.get_model_info()}")
                else:
                    print("⚠️ AI查询分析器不可用，将使用基础分析")
                    self.ai_analyzer = None
            except Exception as e:
                print(f"⚠️ AI查询分析器初始化失败: {e}")
                self.ai_analyzer = None
        else:
            self.ai_analyzer = None
        
    def _get_default_knowledge_path(self) -> str:
        """获取默认先验知识库路径"""
        current_dir = Path(__file__).parent
        return str(current_dir / "knowledge" / "prior_knowledge.json")
    
    def _load_prior_knowledge(self) -> Dict[str, Any]:
        """加载先验知识库"""
        try:
            if os.path.exists(self.knowledge_path):
                with open(self.knowledge_path, 'r', encoding='utf-8') as f:
                    knowledge = json.load(f)
                print(f"✅ 成功加载先验知识库: {self.knowledge_path}")
                return knowledge
            else:
                print(f"⚠️ 先验知识库文件不存在: {self.knowledge_path}")
                return {}
        except Exception as e:
            print(f"❌ 加载先验知识库失败: {e}")
            return {}
    
    def decompose_query(self, query: str) -> Dict[str, Any]:
        """智能分解查询 - 使用AI大模型进行分析"""
        print(f"🧠 开始AI智能查询分解: '{query}'")
        
        # 1. 使用AI大模型进行查询分析
        ai_analysis = self._analyze_with_ai(query)
        
        # 2. 结合先验知识库进行策略识别
        decomposition_strategy = self._identify_decomposition_strategy(query, ai_analysis)
        
        # 3. 整合实体提取结果
        entities = self._integrate_entity_extraction(query, ai_analysis)
        
        # 4. 生成语义扩展
        expanded_terms = self._generate_semantic_expansions(query, ai_analysis)
        
        # 5. 生成子查询
        sub_queries = self._generate_sub_queries(query, decomposition_strategy, entities, ai_analysis)
        
        # 6. 确定多路检索策略
        multi_path_strategies = self._determine_multi_path_strategies(query, entities, ai_analysis)
        
        result = {
            "original_query": query,
            "decomposition_strategy": decomposition_strategy,
            "entities": entities,
            "expanded_terms": expanded_terms,
            "sub_queries": sub_queries,
            "multi_path_strategies": multi_path_strategies,
            "complexity_score": ai_analysis.get("complexity_score", 0.3),
            "ai_confidence": ai_analysis.get("confidence", 0.0),
            "query_intent": ai_analysis.get("query_intent", "general"),
            "ai_model_info": self.ai_analyzer.get_model_info() if self.ai_analyzer else {}
        }
        
        print(f"📊 AI智能查询分解结果:")
        print(f"  策略: {decomposition_strategy}")
        print(f"  实体数量: {sum(len(v) for v in entities.values())}")
        print(f"  子查询数量: {len(sub_queries)}")
        print(f"  复杂度评分: {result['complexity_score']}")
        print(f"  AI置信度: {result['ai_confidence']}")
        print(f"  查询意图: {result['query_intent']}")
        
        return result
    
    def _analyze_with_ai(self, query: str) -> Dict[str, Any]:
        """使用AI大模型分析查询"""
        if self.ai_analyzer and self.ai_analyzer.is_available():
            print(f"🤖 使用AI大模型分析查询...")
            try:
                ai_result = self.ai_analyzer.analyze_query_with_ai(query)
                print(f"✅ AI分析成功，置信度: {ai_result.get('confidence', 0.0):.2f}")
                return ai_result
            except Exception as e:
                print(f"⚠️ AI分析失败，使用基础分析: {e}")
        else:
            print(f"🔄 AI分析器不可用，使用基础分析")
        
        # 回退到基础分析
        return self._basic_analysis(query)
    
    def _basic_analysis(self, query: str) -> Dict[str, Any]:
        """基础分析方法（当AI不可用时）"""
        entities = {
            "persons": [],
            "organizations": [],
            "locations": [],
            "times": [],
            "topics": []
        }
        
        # 基础实体提取
        person_names = self._extract_person_names_with_regex(query)
        entities["persons"].extend(person_names)
        
        # 基础主题词提取
        topic_keywords = ['投诉', '举报', '反映', '申诉', '意见', '建议', '问题', '事件', '情况', '处理', '调查', '检查']
        for keyword in topic_keywords:
            if keyword in query:
                entities["topics"].append(keyword)
        
        # 基础意图分析
        query_intent = "general"
        if "投诉" in query:
            if "内容" in query or "什么" in query:
                query_intent = "complaint_content"
            elif "处理" in query:
                query_intent = "complaint_handling"
            else:
                query_intent = "complaint_general"
        elif entities["persons"]:
            query_intent = "person_related"
        
        return {
            "entities": entities,
            "query_intent": query_intent,
            "keywords": [word for word in ['投诉', '处理', '内容', '情况'] if word in query],
            "semantic_expansions": [],
            "complexity_score": 0.3,
            "confidence": 0.6
        }
    
    def _identify_decomposition_strategy(self, query: str, ai_analysis: Dict) -> str:
        """识别分解策略 - 结合AI分析和先验知识"""
        # 优先使用AI分析的查询意图
        query_intent = ai_analysis.get("query_intent", "general")
        
        # 映射查询意图到分解策略
        intent_to_strategy = {
            "complaint_content": "person_complaint_content",
            "complaint_handling": "process_oriented",
            "person_related": "person_complaint_general",
            "event_related": "cause_analysis",
            "general": "simple"
        }
        
        strategy = intent_to_strategy.get(query_intent, "simple")
        
        # 使用先验知识库进行验证和补充
        if self.prior_knowledge:
            patterns = self.prior_knowledge.get("query_decomposition_rules", {}).get("complex_patterns", [])
            
            for pattern_info in patterns:
                pattern = pattern_info.get("pattern", "")
                if re.search(pattern, query):
                    prior_strategy = pattern_info.get("decomposition_strategy", "simple")
                    print(f"🎯 先验知识匹配: '{pattern}' -> {prior_strategy}")
                    # 如果先验知识更具体，则使用先验知识的策略
                    if prior_strategy != "simple":
                        strategy = prior_strategy
                    break
        
        print(f"📋 确定分解策略: {strategy} (基于AI意图: {query_intent})")
        return strategy
    
    def _integrate_entity_extraction(self, query: str, ai_analysis: Dict) -> Dict[str, List[str]]:
        """整合实体提取结果"""
        # 从AI分析获取实体
        ai_entities = ai_analysis.get("entities", {})
        
        # 使用增强分词器进行补充提取
        enhanced_entities = self._extract_entities_with_enhanced_tokenizer(query)
        
        # 整合结果
        integrated_entities = {
            "persons": [],
            "organizations": [],
            "locations": [],
            "times": [],
            "topics": []
        }
        
        # 合并AI提取的实体
        for entity_type, entity_list in ai_entities.items():
            if entity_type in integrated_entities:
                integrated_entities[entity_type].extend(entity_list)
        
        # 合并增强分词器提取的实体
        for entity_type, entity_list in enhanced_entities.items():
            if entity_type in integrated_entities:
                for entity in entity_list:
                    if entity not in integrated_entities[entity_type]:
                        integrated_entities[entity_type].append(entity)
        
        # 去重并清理
        for key in integrated_entities:
            integrated_entities[key] = list(set([entity.strip() for entity in integrated_entities[key] if entity.strip()]))
        
        if any(integrated_entities.values()):
            print(f"🏷️ 整合实体提取结果: {integrated_entities}")
        
        return integrated_entities
    
    def _extract_entities_with_enhanced_tokenizer(self, query: str) -> Dict[str, List[str]]:
        """使用增强分词器提取实体"""
        entities = {
            "persons": [],
            "organizations": [],
            "locations": [],
            "times": [],
            "topics": []
        }
        
        try:
            from .utils.enhanced_tokenizer import get_enhanced_tokenizer
            tokenizer = get_enhanced_tokenizer()
            
            # 提取人员姓名
            person_names = tokenizer.get_person_names(query)
            entities["persons"].extend(person_names)
            
            # 提取组织机构
            organizations = tokenizer.get_organizations(query)
            entities["organizations"].extend(organizations)
            
            # 提取地点
            locations = tokenizer.get_locations(query)
            entities["locations"].extend(locations)
            
        except Exception as e:
            print(f"⚠️ 增强分词器实体提取失败: {e}")
            # 回退到正则表达式提取
            person_names = self._extract_person_names_with_regex(query)
            entities["persons"].extend(person_names)
        
        # 提取主题词
        topic_keywords = ['投诉', '举报', '反映', '申诉', '意见', '建议', '问题', '事件', '情况', '处理', '调查', '检查']
        for keyword in topic_keywords:
            if keyword in query:
                entities["topics"].append(keyword)
        
        return entities
    
    def _generate_semantic_expansions(self, query: str, ai_analysis: Dict) -> Dict[str, List[str]]:
        """生成语义扩展 - 结合AI和先验知识"""
        expanded_terms = {
            "synonyms": [],
            "related_terms": [],
            "contextual_terms": []
        }
        
        # 1. 使用AI生成语义扩展
        if self.ai_analyzer and self.ai_analyzer.is_available():
            try:
                ai_expansions = self.ai_analyzer.generate_semantic_expansions_with_ai(query)
                expanded_terms["synonyms"].extend(ai_expansions)
            except Exception as e:
                print(f"⚠️ AI语义扩展失败: {e}")
        
        # 2. 使用先验知识库进行扩展
        if self.prior_knowledge:
            semantic_expansion = self.prior_knowledge.get("query_expansion", {}).get("semantic_expansion", {})
            
            # 基于AI提取的关键词进行扩展
            ai_keywords = ai_analysis.get("keywords", [])
            for keyword in ai_keywords:
                if keyword in semantic_expansion:
                    synonyms = semantic_expansion[keyword]
                    expanded_terms["synonyms"].extend(synonyms)
        
        # 去重
        for key in expanded_terms:
            expanded_terms[key] = list(set(expanded_terms[key]))
        
        if any(expanded_terms.values()):
            print(f"🔍 语义扩展结果: {expanded_terms}")
        
        return expanded_terms
    
    def _extract_person_names_with_regex(self, query: str) -> List[str]:
        """使用正则表达式提取人员姓名"""
        person_names = []
        
        # 优化的人员姓名识别模式
        patterns = [
            # 常见姓氏 + 名字 + 称谓（精确匹配）
            r'([王李张刘陈杨黄赵周吴徐孙朱马胡郭林何高梁郑罗宋谢唐韩曹许邓萧冯曾程蔡彭潘袁于董余苏叶吕魏蒋田杜丁沈姜范江傅钟卢汪戴崔任陆廖姚方金邱夏谭韦贾邹石熊孟秦阎薛侯雷白龙段郝孔邵史毛常万顾赖武康贺严尹钱施牛洪龚汤陶黎温莫易樊乔文安殷颜庄章鲁倪庞邢俞翟蓝聂丛岳齐沿][一-龥]{1,3})(先生|女士|同志|老师|医生|护士|主任|经理|总监|专家|局长|处长|科长|主管|员工|客户|患者|学生|家长)',
            
            # 2-4个汉字 + 称谓（精确匹配）
            r'([一-龥]{2,4})(先生|女士|同志|老师|医生|护士|主任|经理|总监|专家|局长|处长|科长|主管|员工|客户|患者|学生|家长)',
            
            # 投诉人/举报人等模式（精确匹配）
            r'(?:投诉人|举报人|申诉人|反映人)[:：]?\s*([一-龥]{2,4})',
            
            # 姓名在句首的模式（精确匹配）
            r'^([一-龥]{2,4})(?:投诉|反映|举报|申诉)',
            
            # 姓名 + 的 + 投诉相关词（避免提取"钟女士的"）
            r'([一-龥]{2,4})(?=的(?:投诉|反映|举报|申诉))',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query)
            for match in matches:
                if isinstance(match, tuple):
                    # 处理多个捕获组的情况
                    name = None
                    for group in match:
                        if group and self._is_valid_person_name(group):
                            name = group
                            break
                    if name:
                        person_names.append(name)
                        print(f"🏷️ 提取到人员姓名: '{name}'")
                else:
                    if self._is_valid_person_name(match):
                        person_names.append(match)
                        print(f"🏷️ 提取到人员姓名: '{match}'")
        
        # 后处理：清理错误的后缀
        cleaned_names = []
        for name in person_names:
            # 移除常见的错误后缀
            cleaned_name = re.sub(r'(的|投诉|反映|举报|申诉|相关|处理|情况)$', '', name)
            if cleaned_name and self._is_valid_person_name(cleaned_name) and cleaned_name not in cleaned_names:
                cleaned_names.append(cleaned_name)
        
        return cleaned_names
    
    def _is_valid_person_name(self, name: str) -> bool:
        """验证姓名有效性"""
        if not name or len(name) < 2 or len(name) > 4:
            return False
        
        # 过滤明显不是姓名的词汇
        invalid_names = {
            '投诉', '处理', '情况', '内容', '什么', '如何', '为什么', '怎么', 
            '哪里', '什么时候', '问题', '事件', '反映', '举报', '申诉',
            '先生', '女士', '同志', '老师', '医生', '护士', '主任', '经理',
            '有关', '关于', '相关', '所有', '记录', '详细', '信息'
        }
        
        if name in invalid_names:
            return False
        
        # 检查是否包含数字或特殊字符
        if any(char.isdigit() or not char.isalnum() for char in name):
            return False
        
        # 检查是否全是汉字
        if not all('\u4e00' <= char <= '\u9fff' for char in name):
            return False
        
        return True
        
    def _generate_sub_queries(self, query: str, strategy: str, entities: Dict[str, List[str]], ai_analysis: Dict) -> List[str]:
        """生成子查询"""
        sub_queries = []
        
        if strategy == "simple":
            return [query]  # 简单查询不分解
        
        # 基于策略生成子查询
        if strategy in ["topic_detail", "process_oriented", "cause_analysis", "safety_domain", "crisis_management"]:
            sub_queries.extend(self._generate_strategy_based_sub_queries(query, strategy))
        
        # 基于实体生成子查询
        sub_queries.extend(self._generate_entity_based_sub_queries(query, entities))
        
        # 基于语义生成子查询
        sub_queries.extend(self._generate_semantic_based_sub_queries(query))
        
        # 去重并过滤
        sub_queries = list(set(sub_queries))
        sub_queries = [q for q in sub_queries if q and len(q.strip()) > 2]
        
        # 限制子查询数量
        if len(sub_queries) > 8:
            sub_queries = sub_queries[:8]
        
        print(f"📝 生成子查询: {sub_queries}")
        return sub_queries
    
    def _generate_strategy_based_sub_queries(self, query: str, strategy: str) -> List[str]:
        """基于策略生成子查询"""
        sub_queries = []
        
        if not self.prior_knowledge:
            return sub_queries
        
        patterns = self.prior_knowledge.get("query_decomposition_rules", {}).get("complex_patterns", [])
        
        for pattern_info in patterns:
            if pattern_info.get("decomposition_strategy") == strategy:
                template_queries = pattern_info.get("sub_queries", [])
                
                # 提取主题词进行模板替换
                topic_match = re.search(r"关于(.+?)的", query)
                if topic_match:
                    topic = topic_match.group(1)
                    for template in template_queries:
                        sub_query = template.replace("{topic}", topic)
                        sub_queries.append(sub_query)
                else:
                    # 如果没有明确主题，使用关键词
                    keywords = pattern_info.get("keywords", [])
                    for keyword in keywords:
                        if keyword in query:
                            sub_queries.append(keyword)
                break
        
        return sub_queries
    
    def _generate_entity_based_sub_queries(self, query: str, entities: Dict[str, List[str]]) -> List[str]:
        """基于实体生成子查询"""
        sub_queries = []
        
        # 基于人员实体
        for person in entities.get("persons", []):
            sub_queries.append(f"{person}相关信息")
            sub_queries.append(f"{person}投诉")
        
        # 基于组织机构
        for org in entities.get("organizations", []):
            sub_queries.append(f"{org}处理情况")
            sub_queries.append(f"{org}检查")
        
        # 基于地点
        for location in entities.get("locations", []):
            sub_queries.append(f"{location}事件")
            sub_queries.append(f"{location}安全")
        
        # 基于时间
        for time in entities.get("times", []):
            sub_queries.append(f"{time}发生")
            sub_queries.append(f"{time}处理")
        
        # 基于主题
        for topic in entities.get("topics", []):
            sub_queries.append(f"{topic}事件")
            sub_queries.append(f"{topic}处理")
            sub_queries.append(f"{topic}规定")
        
        return sub_queries
    
    def _generate_semantic_based_sub_queries(self, query: str) -> List[str]:
        """基于语义生成子查询"""
        sub_queries = []
        
        # 提取核心动词和名词
        action_words = ["处理", "调查", "检查", "处置", "应对", "解决"]
        object_words = ["投诉", "事件", "问题", "情况", "案件", "舆情"]
        
        for action in action_words:
            if action in query:
                for obj in object_words:
                    if obj in query:
                        sub_queries.append(f"{obj}{action}")
                        sub_queries.append(f"{action}{obj}")
        
        return sub_queries
    
    def _determine_multi_path_strategies(self, query: str, entities: Dict[str, List[str]], ai_analysis: Dict) -> List[str]:
        """确定多路检索策略"""
        strategies = []
        
        # 基于实体数量确定策略
        entity_count = sum(len(v) for v in entities.values())
        
        if entity_count > 3:
            strategies.append("entity_based")
        
        if len(query) > 15:
            strategies.append("semantic_based")
        
        if entities.get("topics"):
            strategies.append("topic_based")
        
        if entities.get("times"):
            strategies.append("time_based")
        
        # 默认策略
        if not strategies:
            strategies.append("semantic_based")
        
        return strategies


class MultiPathRetriever:
    """多路检索器 - 增强版本"""
    
    def __init__(self, base_retriever):
        """初始化多路检索器"""
        self.base_retriever = base_retriever
        self.query_decomposer = IntelligentQueryDecomposer()
    
    def multi_path_search(self, query: str) -> List[Document]:
        """多路检索 - 使用增强检索方法"""
        print(f"🚀 开始增强多路检索: '{query}'")
        
        # 1. 查询分解和语义理解
        decomposition_result = self.query_decomposer.decompose_query(query)
        
        # 2. 判断是否需要多路检索
        if decomposition_result["complexity_score"] < 0.3:
            print("📝 查询复杂度较低，使用增强单路检索")
            # 使用增强的分层检索
            enhanced_query_info = {
                "entities": decomposition_result.get("entities", {}),
                "keywords": [],
                "query_intent": self._analyze_query_intent(query, decomposition_result),
                "complexity_score": decomposition_result["complexity_score"]
            }
            return self.base_retriever._enhanced_hierarchical_search(query, enhanced_query_info)
        
        # 3. 执行多路检索
        all_results = []
        search_paths = []
        
        # 主查询路径 - 使用增强检索
        print("🔍 执行主查询路径...")
        enhanced_query_info = {
            "entities": decomposition_result.get("entities", {}),
            "keywords": [],
            "query_intent": self._analyze_query_intent(query, decomposition_result),
            "complexity_score": decomposition_result["complexity_score"]
        }
        main_results = self.base_retriever._enhanced_hierarchical_search(query, enhanced_query_info)
        search_paths.append(("main_query", query, main_results))
        all_results.extend(main_results)
        
        # 实体查询路径 - 针对提取到的实体进行专门检索
        entities = decomposition_result.get("entities", {})
        self._execute_entity_search_paths(entities, all_results, search_paths)
        
        # 子查询路径 - 使用增强检索
        sub_queries = decomposition_result["sub_queries"][:3]  # 限制子查询数量
        for i, sub_query in enumerate(sub_queries):
            try:
                print(f"🔍 执行子查询 {i+1}: '{sub_query}'")
                sub_enhanced_info = {
                    "entities": entities,
                    "keywords": [],
                    "query_intent": "general",
                    "complexity_score": 0.2
                }
                sub_results = self.base_retriever._enhanced_hierarchical_search(sub_query, sub_enhanced_info)
                search_paths.append((f"sub_query_{i+1}", sub_query, sub_results))
                all_results.extend(sub_results)
                print(f"🔍 子查询 {i+1}: '{sub_query}' -> {len(sub_results)} 个结果")
            except Exception as e:
                print(f"⚠️ 子查询 {i+1} 失败: {e}")
        
        # 扩展词查询路径
        expanded_terms = decomposition_result.get("expanded_terms", {})
        if expanded_terms.get("synonyms"):
            for synonym in expanded_terms["synonyms"][:2]:  # 限制同义词数量
                try:
                    synonym_query = query.replace(query.split()[0], synonym, 1)
                    print(f"🔄 执行同义词查询: '{synonym_query}'")
                    synonym_enhanced_info = {
                        "entities": entities,
                        "keywords": [],
                        "query_intent": "general",
                        "complexity_score": 0.2
                    }
                    synonym_results = self.base_retriever._enhanced_hierarchical_search(synonym_query, synonym_enhanced_info)
                    search_paths.append(("synonym", synonym_query, synonym_results))
                    all_results.extend(synonym_results)
                    print(f"🔄 同义词查询: '{synonym_query}' -> {len(synonym_results)} 个结果")
                except Exception as e:
                    print(f"⚠️ 同义词查询失败: {e}")
        
        # 4. 结果融合
        fused_results = self._fuse_results(all_results, search_paths, decomposition_result)
        
        print(f"🎯 增强多路检索完成，融合后结果数量: {len(fused_results)}")
        return fused_results
    
    def _analyze_query_intent(self, query: str, decomposition_result: Dict) -> str:
        """分析查询意图"""
        query_lower = query.lower()
        
        # 投诉相关查询
        if "投诉" in query_lower:
            if "内容" in query_lower or "什么" in query_lower:
                return "complaint_content"
            elif "处理" in query_lower:
                return "complaint_handling"
            else:
                return "complaint_general"
        
        # 人员相关查询
        entities = decomposition_result.get("entities", {})
        if entities.get("persons"):
            return "person_related"
        
        # 事件相关查询
        if "事件" in query_lower or "情况" in query_lower:
            return "event_related"
        
        return "general"
    
    def _execute_entity_search_paths(self, entities: Dict[str, List[str]], all_results: List, search_paths: List):
        """执行实体搜索路径"""
        # 人员实体搜索
        persons = entities.get("persons", [])
        for person in persons[:2]:  # 限制人员数量
            try:
                print(f"👤 执行人员实体搜索: '{person}'")
                
                # 构建人员相关的查询
                person_queries = [
                    f"{person}投诉",
                    f"{person}相关",
                    f"{person}反映",
                    person  # 直接搜索人员姓名
                ]
                
                for person_query in person_queries:
                    try:
                        person_enhanced_info = {
                            "entities": {"persons": [person]},
                            "keywords": [],
                            "query_intent": "person_related",
                            "complexity_score": 0.3
                        }
                        person_results = self.base_retriever._enhanced_hierarchical_search(person_query, person_enhanced_info)
                        if person_results:
                            search_paths.append(("person_entity", person_query, person_results))
                            all_results.extend(person_results)
                            print(f"👤 人员查询: '{person_query}' -> {len(person_results)} 个结果")
                            break  # 找到结果就停止
                    except Exception as e:
                        print(f"⚠️ 人员查询 '{person_query}' 失败: {e}")
                        
            except Exception as e:
                print(f"⚠️ 人员实体搜索失败: {e}")
        
        # 组织机构实体搜索
        organizations = entities.get("organizations", [])
        for org in organizations[:1]:  # 限制组织数量
            try:
                print(f"🏢 执行组织实体搜索: '{org}'")
                org_enhanced_info = {
                    "entities": {"organizations": [org]},
                    "keywords": [],
                    "query_intent": "organization_related",
                    "complexity_score": 0.2
                }
                org_results = self.base_retriever._enhanced_hierarchical_search(org, org_enhanced_info)
                if org_results:
                    search_paths.append(("organization_entity", org, org_results))
                    all_results.extend(org_results)
                    print(f"🏢 组织查询: '{org}' -> {len(org_results)} 个结果")
            except Exception as e:
                print(f"⚠️ 组织实体搜索失败: {e}")
    
    def _fuse_results(self, all_results: List[Document], search_paths: List[Tuple], decomposition_result: Dict) -> List[Document]:
        """融合多路检索结果 - 增强版本"""
        if not all_results:
            return []
        
        # 去重（基于内容相似度和实体匹配）
        unique_results = self._enhanced_deduplicate_results(all_results, decomposition_result)
        
        # 重新评分（考虑实体匹配）
        scored_results = self._enhanced_rescore_results(unique_results, decomposition_result)
        
        # 排序并返回前N个
        scored_results.sort(key=lambda x: x[1], reverse=True)
        final_results = [doc for doc, score in scored_results[:self.base_retriever.chunk_top_k]]
        
        return final_results
    
    def _enhanced_deduplicate_results(self, results: List[Document], decomposition_result: Dict) -> List[Document]:
        """增强去重结果 - 考虑实体匹配"""
        unique_results = []
        seen_contents = set()
        seen_doc_ids = set()
        
        # 提取实体用于匹配
        entities = decomposition_result.get("entities", {})
        all_entities = []
        for entity_list in entities.values():
            all_entities.extend(entity_list)
        
        for doc in results:
            # 使用doc_id进行去重
            doc_id = doc.metadata.get('doc_id')
            if doc_id and doc_id in seen_doc_ids:
                continue
            
            # 使用内容的前100个字符作为去重标识
            content_key = doc.page_content[:100].strip()
            if content_key in seen_contents:
                continue
            
            # 检查是否包含重要实体（优先保留包含实体的文档）
            doc_content = doc.page_content.lower()
            contains_entity = any(entity.lower() in doc_content for entity in all_entities)
            
            if contains_entity or len(unique_results) < self.base_retriever.chunk_top_k:
                seen_contents.add(content_key)
                if doc_id:
                    seen_doc_ids.add(doc_id)
                unique_results.append(doc)
                
                if contains_entity:
                    print(f"🎯 保留包含实体的文档: doc_id={doc_id}")
        
        print(f"🔄 增强去重: {len(results)} -> {len(unique_results)}")
        return unique_results
    
    def _enhanced_rescore_results(self, results: List[Document], decomposition_result: Dict) -> List[Tuple[Document, float]]:
        """增强重新评分结果 - 考虑实体匹配和查询意图"""
        scored_results = []
        
        # 提取关键词和实体用于评分
        entities = decomposition_result.get("entities", {})
        all_entities = []
        for entity_list in entities.values():
            all_entities.extend(entity_list)
        
        query_intent = decomposition_result.get("query_intent", "general")
        original_query = decomposition_result["original_query"]
        
        for doc in results:
            score = self._calculate_enhanced_relevance_score(
                doc, all_entities, original_query, query_intent
            )
            scored_results.append((doc, score))
        
        return scored_results
    
    def _calculate_enhanced_relevance_score(self, doc: Document, entities: List[str], 
                                          original_query: str, query_intent: str) -> float:
        """计算增强相关性评分 - 考虑实体匹配和查询意图"""
        content = doc.page_content.lower()
        query_lower = original_query.lower()
        
        score = 0.0
        
        # 1. 原查询匹配度 (40%)
        query_words = query_lower.split()
        query_matches = sum(1 for word in query_words if word in content)
        score += (query_matches / len(query_words)) * 0.4
        
        # 2. 实体匹配度 (35%)
        if entities:
            entity_matches = sum(1 for entity in entities if entity.lower() in content)
            entity_score = (entity_matches / len(entities)) * 0.35
            score += entity_score
            
            # 实体精确匹配加分
            for entity in entities:
                if entity.lower() in content:
                    score += 0.1  # 每个匹配的实体额外加分
        
        # 3. 查询意图匹配度 (15%)
        intent_keywords = {
            "complaint_content": ["投诉", "内容", "反映", "举报", "申诉"],
            "complaint_handling": ["处理", "办理", "解决", "回复", "答复"],
            "person_related": ["姓名", "联系", "电话", "地址", "身份"],
            "event_related": ["事件", "情况", "经过", "详情", "过程"]
        }
        
        if query_intent in intent_keywords:
            intent_words = intent_keywords[query_intent]
            intent_matches = sum(1 for word in intent_words if word in content)
            score += (intent_matches / len(intent_words)) * 0.15
        
        # 4. 文档质量加分 (10%)
        if doc.metadata.get('source'):
            score += 0.05
        if doc.metadata.get('doc_id'):
            score += 0.05
        
        # 5. 文档长度惩罚（避免过长文档）
        length_penalty = min(len(content) / 1000.0, 1.0) * 0.05
        score -= length_penalty
        
        return max(score, 0.0) 