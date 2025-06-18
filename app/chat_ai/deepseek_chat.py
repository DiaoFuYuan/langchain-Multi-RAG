import time
import requests
import json
from typing import Generator, Optional
import logging

logger = logging.getLogger(__name__)

class DeepSeekChat:
    """
    DeepSeek聊天处理类，专门用于与DeepSeek API进行交互
    """
    
    def __init__(self, api_key: str, model_name: str = "deepseek-chat", endpoint: str = "https://api.deepseek.com"):
        """
        初始化DeepSeek聊天助手
        
        Args:
            api_key: DeepSeek API密钥
            model_name: 模型名称，默认为deepseek-chat
            endpoint: API端点，默认为https://api.deepseek.com
        """
        self.api_key = api_key
        self.model_name = model_name
        self.endpoint = endpoint.rstrip('/')
        self.chat_url = f"{self.endpoint}/v1/chat/completions"
        
        # 设置默认系统提示词
        self.system_prompt = """你是一个功能强大的AI助手，能够针对用户的各种请求提供信息、解释和建议。
在回复中尽量简明扼要并使用适当的结构。如果遇到不确定的问题，应坦诚承认，
并说明局限性。优先使用中文回答。"""
        
        # 设置默认温度
        self.temperature = 0.7
        
        # 对话历史
        self.conversation_history = []
        
        logger.info(f"DeepSeek聊天实例已初始化，模型: {model_name}, 端点: {endpoint}")
    
    def set_system_prompt(self, prompt: str) -> bool:
        """
        设置系统提示词
        
        Args:
            prompt: 系统提示词
            
        Returns:
            bool: 设置是否成功
        """
        try:
            if prompt and isinstance(prompt, str):
                self.system_prompt = prompt
                logger.info("系统提示词已更新")
                return True
            return False
        except Exception as e:
            logger.error(f"设置系统提示词失败: {str(e)}")
            return False
    
    def set_temperature(self, temperature: float) -> bool:
        """
        设置温度值
        
        Args:
            temperature: 温度值，范围0-2
            
        Returns:
            bool: 设置是否成功
        """
        try:
            if 0 <= temperature <= 2:
                self.temperature = temperature
                logger.info(f"温度值已设置为: {temperature}")
                return True
            return False
        except Exception as e:
            logger.error(f"设置温度值失败: {str(e)}")
            return False
    
    def _prepare_messages(self, user_message: str) -> list:
        """
        准备发送给API的消息列表
        
        Args:
            user_message: 用户消息
            
        Returns:
            list: 格式化的消息列表
        """
        messages = []
        
        # 添加系统消息
        if self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })
        
        # 添加对话历史
        messages.extend(self.conversation_history)
        
        # 添加当前用户消息
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        return messages
    
    def chat(self, message: str) -> str:
        """
        发送消息并获取完整回复
        
        Args:
            message: 用户消息
            
        Returns:
            str: AI回复
        """
        try:
            messages = self._prepare_messages(message)
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
                "stream": False
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.chat_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                choice = result["choices"][0]
                message_obj = choice["message"]
                
                ai_response = message_obj.get("content", "")
                reasoning_content = message_obj.get("reasoning_content", "")
                
                # 如果有思考过程，将其包含在回复中
                full_response = ai_response
                if reasoning_content:
                    full_response = f"**🤔 思考过程：**\n\n```thinking\n{reasoning_content}\n```\n\n**💭 回答：**\n\n{ai_response}"
                
                # 更新对话历史
                self.conversation_history.append({
                    "role": "user",
                    "content": message
                })
                self.conversation_history.append({
                    "role": "assistant",
                    "content": full_response
                })
                
                # 保持历史长度在合理范围内（最近10轮对话）
                if len(self.conversation_history) > 20:
                    self.conversation_history = self.conversation_history[-20:]
                
                return full_response
            else:
                error_msg = f"API请求失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return f"抱歉，请求失败: {error_msg}"
                
        except Exception as e:
            error_msg = f"发送消息时出错: {str(e)}"
            logger.error(error_msg)
            return f"抱歉，发生错误: {error_msg}"
    
    def chat_stream(self, message: str) -> Generator[str, None, None]:
        """
        发送消息并获取流式回复
        
        Args:
            message: 用户消息
            
        Yields:
            str: AI回复的片段
        """
        try:
            messages = self._prepare_messages(message)
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
                "stream": True
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.chat_url,
                headers=headers,
                json=payload,
                timeout=30,
                stream=True
            )
            
            if response.status_code == 200:
                full_response = ""
                full_reasoning = ""
                thinking_started = False
                thinking_ended = False
                
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data = line[6:]  # 移除 'data: ' 前缀
                            
                            if data.strip() == '[DONE]':
                                break
                            
                            try:
                                json_data = json.loads(data)
                                if 'choices' in json_data and len(json_data['choices']) > 0:
                                    choice = json_data['choices'][0]
                                    delta = choice.get('delta', {})
                                    
                                    # 处理思考过程（reasoning_content）
                                    reasoning_content = delta.get('reasoning_content', '')
                                    if reasoning_content:
                                        full_reasoning += reasoning_content
                                        if not thinking_started:
                                            thinking_started = True
                                            yield "\n\n**🤔 思考过程：**\n\n"
                                            yield "```thinking\n"
                                        yield reasoning_content
                                    
                                    # 处理普通回复内容
                                    content = delta.get('content', '')
                                    if content:
                                        # 如果之前有思考过程，先结束思考块
                                        if thinking_started and not thinking_ended:
                                            thinking_ended = True
                                            yield "\n```\n\n**💭 回答：**\n\n"
                                        
                                        full_response += content
                                        yield content
                                        
                            except json.JSONDecodeError:
                                continue
                
                # 更新对话历史
                if full_response or full_reasoning:
                    self.conversation_history.append({
                        "role": "user",
                        "content": message
                    })
                    
                    # 如果有思考过程，将其包含在助手回复中
                    assistant_content = full_response
                    if full_reasoning:
                        assistant_content = f"**思考过程：**\n{full_reasoning}\n\n**回答：**\n{full_response}"
                    
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": assistant_content
                    })
                    
                    # 保持历史长度在合理范围内
                    if len(self.conversation_history) > 20:
                        self.conversation_history = self.conversation_history[-20:]
            else:
                error_msg = f"API请求失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                yield f"抱歉，请求失败: {error_msg}"
                
        except Exception as e:
            error_msg = f"流式发送消息时出错: {str(e)}"
            logger.error(error_msg)
            yield f"抱歉，发生错误: {error_msg}"
    
    def clear_history(self):
        """清除对话历史"""
        self.conversation_history = []
        logger.info("对话历史已清除") 