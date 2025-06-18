#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI查询分析器
使用数据库中配置的AI大模型进行智能查询理解、实体提取和语义分析
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.services.model_config_service import ModelConfigService
    from app.database import get_db
    from langchain_openai import ChatOpenAI
    from langchain.schema import HumanMessage, SystemMessage
    DB_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 数据库或LangChain模块导入失败: {e}")
    DB_AVAILABLE = False

logger = logging.getLogger(__name__)


class AIQueryAnalyzer:
    """AI查询分析器 - 使用数据库配置的AI模型"""
    
    def __init__(self, model_config_id: Optional[int] = None):
        """
        初始化AI查询分析器
        
        Args:
            model_config_id: 数据库中的模型配置ID，如果为None则使用第一个可用的LLM模型
        """
        self.model_config_id = model_config_id
        self.llm = None
        self.model_config = None
        self._initialize_llm()
        
    def _initialize_llm(self):
        """初始化大语言模型"""
        if not DB_AVAILABLE:
            print("❌ 数据库不可用，无法初始化AI模型")
            return
            
        try:
            # 获取数据库连接
            db = next(get_db())
            
            # 获取模型配置
            if self.model_config_id:
                model_config = ModelConfigService.get_model_config_by_id(db, self.model_config_id)
                if not model_config:
                    raise ValueError(f"未找到ID为 {self.model_config_id} 的模型配置")
            else:
                # 获取第一个可用的LLM模型
                all_configs = ModelConfigService.get_all_model_configs(db)
                llm_configs = [config for config in all_configs 
                             if config.model_type == "llm" and config.test_status == "success"]
                
                if not llm_configs:
                    raise ValueError("未找到可用的LLM模型配置")
                
                model_config = llm_configs[0]
                self.model_config_id = model_config.id
            
            self.model_config = model_config
            
            # 创建ChatOpenAI实例
            self.llm = ChatOpenAI(
                model_name=model_config.model_name,
                openai_api_key=model_config.api_key,
                openai_api_base=model_config.endpoint,
                temperature=0.1,  # 低温度确保结果稳定
                max_tokens=model_config.max_tokens or 2000,
                request_timeout=30
            )
            
            print(f"✅ AI模型初始化成功: {model_config.provider_name} - {model_config.model_name}")
            
        except Exception as e:
            print(f"❌ AI模型初始化失败: {e}")
            logger.error(f"AI模型初始化失败: {e}")
            self.llm = None
            self.model_config = None
    
    def analyze_query_with_ai(self, query: str) -> Dict[str, Any]:
        """使用AI大模型分析查询"""
        if not self.llm:
            print("⚠️ AI模型未初始化，使用基础分析")
            return self._fallback_analysis(query)
        
        try:
            print(f"🤖 使用AI模型分析查询: '{query}'")
            
            # 构建系统提示词
            system_prompt = self._build_system_prompt()
            
            # 构建用户查询
            user_prompt = self._build_user_prompt(query)
            
            # 调用AI模型
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm(messages)
            result_text = response.content
            
            # 解析AI返回的JSON结果
            analysis_result = self._parse_ai_response(result_text, query)
            
            print(f"🎯 AI分析完成:")
            print(f"  实体: {analysis_result.get('entities', {})}")
            print(f"  查询意图: {analysis_result.get('query_intent', 'unknown')}")
            print(f"  关键词: {analysis_result.get('keywords', [])}")
            
            return analysis_result
            
        except Exception as e:
            print(f"⚠️ AI分析失败: {e}")
            logger.error(f"AI分析失败: {e}")
            return self._fallback_analysis(query)
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一个专业的查询分析专家，专门分析用户的查询意图并提取关键信息。

你的任务是分析用户查询，提取以下信息：
1. 人员实体（姓名+称谓，如"钟女士"、"李先生"等）
2. 组织机构（公司、部门、医院等）
3. 地点信息（城市、区域、具体地址等）
4. 时间信息（日期、时间段等）
5. 主题关键词（投诉、处理、检查等）
6. 查询意图分类

请严格按照以下JSON格式返回结果，不要添加任何其他文字：

{
  "entities": {
    "persons": ["提取到的人员姓名"],
    "organizations": ["提取到的组织机构"],
    "locations": ["提取到的地点"],
    "times": ["提取到的时间"],
    "topics": ["提取到的主题词"]
  },
  "query_intent": "查询意图分类",
  "keywords": ["关键词列表"],
  "semantic_expansions": ["语义扩展词"],
  "complexity_score": 0.0,
  "confidence": 0.0
}

查询意图分类包括：
- complaint_content: 询问投诉内容
- complaint_handling: 询问投诉处理情况
- person_related: 人员相关查询
- event_related: 事件相关查询
- general: 一般查询

请确保返回的是有效的JSON格式。"""

    def _build_user_prompt(self, query: str) -> str:
        """构建用户提示词"""
        return f"""请分析以下查询：

查询内容：{query}

请提取其中的实体信息、判断查询意图，并按照指定的JSON格式返回结果。

特别注意：
1. 人员姓名要包含称谓（如"钟女士"、"李先生"）
2. 投诉相关查询要准确分类意图
3. 关键词要提取最重要的3-5个词
4. 复杂度评分范围0-1，越复杂分数越高
5. 置信度评分范围0-1，越确定分数越高"""

    def _parse_ai_response(self, response_text: str, original_query: str) -> Dict[str, Any]:
        """解析AI返回的响应"""
        try:
            # 尝试直接解析JSON
            if response_text.strip().startswith('{'):
                result = json.loads(response_text.strip())
                
                # 验证和补充必要字段
                if "entities" not in result:
                    result["entities"] = {}
                if "query_intent" not in result:
                    result["query_intent"] = "general"
                if "keywords" not in result:
                    result["keywords"] = []
                if "complexity_score" not in result:
                    result["complexity_score"] = 0.3
                if "confidence" not in result:
                    result["confidence"] = 0.8
                
                return result
            
            # 如果不是JSON格式，尝试提取JSON部分
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                return result
            
            # 如果都失败，返回基础分析
            print(f"⚠️ AI返回格式不正确，使用基础分析: {response_text[:100]}...")
            return self._fallback_analysis(original_query)
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON解析失败: {e}")
            return self._fallback_analysis(original_query)
        except Exception as e:
            print(f"⚠️ 响应解析失败: {e}")
            return self._fallback_analysis(original_query)
    
    def _fallback_analysis(self, query: str) -> Dict[str, Any]:
        """回退分析方法（基于规则）"""
        print(f"🔄 使用基础规则分析: '{query}'")
        
        entities = {
            "persons": [],
            "organizations": [],
            "locations": [],
            "times": [],
            "topics": []
        }
        
        # 基础人员姓名提取
        import re
        person_patterns = [
            r'([王李张刘陈杨黄赵周吴徐孙朱马胡郭林何高梁郑罗宋谢唐韩曹许邓萧冯曾程蔡彭潘袁于董余苏叶吕魏蒋田杜丁沈姜范江傅钟卢汪戴崔任陆廖姚方金邱夏谭韦贾邹石熊孟秦阎薛侯雷白龙段郝孔邵史毛常万顾赖武康贺严尹钱施牛洪龚汤陶黎温莫易樊乔文安殷颜庄章鲁倪庞邢俞翟蓝聂丛岳齐沿][一-龥]{1,3})(先生|女士|同志|老师|医生|护士|主任|经理|总监|专家|局长|处长|科长|主管)',
            r'([一-龥]{2,4})(先生|女士|同志|老师|医生|护士|主任|经理|总监|专家|局长|处长|科长|主管)',
        ]
        
        for pattern in person_patterns:
            matches = re.findall(pattern, query)
            for match in matches:
                if isinstance(match, tuple):
                    person_name = match[0] + match[1]
                    entities["persons"].append(person_name)
        
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
        elif "事件" in query or "情况" in query:
            query_intent = "event_related"
        
        # 基础关键词提取
        keywords = []
        for word in ['投诉', '处理', '内容', '情况', '问题', '事件']:
            if word in query:
                keywords.append(word)
        
        return {
            "entities": entities,
            "query_intent": query_intent,
            "keywords": keywords,
            "semantic_expansions": [],
            "complexity_score": 0.3,
            "confidence": 0.6
        }
    
    def extract_entities_with_ai(self, text: str) -> Dict[str, List[str]]:
        """使用AI提取实体"""
        analysis_result = self.analyze_query_with_ai(text)
        return analysis_result.get("entities", {})
    
    def analyze_query_intent_with_ai(self, query: str) -> str:
        """使用AI分析查询意图"""
        analysis_result = self.analyze_query_with_ai(query)
        return analysis_result.get("query_intent", "general")
    
    def generate_semantic_expansions_with_ai(self, query: str) -> List[str]:
        """使用AI生成语义扩展"""
        if not self.llm:
            return []
        
        try:
            system_prompt = """你是一个语义扩展专家。给定一个查询，请生成3-5个语义相关的扩展词或短语。

请只返回扩展词列表，每行一个，不要添加其他文字。"""
            
            user_prompt = f"请为以下查询生成语义扩展词：{query}"
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm(messages)
            expansions = [line.strip() for line in response.content.split('\n') if line.strip()]
            
            return expansions[:5]  # 限制数量
            
        except Exception as e:
            print(f"⚠️ AI语义扩展失败: {e}")
            return []
    
    def is_available(self) -> bool:
        """检查AI分析器是否可用"""
        return self.llm is not None and self.model_config is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取当前使用的模型信息"""
        if not self.model_config:
            return {}
        
        return {
            "config_id": self.model_config_id,
            "provider": self.model_config.provider,
            "provider_name": self.model_config.provider_name,
            "model_name": self.model_config.model_name,
            "endpoint": self.model_config.endpoint
        }


def get_ai_query_analyzer(model_config_id: Optional[int] = None) -> AIQueryAnalyzer:
    """获取AI查询分析器实例"""
    return AIQueryAnalyzer(model_config_id)


# 测试函数
def test_ai_query_analyzer():
    """测试AI查询分析器"""
    print("🧪 测试AI查询分析器")
    
    analyzer = get_ai_query_analyzer()
    
    if not analyzer.is_available():
        print("❌ AI分析器不可用")
        return
    
    print(f"✅ 使用模型: {analyzer.get_model_info()}")
    
    test_queries = [
        "钟女士的投诉内容是什么",
        "李女士投诉了什么问题",
        "张先生的投诉处理情况如何"
    ]
    
    for query in test_queries:
        print(f"\n🔍 分析查询: '{query}'")
        result = analyzer.analyze_query_with_ai(query)
        print(f"  结果: {json.dumps(result, ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    test_ai_query_analyzer() 