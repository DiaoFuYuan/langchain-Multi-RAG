"""
联网搜索路由模块
集成百度搜索agent，提供联网搜索功能
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

# 尝试导入requests，如果失败则使用内置的urllib
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.parse
    import json
    HAS_REQUESTS = False

try:
    from langchain.agents import create_tool_calling_agent, AgentExecutor
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.tools import tool
    from langchain_openai import ChatOpenAI
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/network", tags=["network"])

# 百度搜索工具
def baidu_search_tool_func(query: str) -> str:
    """
    使用Baidu Search API进行联网搜索，返回搜索结果的字符串。
    参数:
    - query: 搜索关键词
    返回:
    - 搜索结果的字符串形式
    """
    url = 'https://qianfan.baidubce.com/v2/ai_search'
    API_KEY = "bce-v3/ALTAK-gwSczlnAJmkqKBAL0AduY/82d5c84861caaf89eec947fbf9a2d413b415d9d0"
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    messages = [
        {
            "content": query,
            "role": "user"
        }
    ]
    data = {
        "messages": messages,
        "search_source": "baidu_search_v2",
        "search_recency_filter": "month"  # 可以自定义各种检索条件
    }
 
    try:
        if HAS_REQUESTS:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                # 提取搜索结果的关键信息
                if 'references' in result:
                    formatted_results = []
                    for ref in result['references'][:5]:  # 取前5个结果
                        title = ref.get('title', '')
                        content = ref.get('content', '')
                        url_ref = ref.get('url', '')
                        date = ref.get('date', '')
                        
                        formatted_results.append(f"""
                        标题: {title}
                        内容: {content}
                        来源: {url_ref}
                        时间: {date}
                        """)
                    
                    return "搜索结果:\n" + "\n---\n".join(formatted_results)
                else:
                    return str(result)
            else:
                raise Exception(f"API请求失败，状态码: {response.status_code}, 错误信息: {response.text}")
        else:
            # 使用urllib作为fallback
            data_bytes = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(url, data=data_bytes, headers=headers)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    
                    if 'references' in result:
                        formatted_results = []
                        for ref in result['references'][:5]:  # 取前5个结果
                            title = ref.get('title', '')
                            content = ref.get('content', '')
                            url_ref = ref.get('url', '')
                            date = ref.get('date', '')
                            
                            formatted_results.append(f"""
                            标题: {title}
                            内容: {content}
                            来源: {url_ref}
                            时间: {date}
                            """)
                        
                        return "搜索结果:\n" + "\n---\n".join(formatted_results)
                    else:
                        return str(result)
                else:
                    raise Exception(f"API请求失败，状态码: {response.status}")
                    
    except Exception as e:
        logger.error(f"百度搜索失败: {str(e)}")
        return f"搜索失败: {str(e)}"

# 创建工具，如果LangChain可用的话
if HAS_LANGCHAIN:
    baidu_search_tool = tool(description="使用Baidu Search API进行联网搜索，返回搜索结果的字符串。")(baidu_search_tool_func)
else:
    baidu_search_tool = baidu_search_tool_func

# 请求模型
class NetworkSearchRequest(BaseModel):
    query: str
    llm_config: Optional[Dict[str, Any]] = None

class NetworkSearchResponse(BaseModel):
    success: bool
    search_results: Optional[str] = None
    enhanced_prompt: Optional[str] = None
    error: Optional[str] = None

@router.post("/search", response_model=NetworkSearchResponse)
async def network_search(request: NetworkSearchRequest):
    """
    执行联网搜索并返回增强的提示词
    """
    try:
        query = request.query.strip()
        if not query:
            raise HTTPException(status_code=400, detail="搜索查询不能为空")
        
        logger.info(f"执行联网搜索: {query}")
        
        # 执行搜索
        if HAS_LANGCHAIN and hasattr(baidu_search_tool, 'invoke'):
            search_results = baidu_search_tool.invoke(query)
        else:
            search_results = baidu_search_tool_func(query)
        
        # 创建增强的提示词
        enhanced_prompt = f"""
基于以下最新的搜索结果回答用户问题：

用户问题: {query}

搜索结果:
{search_results}

请基于上述搜索结果，为用户提供准确、全面的回答。如果搜索结果中包含多个观点，请整合并客观呈现。同时注明信息来源和时间。
"""
        
        return NetworkSearchResponse(
            success=True,
            search_results=search_results,
            enhanced_prompt=enhanced_prompt
        )
        
    except Exception as e:
        logger.error(f"联网搜索失败: {str(e)}")
        return NetworkSearchResponse(
            success=False,
            error=str(e)
        )

@router.post("/search-and-chat")
async def search_and_chat(request: NetworkSearchRequest):
    """
    执行联网搜索并通过AI模型生成回答
    """
    try:
        query = request.query.strip()
        if not query:
            raise HTTPException(status_code=400, detail="搜索查询不能为空")
        
        # 获取模型配置
        llm_config = request.llm_config
        if not llm_config:
            raise HTTPException(status_code=400, detail="未提供模型配置")
        
        logger.info(f"执行联网搜索+AI回答: {query}")
        
        # 1. 执行搜索
        if HAS_LANGCHAIN and hasattr(baidu_search_tool, 'invoke'):
            search_results = baidu_search_tool.invoke(query)
        else:
            search_results = baidu_search_tool_func(query)
        
        if not HAS_LANGCHAIN:
            # 如果没有LangChain，返回搜索结果
            return {
                "success": True,
                "search_results": search_results,
                "ai_response": f"基于搜索结果的回答：\n\n{search_results}\n\n注意：当前环境未安装LangChain，无法使用AI增强功能。",
                "query": query
            }
        
        # 2. 创建AI工具列表
        tools = [baidu_search_tool]
        
        # 3. 初始化AI模型
        if llm_config.get("provider") == "deepseek":
            llm = ChatOpenAI(
                model_name=llm_config.get("model_name", "deepseek-chat"),
                openai_api_key=llm_config.get("api_key"),
                openai_api_base=llm_config.get("endpoint", "https://api.deepseek.com"),
                temperature=0.7
            )
        else:
            # 默认使用OpenAI兼容接口
            llm = ChatOpenAI(
                model_name=llm_config.get("model_name", "gpt-3.5-turbo"),
                openai_api_key=llm_config.get("api_key"),
                openai_api_base=llm_config.get("endpoint"),
                temperature=0.7
            )
        
        # 4. 创建智能体
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个能够使用联网搜索工具的智能助手。
            当用户提问时，你应该：
            1. 分析问题是否需要最新信息
            2. 如果需要，使用搜索工具获取最新信息
            3. 基于搜索结果提供准确、全面的回答
            4. 注明信息来源和时间
            """),
            ("user", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        agent = create_tool_calling_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent, 
            tools=tools, 
            verbose=True,
            handle_parsing_errors=True
        )
        
        # 5. 执行AI推理
        result = agent_executor.invoke({"input": query})
        
        return {
            "success": True,
            "search_results": search_results,
            "ai_response": result.get("output", ""),
            "query": query
        }
        
    except Exception as e:
        logger.error(f"联网搜索+AI回答失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理请求失败: {str(e)}")

@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "service": "network_search"} 