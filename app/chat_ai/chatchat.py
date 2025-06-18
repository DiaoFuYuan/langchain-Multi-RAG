import time
import random
from typing import List, Generator, Iterator, Optional, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from .config.load_key import load_key
# 导入Markdown处理器
from .config.markdown_helper import markdown_processor
# 由于导入错误，直接实现简单的内存类
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage

# 定义简单的记忆类，替代原始的ConversationBufferMemory等
class SimpleMemory:
    """一个简单的对话内存类，用于存储对话历史"""
    
    def __init__(self, return_messages=True, memory_key="history"):
        self.return_messages = return_messages
        self.memory_key = memory_key
        self.chat_memory = ChatMessageHistory()
        
    def clear(self):
        """清除所有存储的消息"""
        self.chat_memory.clear()
        
    def add_messages(self, messages: List[BaseMessage]) -> None:
        """添加多条消息到历史记录中"""
        for message in messages:
            if isinstance(message, HumanMessage):
                self.chat_memory.add_user_message(message.content)
            elif isinstance(message, AIMessage):
                self.chat_memory.add_ai_message(message.content)
            elif isinstance(message, SystemMessage):
                # 系统消息通常不加入对话历史
                pass
            else:
                # 对于其他类型的消息，记录但不处理
                print(f"未处理的消息类型: {type(message)}")
                
    # 为了兼容RunnableWithMessageHistory，添加所需的方法
    @property
    def messages(self) -> List[BaseMessage]:
        """获取所有消息"""
        return self.chat_memory.messages
        
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """加载记忆变量，供RunnableWithMessageHistory使用"""
        if self.return_messages:
            return {self.memory_key: self.chat_memory.messages}
        
        # 如果不需要返回消息对象，则将消息转换为字符串
        result = []
        for message in self.chat_memory.messages:
            if isinstance(message, HumanMessage):
                result.append(f"Human: {message.content}")
            elif isinstance(message, AIMessage):
                result.append(f"AI: {message.content}")
            # 忽略系统消息
        
        # 返回字符串形式的历史
        return {self.memory_key: "\n".join(result)}
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """保存对话上下文，供RunnableWithMessageHistory使用"""
        input_str = inputs.get("input", "")
        output_str = outputs.get("output", "")
        
        # 添加用户输入
        if input_str:
            self.chat_memory.add_user_message(input_str)
            
        # 添加AI输出
        if output_str:
            self.chat_memory.add_ai_message(output_str)

# 消息历史管理类
class ChatMessageHistory:
    """管理聊天消息历史的类"""
    
    def __init__(self):
        self.messages = []
    
    def add_user_message(self, message: str) -> None:
        """添加用户消息"""
        self.messages.append(HumanMessage(content=message))
    
    def add_ai_message(self, message: str) -> None:
        """添加AI消息"""
        self.messages.append(AIMessage(content=message))
    
    def clear(self) -> None:
        """清除所有消息"""
        self.messages = []

# 实现三种内存类型
class ConversationBufferMemory(SimpleMemory):
    """保存完整对话历史的记忆类"""
    pass

class ConversationBufferWindowMemory(SimpleMemory):
    """保存固定窗口大小的对话历史的记忆类"""
    
    def __init__(self, k=5, return_messages=True, memory_key="history"):
        super().__init__(return_messages=return_messages, memory_key=memory_key)
        self.k = k
        
    @property
    def messages(self) -> List[BaseMessage]:
        """获取最近的k轮对话"""
        return self.chat_memory.messages[-2*self.k:] if self.chat_memory.messages else []
    
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """加载记忆变量，供RunnableWithMessageHistory使用"""
        if self.return_messages:
            return {self.memory_key: self.messages}
        
        # 如果不需要返回消息对象，则将消息转换为字符串
        result = []
        for message in self.messages:
            if isinstance(message, HumanMessage):
                result.append(f"Human: {message.content}")
            elif isinstance(message, AIMessage):
                result.append(f"AI: {message.content}")
            # 忽略系统消息
        
        # 返回字符串形式的历史
        return {self.memory_key: "\n".join(result)}

class ConversationSummaryMemory(SimpleMemory):
    """使用摘要记录对话历史的记忆类"""
    
    def __init__(self, llm=None, return_messages=True, memory_key="history"):
        super().__init__(return_messages=return_messages, memory_key=memory_key)
        self.llm = llm


class ChatChat_prompt:
    """
    聊天处理类，负责处理用户输入并生成回复
    """
    
    def __init__(self, memory_type="buffer", memory_k=5):
        """
        初始化聊天助手
        
        Args:
            memory_type: 聊天历史记忆类型（buffer, window 或 summary）
                         buffer - 保存完整历史
                         window - 只保留最近k轮对话
                         summary - 压缩历史为摘要
            memory_k: 窗口记忆中保留的对话轮数
        """
        # 初始化会话ID
        self.session_id = f"chat_{int(time.time())}"
        
        # 设置系统提示词
        self.system_prompt = """
        你是一个功能强大的AI助手，能够针对用户的各种请求提供信息、解释和建议。
        在回复中尽量简明扼要并使用适当的结构。如果遇到不确定的问题，应坦诚承认，
        并说明局限性。优先使用中文回答。
        """
        
        # 初始化记忆类型
        self.memory_type = memory_type
        self.memory_k = memory_k
        
        # 开启Markdown格式化功能
        self.enable_markdown = True
        
        # 初始化LLM
        self._initialize_llm()
            
        # 设置输出解析器
        self.parser = StrOutputParser()
        
        # 初始化记忆组件
        self._init_memory()
        
        # 设置提示词模板
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("placeholder", "{history}"),
            ("user", "{input}"),
        ])
    
    def _initialize_llm(self):
        """初始化大语言模型"""
        try:
            # 尝试初始化LLM
            print(f"正在初始化LLM，使用API: {load_key('OPENAI_BASE_URL')}, 模型: {load_key('OPENAI_API_MODEL')}")
            
            # 创建ChatOpenAI对象，添加请求超时和重试参数
            self.llm = ChatOpenAI(
                model_name=load_key("OPENAI_API_MODEL"),  # 如：deepseek-chat
                openai_api_key=load_key("OPENAI_API_KEY"),
                openai_api_base=load_key("OPENAI_BASE_URL"),  # 如: https://api.deepseek.com
                temperature=0.7,  # 控制随机性
                # 添加超时和重试配置
                request_timeout=load_key("OPENAI_TIMEOUT"),  # 请求超时时间 
                max_retries=load_key("OPENAI_MAX_RETRIES"),  # 最大重试次数
                streaming=True  # 启用流式输出
            )
            print("LLM初始化成功")
            self.is_mock = False
        except Exception as e:
            print(f"初始化LLM失败: {str(e)}")
            import traceback
            print(traceback.format_exc())  # 打印详细错误堆栈
            # 抛出异常而不使用模拟模式
            raise ValueError(f"无法连接到AI服务: {str(e)}")
    
    def _init_memory(self):
        """初始化不同类型的记忆组件"""
        # 保存记忆组件的字典
        self.memories = {}
        
        # 初始化 Buffer 记忆 (完整历史)
        self.memories["buffer"] = ConversationBufferMemory(
            return_messages=True,
            memory_key="history"
        )
        
        # 初始化 Window 记忆 (窗口历史，只保留最近k轮对话)
        self.memories["window"] = ConversationBufferWindowMemory(
            k=self.memory_k,
            return_messages=True,
            memory_key="history"
        )
        
        # 初始化 Summary 记忆 (摘要历史，压缩历史对话)
        # 注意：Summary记忆需要一个LLM来生成摘要，如果没有可用LLM，会返回空
        try:
            summary_llm = ChatOpenAI(
                model_name=load_key("OPENAI_API_MODEL"),  # 使用配置中的模型（deepseek-chat）
                openai_api_key=load_key("OPENAI_API_KEY"),
                openai_api_base=load_key("OPENAI_BASE_URL"),
                # 添加超时和重试配置，增强对API不稳定情况的处理
                request_timeout=load_key("OPENAI_TIMEOUT"),  # 请求超时时间
                max_retries=load_key("OPENAI_MAX_RETRIES"),  # 最大重试次数
                # 流式响应设置
                streaming=False
            )
            
            self.memories["summary"] = ConversationSummaryMemory(
                llm=summary_llm,
                return_messages=True,
                memory_key="history"
            )
            print("摘要记忆初始化成功")
        except Exception as e:
            # 如果无法初始化摘要记忆，则使用缓冲记忆代替
            print(f"摘要记忆初始化失败，使用缓冲记忆代替: {e}")
            self.memories["summary"] = self.memories["buffer"]
    
    def _get_session_history(self, session_id: str):
        """获取指定会话ID的历史记忆组件
        
        Args:
            session_id: 会话ID
            
        Returns:
            指定类型的历史记忆组件
        """
        # 确保当前设置的记忆类型存在
        if self.memory_type not in self.memories:
            print(f"记忆类型 {self.memory_type} 不存在，使用默认buffer类型")
            self.memory_type = "buffer"
            
        # 返回当前配置的记忆类型组件
        memory = self.memories[self.memory_type]
        return memory
    
    def set_memory_type(self, memory_type: str):
        """
        设置记忆类型
        
        Args:
            memory_type: 记忆类型，可选 "buffer", "window", "summary"
        """
        if memory_type in self.memories:
            self.memory_type = memory_type
            return True
        return False
    
    def set_system_prompt(self, prompt):
        """
        设置系统提示词
        
        Args:
            prompt: 新的系统提示词文本
        """
        if prompt and prompt.strip():
            self.system_prompt = prompt.strip()
            print(f"已设置新的系统提示词: {self.system_prompt}")
            return True
        return False
    
    def set_temperature(self, temperature):
        """
        设置AI回复的温度值
        
        Args:
            temperature: 浮点数，范围0.0到1.0，控制回复的随机性
                         较低的值(如0.1)使回复更确定、更一致
                         较高的值(如0.9)使回复更随机、更创意
                         
        Returns:
            bool: 设置是否成功
        """
        try:
            temp_value = float(temperature)
            if 0.0 <= temp_value <= 1.0:
                # 如果LLM已初始化，更新其温度参数
                if hasattr(self, 'llm') and not self.is_mock:
                    self.llm.temperature = temp_value
                    print(f"已更新LLM温度为: {temp_value}")
                
                return True
            else:
                print(f"温度值 {temperature} 超出有效范围(0.0-1.0)，使用默认值")
                return False
        except (ValueError, TypeError) as e:
            print(f"设置温度出错: {e}，使用默认值")
            return False
    
    def format_response_as_markdown(self, response: str) -> str:
        """
        将普通文本回复格式化为更好的Markdown格式
        
        Args:
            response: AI生成的原始回复
            
        Returns:
            格式化后的Markdown文本
        """
        if not self.enable_markdown or not response:
            return response
            
        # 已经包含Markdown语法标记的情况下，不做多余处理
        if "```" in response or "###" in response or "- " in response:
            return response
            
        # 将长段落分成更小的段落
        paragraphs = response.split("\n\n")
        formatted_paragraphs = []
        
        for i, para in enumerate(paragraphs):
            # 跳过空段落
            if not para.strip():
                continue
                
            # 第一段可以作为摘要或引言
            if i == 0 and len(para) > 50 and len(paragraphs) > 1:
                formatted_paragraphs.append(f"> {para}\n")
            # 检测是否可以转化为标题
            elif para.strip().endswith("：") or para.strip().endswith(":"):
                title = para.strip().rstrip("：").rstrip(":")
                formatted_paragraphs.append(f"### {title}\n")
            # 检测是否是列表内容
            elif "，" in para and len(para.split("，")) > 3:
                items = para.split("，")
                list_items = "\n".join([f"- {item.strip()}" for item in items if item.strip()])
                formatted_paragraphs.append(list_items)
            # 普通段落
            else:
                formatted_paragraphs.append(para)
        
        # 组合处理后的段落
        formatted_response = "\n\n".join(formatted_paragraphs)
        
        return formatted_response
    
    def chat(self, message: str) -> str:
        """
        处理用户消息并返回完整回复
        
        Args:
            message: 用户输入的消息
            
        Returns:
            完整的回复内容
        """
        try:
            # 更新提示模板以使用当前系统提示词
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt),
                ("placeholder", "{history}"),
                ("user", "{input}"),
            ])
            
            # 重建处理链
            chain = self.prompt | self.llm | self.parser
            
            # 将链与记忆组件结合
            self.chain_with_history = RunnableWithMessageHistory(
                chain,
                self._get_session_history,
                input_messages_key="input",
                history_messages_key="history",
            )
            
            # 使用带记忆的链处理输入
            response = self.chain_with_history.invoke(
                {"input": message},
                config={"configurable": {"session_id": self.session_id}}
            )
            
            # 如果启用了Markdown格式，格式化回复
            if self.enable_markdown:
                response = self.format_response_as_markdown(response)
                
            return response
        except Exception as e:
            print(f"LangChain调用失败: {e}")
            import traceback
            print(traceback.format_exc())
            # 不使用模拟数据，而是返回错误信息
            raise ValueError(f"AI回复生成失败: {str(e)}")
    
    def chat_stream(self, message: str) -> Generator[str, None, None]:
        """
        处理用户消息并以流式方式返回回复
        
        Args:
            message: 用户输入的消息
            
        Yields:
            回复内容的片段
        """
        full_response = ""
        # 获取当前会话的记忆组件
        memory = self._get_session_history(self.session_id)
        
        try:
            # 获取历史消息但不包括当前消息
            history_messages = list(memory.messages) if hasattr(memory, 'messages') and memory.messages else []
            
            # 创建一个包含系统提示词和历史消息的列表
            messages = [
                SystemMessage(content=self.system_prompt)  # 使用设置的系统提示词
            ]
            
            # 添加历史消息，但限制历史消息数量，减少负载
            if history_messages and len(history_messages) > 0:
                # 只保留最近的对话，更多的历史可能会减慢响应速度
                recent_history = history_messages[-8:] if len(history_messages) > 8 else history_messages
                messages.extend(recent_history)
            
            # 添加当前用户消息
            current_message = HumanMessage(content=message)
            messages.append(current_message)
            
            # 直接将用户消息添加到记忆（不通过RunnableWithMessageHistory）
            memory.chat_memory.add_user_message(message)
            
            # 直接使用llm和消息列表进行流式调用
            buffer = ""
            buffer_size = 5  # 减小缓冲区大小，避免长时间阻塞
            
            # 设置超时时间和容错重试
            import time
            last_chunk_time = time.time()
            timeout_seconds = 30  # 30秒超时
            
            print(f"开始从API接收流式响应...")
            
            for chunk in self.llm.stream(messages):
                # 更新最后接收块的时间
                last_chunk_time = time.time()
                
                # 从响应中获取内容
                if hasattr(chunk, 'content'):
                    content = chunk.content
                else:
                    content = str(chunk)
                
                if not content:  # 跳过空内容
                    continue
                    
                buffer += content
                full_response += content
                
                # 当缓冲区达到一定大小时才发送，或每200ms强制发送
                if len(buffer) >= buffer_size:
                    yield buffer
                    buffer = ""
                    
                    # 添加调试日志
                    print(f"已发送响应片段，长度:{len(buffer)}")
            
            # 发送剩余缓冲区内容
            if buffer:
                yield buffer
                print(f"已发送最后响应片段，长度:{len(buffer)}")
                
            print(f"API流式响应接收完成")
        except Exception as e:
            print(f"流式输出失败: {e}")
            import traceback
            print(traceback.format_exc())  # 打印完整错误堆栈，方便调试
            # 错误信息流式输出
            error_msg = f"AI回复生成失败: {str(e)[:100]}... 请稍后再试"
            yield error_msg
            full_response += error_msg
        
        # 如果启用了Markdown格式，格式化完整响应
        if self.enable_markdown:
            full_response = self.format_response_as_markdown(full_response)
        
        # 直接将AI回复添加到记忆（不通过RunnableWithMessageHistory）
        memory.chat_memory.add_ai_message(full_response)
    
    def clear_history(self):
        """清除聊天历史"""
        for memory_type, memory in self.memories.items():
            memory.clear()
        # 重新生成会话ID
        self.session_id = f"chat_{int(time.time())}"
    
    def set_markdown_mode(self, enable: bool) -> bool:
        """
        设置是否启用Markdown格式输出
        
        Args:
            enable: 是否启用Markdown格式
                    
        Returns:
            bool: 设置是否成功
        """
        self.enable_markdown = bool(enable)
        
        # 如果启用Markdown，更新系统提示词以引导模型使用Markdown
        if self.enable_markdown and "Markdown" not in self.system_prompt:
            self.system_prompt += " 尽可能使用Markdown格式回复，可以使用标题、列表、表格、代码块等Markdown语法使回答更加结构化和易读。"
        
        return True


if __name__ == "__main__":
    chat = ChatChat_prompt()
    # 测试流式输出
    for chunk in chat.chat_stream("介绍一下你自己，分成多个部分逐步输出"):
        print(chunk, end="", flush=True)  # 立即显示每个输出块
