
import requests
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI


@tool(description="使用Baidu Search API进行联网搜索，返回搜索结果的字符串。")
def baidu_search_tool(query: str) -> str:
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
        'Authorization': f'Bearer {API_KEY}',  # 请替换为你的API密钥
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
        "search_recency_filter":"month" #可以自定义各种检索条件
    }
 
    response = requests.post(url, headers=headers, json=data)
 
    if response.status_code == 200:
        # 返回给大模型的格式化的搜索结果文本
        # 可以自己对博查的搜索结果进行自定义处理
        return str(response.json())
    else:
        raise Exception(f"API请求失败，状态码: {response.status_code}, 错误信息: {response.text}")
 
#打印工具名称，描述，参数等 名称正确、文档正确且类型提示正确的工具更易于模型使用
print(baidu_search_tool.name)
print(baidu_search_tool.description)
print(baidu_search_tool.args)
 
#直接使用工具
print(baidu_search_tool.invoke("介绍下langchain"))
 
tools = [baidu_search_tool]
 
#通义千问大模型，可以替换为任何一个支持工具调用的大模型
openai_chat = ChatOpenAI(
    model_name="deepseek-chat",
    openai_api_key="sk-4d1c2f1ab80049f1a55b1e2e45694cc5",
    openai_api_base="https://api.deepseek.com",
)
 
#查看我们的输入是否会调用工具，注意，这里并不会真正调用工具
with_tool = openai_chat.bind_tools(tools)
result = with_tool.invoke("今天成都天气怎么样")
print(result.content)
print(result.tool_calls)
 
#创建代理并调用工具
prompt = ChatPromptTemplate.from_template("今天{city}天气怎么样 {agent_scratchpad}")
agent = create_tool_calling_agent(openai_chat, tools, prompt)  # 使用实例而不是类
agent_executor = AgentExecutor(agent=agent, tools=tools)
print(agent_executor.invoke({"city":"成都", "agent_scratchpad":"intermediate_steps"}))

