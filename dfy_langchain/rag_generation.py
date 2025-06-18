import os
import sys
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv

# 确保可以导入当前目录的模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from langchain_community.llms import ollama
from langchain_community.chat_models import ChatZhipuAI

# 使用相对导入
try:
    from rag_retrievers import search_documents
except ImportError as e:
    print(f"导入rag_retrievers失败: {e}")
    # 尝试相对导入
    try:
        from .rag_retrievers import search_documents
    except ImportError as e2:
        print(f"相对导入rag_retrievers也失败: {e2}")
        # 如果都失败了，定义一个简单的替代函数
        def search_documents(query, knowledge_base_ids=None, top_k=5, return_scores=False, enable_context_enrichment=True, enable_ranking=True):
            print(f"检索器不可用，查询: {query}, 知识库: {knowledge_base_ids}")
            return []

from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import HumanMessage
# 加载环境变量
load_dotenv()

# 辅助函数：获取文档来源信息
def get_document_source_info(doc):
    """获取文档的详细来源信息"""
    source = doc.metadata.get("source", "未知来源")
    filename = os.path.basename(source) if source else "未知文档"
    
    # 收集额外的来源信息
    source_info = [f"文件名: {filename}"]
    
    # 如果有页码信息，添加页码
    if "page" in doc.metadata:
        source_info.append(f"页码: {doc.metadata['page']}")
        
    # 如果有行号信息（对于表格数据），添加行号
    if "row" in doc.metadata:
        source_info.append(f"行号: {doc.metadata['row']}")
    
    # 如果有创建时间，添加时间信息
    if "created_at" in doc.metadata:
        source_info.append(f"创建时间: {doc.metadata['created_at']}")
        
    # 如果有作者信息，添加作者
    if "author" in doc.metadata:
        source_info.append(f"作者: {doc.metadata['author']}")
    
    return "\n".join(source_info)

class RAGGenerator:
    """
    检索增强生成（RAG）系统
    
    使用检索系统获取相关文档，然后使用大模型生成回答
    """
    
    def __init__(
        self,
        model_name: str = None,
        model_provider: str = None,
        temperature: float = None,
        top_k: int = 5,
        enable_context_enrichment: bool = True,
        enable_ranking: bool = True,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        memory_window_size: int = 5,
        knowledge_base_path: Optional[str] = None,
        # 新增RAG配置参数
        keyword_threshold: int = 1,
        context_window: int = 150,
        score_threshold: float = 0.3,
        weight_keyword_freq: float = 0.4,
        weight_keyword_pos: float = 0.3,
        weight_keyword_coverage: float = 0.3
    ):
        """
        初始化RAG生成器
        
        参数:
            model_name: 使用的模型名称
            model_provider: 模型提供商，支持 'openai', 'zhipu', 'ollama'
            temperature: 生成温度，越高越创造性，越低越确定性
            top_k: 检索的文档数量
            enable_context_enrichment: 是否启用上下文增强
            enable_ranking: 是否启用相关性排序
            api_key: API密钥（如果需要）
            api_url: API基础URL（如果需要）
            memory_window_size: 记忆窗口大小
            knowledge_base_path: 知识库路径
            keyword_threshold: 关键词匹配阈值（至少包含多少个关键词才算匹配）
            context_window: 上下文窗口大小（字符数）
            score_threshold: 相似度分数阈值
            weight_keyword_freq: 关键词频率权重
            weight_keyword_pos: 关键词位置权重
            weight_keyword_coverage: 关键词覆盖度权重
        """
        self.model_name = model_name or os.getenv("RAG_MODEL_NAME", "deepseek-chat")
        self.model_provider = model_provider or os.getenv("RAG_MODEL_PROVIDER", "openai")
        self.temperature = temperature if temperature is not None else float(os.getenv("RAG_TEMPERATURE", "0.3"))
        self.top_k = top_k
        self.enable_context_enrichment = enable_context_enrichment
        self.enable_ranking = enable_ranking
        self.chat_history = ChatMessageHistory()
        self.memory_window_size = memory_window_size
        self.knowledge_base_path = knowledge_base_path or os.path.join("data", "knowledge_base")
        
        # 新增RAG配置参数
        self.keyword_threshold = keyword_threshold
        self.context_window = context_window
        self.score_threshold = score_threshold
        self.weight_keyword_freq = weight_keyword_freq
        self.weight_keyword_pos = weight_keyword_pos
        self.weight_keyword_coverage = weight_keyword_coverage
        
        # API配置
        if self.model_provider == "openai":
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            self.api_url = api_url or os.getenv("OPENAI_API_BASE")
            
            # 检查API密钥是否存在
            if not self.api_key:
                raise ValueError("OpenAI API密钥未设置。请设置OPENAI_API_KEY环境变量或通过api_key参数提供。")
                
            print(f"使用OpenAI模型: {self.model_name}")
            print(f"API基础URL: {self.api_url or '默认'}")
            
        elif self.model_provider == "zhipu":
            self.api_key = api_key or os.getenv("ZHIPUAI_API_KEY")
            self.api_url = api_url
            
            # 检查API密钥是否存在
            if not self.api_key:
                raise ValueError("智谱AI API密钥未设置。请设置ZHIPUAI_API_KEY环境变量或通过api_key参数提供。")
                
            print(f"使用智谱AI模型: {self.model_name}")
            
        elif self.model_provider == "ollama":
            self.api_key = None
            self.api_url = api_url or "http://localhost:11434"
            print(f"使用Ollama模型: {self.model_name}")
            print(f"Ollama API URL: {self.api_url}")
            
        else:
            self.api_key = api_key
            self.api_url = api_url
            print(f"使用未知提供商 '{self.model_provider}' 的模型: {self.model_name}")
        
        # 初始化大模型
        try:
            # OpenAI兼容的提供商（包括DeepSeek、OpenAI兼容API等）
            openai_compatible_providers = ["openai", "deepseek", "openai-compatible"]
            
            if self.model_provider in openai_compatible_providers:
                # 设置环境变量
                if self.api_key:
                    os.environ["OPENAI_API_KEY"] = self.api_key
                if self.api_url:
                    os.environ["OPENAI_API_BASE"] = self.api_url
                    
                print(f"使用OpenAI兼容模型: {self.model_name} (提供商: {self.model_provider})")
                print(f"API基础URL: {self.api_url or '默认'}")
                    
                # 创建ChatOpenAI实例
                self.llm = ChatOpenAI(
                    model_name=self.model_name,
                    temperature=self.temperature,
                    openai_api_key=self.api_key,
                    openai_api_base=self.api_url,
                )
                
            elif self.model_provider == "zhipu":
                # 设置环境变量
                if self.api_key:
                    os.environ["ZHIPUAI_API_KEY"] = self.api_key
                    
                # 创建ChatZhipuAI实例
                self.llm = ChatZhipuAI(
                    model_name=self.model_name,
                    temperature=self.temperature,
                    api_key=self.api_key
                )
                
            elif self.model_provider == "ollama":
                # 创建Ollama实例
                self.llm = ollama(
                    model=self.model_name,
                    temperature=self.temperature,
                    base_url=self.api_url
                )
                
            else:
                # 对于未知提供商，尝试使用OpenAI兼容模式,刁福元 2025-06-10 10:00:00
                print(f"⚠️  未知提供商 '{self.model_provider}'，尝试使用OpenAI兼容模式")
                
                # 设置环境变量
                if self.api_key:
                    os.environ["OPENAI_API_KEY"] = self.api_key
                if self.api_url:
                    os.environ["OPENAI_API_BASE"] = self.api_url
                    
                # 创建ChatOpenAI实例
                self.llm = ChatOpenAI(
                    model_name=self.model_name,
                    temperature=self.temperature,
                    openai_api_key=self.api_key,
                    openai_api_base=self.api_url,
                )
                print(f"✅ 成功使用OpenAI兼容模式初始化: {self.model_name}")
                
        except Exception as e:
            print(f"初始化大模型时出错: {str(e)}")
            print(f"模型提供商: {self.model_provider}")
            print(f"模型名称: {self.model_name}")
            print(f"API密钥: {'已设置' if self.api_key else '未设置'}")
            print(f"API URL: {self.api_url or '未设置'}")
            raise
        
        # 创建提示模板
        self.prompt_template = PromptTemplate.from_template(
            """
            你是一个专业的智能助手。请基于以下检索到的文档内容，回答用户的问题。
            如果检索到的文档不包含足够的信息来回答问题，请诚实地说明你不知道，不要编造信息。
            
            检索到的文档:
            {context}

            对话历史:
            {chat_history}
            
            用户问题: {question}
            请提供详细、准确、有条理的回答，并尽可能引用文档中的具体信息。但是不要直接引用原文内容，而是需要你进行总结再输出。
            """
        )
    
    def _format_documents(self, docs: List[Union[Document, tuple]]) -> str:
        """
        将文档格式化为字符串
        
        参数:
            docs: 文档列表或(文档,分数)元组列表
            
        返回:
            格式化后的文档字符串
        """
        formatted_docs = []
        
        for i, doc_item in enumerate(docs, 1):
            if isinstance(doc_item, tuple):
                doc, scores = doc_item
                # 获取文件名作为文档标识
                source = doc.metadata.get("source", "未知来源")
                filename = os.path.basename(source) if source else "未知文档"
                doc_text = f"文档 ({filename}):\n"
                
                # 添加文档来源（详细信息）
                source_info = get_document_source_info(doc)
                doc_text += f"来源信息:\n{source_info}\n"
                
                # 添加相关性分数
                if isinstance(scores, dict):
                    doc_text += f"相关性分数: {scores.get('combined_score', 0):.4f}\n"
                else:
                    doc_text += f"相关性分数: {scores:.4f}\n"
                
                # 添加文档内容
                doc_text += f"内容:\n{doc.page_content}\n"
            else:
                doc = doc_item
                # 获取文件名作为文档标识
                source = doc.metadata.get("source", "未知来源")
                filename = os.path.basename(source) if source else "未知文档"
                doc_text = f"文档 ({filename}):\n"
                
                # 添加文档来源（详细信息）
                source_info = get_document_source_info(doc)
                doc_text += f"来源信息:\n{source_info}\n"
                
                # 添加文档内容
                doc_text += f"内容:\n{doc.page_content}\n"
            
            formatted_docs.append(doc_text)
        
        return "\n\n".join(formatted_docs)

    def _format_chat_history(self) -> str:
        """格式化聊天历史为字符串"""
        formatted_history = []
        messages = self.chat_history.messages
        
        for i, message in enumerate(messages):
            if isinstance(message, HumanMessage):
                formatted_history.append(f"用户: {message.content}")
            else:  # 假设是AI消息
                formatted_history.append(f"AI助手: {message.content}")
    
        return "\n".join(formatted_history)
    
    def add_message_to_history(self, role: str, content: str):
        if role.lower() == "user":
            self.chat_history.add_user_message(content)
        else:
            self.chat_history.add_ai_message(content)
        # 如果历史记录超过窗口大小，移除最早的消息
        while len(self.chat_history.messages) > self.memory_window_size * 2:  # *2 因为每轮对话有用户和AI两条消息
            self.chat_history.messages.pop(0)
    
    def clear_history(self):
        """清除历史记录"""
        self.chat_history.clear()

    
    def retrieve_and_generate(self, query: str, knowledge_base_ids: List[str] = None, return_source_documents: bool = False, force_vectorstore: bool = False, retriever_type: str = "auto") -> Dict[str, Any]:
        """
        检索相关文档并生成回答
        
        参数:
            query: 用户查询
            knowledge_base_ids: 要搜索的知识库ID列表
            return_source_documents: 是否返回源文档
            force_vectorstore: 是否强制使用向量存储检索器
            retriever_type: 检索器类型 ("auto", "hierarchical", "keyword_ensemble", "vectorstore")
            
        返回:
            包含生成回答和可选源文档的字典
        """
        # 检索相关文档，使用实例的配置参数
        docs = search_documents(
            query=query,
            knowledge_base_ids=knowledge_base_ids,
            top_k=self.top_k,
            return_scores=True,
            enable_context_enrichment=self.enable_context_enrichment,
            enable_ranking=self.enable_ranking,
            # 传递新增的RAG配置参数
            keyword_threshold=self.keyword_threshold,
            context_window=self.context_window,
            score_threshold=self.score_threshold,
            weight_keyword_freq=self.weight_keyword_freq,
            weight_keyword_pos=self.weight_keyword_pos,
            weight_keyword_coverage=self.weight_keyword_coverage,
            force_vectorstore=force_vectorstore,
            retriever_type=retriever_type  # 传递检索器类型
        )

        # 将用户问题添加到历史记录
        self.add_message_to_history("user", query)
        
        # 格式化文档
        if docs:
            formatted_docs = self._format_documents(docs)
            print(f"✅ 检索到 {len(docs)} 个相关文档，正在生成回答...")
        else:
            formatted_docs = "没有检索到相关文档。"
            print("⚠️ 未检索到任何相关文档")
        
        # 格式化聊天历史
        formatted_history = self._format_chat_history()
        # 创建RAG链
        rag_chain = (
            {"context": lambda x: formatted_docs, 
             "chat_history": lambda x: formatted_history, 
             "question": RunnablePassthrough(),}
            | self.prompt_template
            | self.llm
            | StrOutputParser()
        )
        
        # 生成回答
        try:
            answer = rag_chain.invoke(query)
            # 将AI回答添加到历史记录
            self.add_message_to_history("assistant", answer)
        except Exception as e:
            print(f"生成回答时出错: {str(e)}")
            answer = f"抱歉，生成回答时出现错误: {str(e)}"
            self.add_message_to_history("assistant", answer)

        result = {
            "query": query,
            "answer": answer,
        }
        
        if return_source_documents:
            result["source_documents"] = [doc for doc, _ in docs]
        
        return result


# 使用示例
if __name__ == "__main__":
    # 加载环境变量
    load_dotenv(verbose=True)
    print(f"使用模型: {os.getenv('RAG_MODEL_NAME', 'deepseek-chat')}")
    print(f"使用提供商: {os.getenv('RAG_MODEL_PROVIDER', 'openai')}")
    print(f"温度: {os.getenv('RAG_TEMPERATURE', '0.3')}")
    print(f"OpenAI API密钥: {'已设置' if os.getenv('OPENAI_API_KEY') else '未设置'}")
    print(f"OpenAI API基础URL: {os.getenv('OPENAI_API_BASE', '未设置')}")
    print(f"智谱AI API密钥: {'已设置' if os.getenv('ZHIPUAI_API_KEY') else '未设置'}")
    print(f"TOP_K: {os.getenv('TOP_K')}")
    print(f"ENABLE_CONTEXT_ENRICHMENT: {os.getenv('ENABLE_CONTEXT_ENRICHMENT')}")
    print(f"ENABLE_RANKING: {os.getenv('ENABLE_RANKING')}")
    
    try:
        rag = RAGGenerator(
            top_k=int(os.getenv('TOP_K')),
            enable_context_enrichment=bool(os.getenv('ENABLE_CONTEXT_ENRICHMENT',True)),
            enable_ranking=bool(os.getenv('ENABLE_RANKING',True)),
            memory_window_size=5  # 设置记忆窗口大小
        )
        
        # 测试查询
        # test_queries = [
        #     "钟曦瑶一共投诉了多少次,投诉内容是什么,她的联系方式是什么,相关投诉内容的登记编号又分别是什么?",
        # ]

        print("\n=== 连续对话示例 ===")
        # 第一轮对话
        query1 = input("请输入第一个问题: ")
        result1 = rag.retrieve_and_generate(query1)
        print(f"回答:\n{result1['answer']}")
        print("-" * 50)
        
        # 第二轮对话
        query2 = input("请输入第二个问题 (可以引用前一个对话): ")
        result2 = rag.retrieve_and_generate(query2)
        print(f"回答:\n{result2['answer']}")
        print("-" * 50)
    
    except Exception as e:
        print(f"发生错误: {str(e)}")
        import traceback
        traceback.print_exc() 