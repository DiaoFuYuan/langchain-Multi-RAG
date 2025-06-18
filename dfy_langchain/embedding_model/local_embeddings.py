"""
Embedding模型实现

提供本地模型和远程API两种embedding方式
支持从数据库配置中获取embedding模型信息
"""

import os
import logging
import httpx
import asyncio
from typing import List, Dict, Any, Union, Optional

import torch
import numpy as np
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)

# 尝试导入必要的依赖
try:
    from transformers import AutoTokenizer, AutoModel
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("transformers库未安装，无法使用本地embedding模型")
    TRANSFORMERS_AVAILABLE = False

def _get_optimal_device():
    """获取最佳可用设备"""
    try:
        import torch_npu
        if torch.npu.is_available():
            return "npu:0"
    except ImportError:
        pass
    
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


class RemoteEmbeddings(Embeddings):
    """
    远程API Embedding模型实现
    """
    
    def __init__(
        self,
        api_key: str,
        endpoint: str,
        model_name: str,
        timeout: int = 30,
        max_batch_size: int = 100,
    ):
        """
        初始化远程Embedding模型
        
        Args:
            api_key: API密钥
            endpoint: API端点
            model_name: 模型名称
            timeout: 请求超时时间
            max_batch_size: 批处理大小
        """
        self.api_key = api_key
        self.endpoint = endpoint.rstrip('/')
        self.model_name = model_name
        self.timeout = timeout
        self.max_batch_size = max_batch_size
        
        # 确保端点格式正确
        if not self.endpoint.startswith('http'):
            self.endpoint = f"https://{self.endpoint}"
        
        # 构建完整的API URL
        self.embedding_url = self._build_embedding_url()
        
        logger.info(f"初始化远程embedding模型: {model_name}, 端点: {self.embedding_url}")
    
    def _build_embedding_url(self) -> str:
        """构建embedding API URL"""
        # 尝试不同的URL格式
        possible_paths = [
            "/v1/embeddings",
            "/embeddings",
        ]
        
        for path in possible_paths:
            if path in self.endpoint:
                return self.endpoint
        
        # 默认添加 /v1/embeddings
        if self.endpoint.endswith('/v1'):
            return f"{self.endpoint}/embeddings"
        else:
            return f"{self.endpoint}/v1/embeddings"
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        对文档列表进行嵌入
        
        Args:
            texts: 文档列表
            
        Returns:
            嵌入向量列表
        """
        try:
            if not texts:
                return []
            
            batch_size = self.max_batch_size
            all_embeddings = []
            
            # 特殊处理：对于结构化数据（如Excel），使用更小的批次
            if self._is_structured_data(texts):
                batch_size = min(batch_size, 5)  # 减小批次大小
                print(f"检测到结构化数据，使用较小批次大小: {batch_size}")
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                # 对于大型批次，添加延迟减少服务器压力
                if len(texts) > 10 and i > 0:
                    import time
                    time.sleep(0.5)  # 500ms延迟
                
                batch_embeddings = self._embed_texts_with_retry(batch_texts)
                all_embeddings.extend(batch_embeddings)
            
            return all_embeddings
            
        except Exception as e:
            print(f"批量embedding失败: {e}")
            # 如果批量失败，尝试逐个处理
            return self._fallback_single_embedding(texts)
    
    def embed_query(self, text: str) -> List[float]:
        """
        对查询文本进行嵌入
        
        Args:
            text: 查询文本
            
        Returns:
            嵌入向量
        """
        embeddings = self._embed_texts([text])
        return embeddings[0] if embeddings else []
    
    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        调用远程API进行文本嵌入
        
        Args:
            texts: 文本列表
            
        Returns:
            嵌入向量列表
        """
        try:
            # 设置请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # 构建请求数据
            data = {
                "model": self.model_name,
                "input": texts
            }
            
            # 更健壮的异步处理逻辑
            return self._handle_async_embedding(headers, data)
            
        except Exception as e:
            logger.error(f"远程embedding API调用失败: {e}")
            raise
    
    def _handle_async_embedding(self, headers: Dict[str, str], data: Dict[str, Any]) -> List[List[float]]:
        """
        处理异步embedding调用的统一入口
        
        Args:
            headers: 请求头
            data: 请求数据
            
        Returns:
            嵌入向量列表
        """
        # 方法1: 尝试检查是否在事件循环中
        try:
            loop = asyncio.get_running_loop()
            if loop and loop.is_running():
                # 在运行的事件循环中，使用线程池
                logger.debug("检测到运行中的事件循环，使用线程池执行")
                return self._run_in_thread_pool(headers, data)
            else:
                # 事件循环未运行，使用asyncio.run
                logger.debug("事件循环未运行，使用asyncio.run")
                return asyncio.run(self._async_embed_texts(headers, data))
        except RuntimeError:
            # 方法2: 没有事件循环，直接使用asyncio.run
            logger.debug("无事件循环，使用asyncio.run")
            try:
                return asyncio.run(self._async_embed_texts(headers, data))
            except RuntimeError as run_error:
                # 方法3: 如果asyncio.run也失败，使用同步HTTP请求作为后备
                logger.warning(f"asyncio.run失败: {run_error}，使用同步HTTP请求作为后备")
                return self._sync_http_request(headers, data)
        except Exception as e:
            # 方法4: 所有异步方法都失败，使用同步HTTP请求
            logger.warning(f"异步方法失败: {e}，使用同步HTTP请求")
            return self._sync_http_request(headers, data)
    
    def _run_in_thread_pool(self, headers: Dict[str, str], data: Dict[str, Any]) -> List[List[float]]:
        """
        在线程池中运行异步方法
        """
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self._sync_embed_texts, headers, data)
            return future.result()
    
    def _sync_http_request(self, headers: Dict[str, str], data: Dict[str, Any]) -> List[List[float]]:
        """
        使用同步HTTP请求作为后备方案
        
        Args:
            headers: 请求头
            data: 请求数据
            
        Returns:
            嵌入向量列表
        """
        import requests
        
        logger.info("使用同步HTTP请求调用远程embedding API")
        
        try:
            response = requests.post(
                self.embedding_url,
                json=data,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            # 解析响应
            if "data" in result and isinstance(result["data"], list):
                embeddings = []
                for item in result["data"]:
                    if "embedding" in item:
                        embeddings.append(item["embedding"])
                    else:
                        logger.warning(f"API响应中缺少embedding字段: {item}")
                
                if len(embeddings) != len(data["input"]):
                    logger.warning(f"返回的embedding数量({len(embeddings)})与输入文本数量({len(data['input'])})不匹配")
                
                return embeddings
            else:
                logger.error(f"API响应格式不正确: {result}")
                raise ValueError(f"API响应格式不正确: {result}")
                
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP错误: {e.response.status_code} - {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"请求错误: {e}")
            raise
    
    def _sync_embed_texts(self, headers: Dict[str, str], data: Dict[str, Any]) -> List[List[float]]:
        """
        在新的事件循环中同步调用异步方法
        
        Args:
            headers: 请求头
            data: 请求数据
            
        Returns:
            嵌入向量列表
        """
        # 在新线程中创建新的事件循环
        return asyncio.run(self._async_embed_texts(headers, data))
    
    async def _async_embed_texts(self, headers: Dict[str, str], data: Dict[str, Any]) -> List[List[float]]:
        """
        异步调用远程API
        
        Args:
            headers: 请求头
            data: 请求数据
            
        Returns:
            嵌入向量列表
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(self.embedding_url, json=data, headers=headers)
                response.raise_for_status()
                
                result = response.json()
                
                # 解析响应
                if "data" in result and isinstance(result["data"], list):
                    embeddings = []
                    for item in result["data"]:
                        if "embedding" in item:
                            embeddings.append(item["embedding"])
                        else:
                            logger.warning(f"API响应中缺少embedding字段: {item}")
                    
                    if len(embeddings) != len(data["input"]):
                        logger.warning(f"返回的embedding数量({len(embeddings)})与输入文本数量({len(data['input'])})不匹配")
                    
                    return embeddings
                else:
                    logger.error(f"API响应格式不正确: {result}")
                    raise ValueError(f"API响应格式不正确: {result}")
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP错误: {e.response.status_code} - {e.response.text}")
                raise
            except httpx.RequestError as e:
                logger.error(f"请求错误: {e}")
                raise
    
    def _is_structured_data(self, texts: List[str]) -> bool:
        """检测是否为结构化数据（如Excel格式）"""
        if not texts:
            return False
        
        sample_text = texts[0]
        # 检查是否包含大量键值对格式
        colon_count = sample_text.count(':')
        line_count = len(sample_text.split('\n'))
        
        # 如果冒号数量超过行数的60%，认为是结构化数据
        return line_count > 10 and colon_count > line_count * 0.6
    
    def _embed_texts_with_retry(self, texts: List[str], max_retries: int = 3) -> List[List[float]]:
        """带重试机制的文本嵌入"""
        for attempt in range(max_retries):
            try:
                return self._embed_texts(texts)
            except Exception as e:
                if "500" in str(e) and attempt < max_retries - 1:
                    # 500错误时增加等待时间
                    import time
                    wait_time = (attempt + 1) * 2  # 递增等待时间
                    print(f"Embedding失败(尝试{attempt + 1}/{max_retries})，{wait_time}秒后重试: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    raise e
        
        # 如果所有重试都失败，抛出最后的异常
        raise Exception(f"经过{max_retries}次重试后仍然失败")
    
    def _fallback_single_embedding(self, texts: List[str]) -> List[List[float]]:
        """备用方案：逐个处理文本"""
        print("使用备用方案：逐个处理文本")
        all_embeddings = []
        
        for i, text in enumerate(texts):
            try:
                # 更长的延迟以避免服务器压力
                if i > 0:
                    import time
                    time.sleep(1.0)  # 1秒延迟
                
                embedding = self._embed_texts_with_retry([text])
                all_embeddings.extend(embedding)
                print(f"成功处理文本 {i+1}/{len(texts)}")
                
            except Exception as e:
                print(f"文本 {i+1} 处理失败: {e}")
                # 创建零向量作为后备
                dimension = 1536  # 默认维度
                all_embeddings.append([0.0] * dimension)
        
        return all_embeddings


class LocalEmbeddings(Embeddings):
    """
    本地Embedding模型的基类
    """
    
    def __init__(
        self,
        model_name: str,
        model_path: Optional[str] = None,
        cache_dir: Optional[str] = None,
        device: Optional[str] = None,
        normalize_embeddings: bool = True,
    ):
        """
        初始化本地Embedding模型
        
        Args:
            model_name: 模型名称
            model_path: 模型路径，如果为None则使用默认路径
            cache_dir: 缓存目录
            device: 设备，如果为None则自动选择
            normalize_embeddings: 是否规范化嵌入向量
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "本地embedding模型依赖transformers库。"
                "请使用 pip install transformers 安装。"
            )
        
        self.model_name = model_name
        self.model_path = model_path or model_name
        self.cache_dir = cache_dir
        self.normalize_embeddings = normalize_embeddings
        
        # 设置设备
        if device is None:
            self.device = _get_optimal_device()
        else:
            self.device = device
        
        logger.info(f"初始化本地embedding模型 {model_name} 在 {self.device} 设备上")
        
        # 加载tokenizer和模型
        self._init_model()
    
    def _init_model(self):
        """
        初始化模型和tokenizer
        """
        try:
            kwargs = {}
            if self.cache_dir:
                kwargs["cache_dir"] = self.cache_dir
            
            # 更严格地检查本地路径
            is_local_path = False
            local_paths_to_check = [
                self.model_path,  # 原始路径
                os.path.abspath(self.model_path),  # 绝对路径
                os.path.join(os.getcwd(), self.model_path),  # 相对于当前工作目录
            ]
            
            # 检查默认模型目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            model_dirs = [
                os.path.join(current_dir, self.model_name),
                os.path.join(current_dir, "..", "embedding_model", self.model_name),
                os.path.join(os.path.dirname(current_dir), "embedding_model", self.model_name),
            ]
            local_paths_to_check.extend(model_dirs)
            
            # 记录所有尝试的路径，方便调试
            logger.debug(f"尝试以下路径寻找本地模型:")
            for path in local_paths_to_check:
                logger.debug(f"  - {path}")
                if os.path.exists(path) and os.path.isdir(path):
                    logger.info(f"找到本地模型目录: {path}")
                    self.model_path = path
                    is_local_path = True
                    break
            
            if is_local_path:
                # 从本地路径加载
                logger.info(f"从本地路径加载模型: {self.model_path}")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, **kwargs)
                self.model = AutoModel.from_pretrained(self.model_path, **kwargs)
            else:
                # 如果不是指向本地路径，再尝试从Hugging Face加载
                logger.warning(f"未找到本地模型路径，尝试从Hugging Face加载模型: {self.model_name}")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, **kwargs)
                self.model = AutoModel.from_pretrained(self.model_name, **kwargs)
            
            self.model = self.model.to(self.device)
            self.model.eval()
            
            logger.info(f"模型 {self.model_name} 初始化成功")
        except Exception as e:
            logger.error(f"初始化模型 {self.model_name} 时出错: {str(e)}")
            raise
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        对文档列表进行嵌入
        
        Args:
            texts: 文档列表
            
        Returns:
            嵌入向量列表
        """
        embeddings = []
        for text in texts:
            embedding = self.embed_query(text)
            embeddings.append(embedding)
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """
        对查询文本进行嵌入
        
        Args:
            text: 查询文本
            
        Returns:
            嵌入向量
        """
        # 这是一个基类方法，应该由子类实现
        raise NotImplementedError("embed_query方法应该由子类实现")


class LocalHuggingFaceEmbeddings(LocalEmbeddings):
    """
    基于HuggingFace的本地Embedding模型实现
    """
    
    def __init__(
        self,
        model_name: str,
        model_path: Optional[str] = None,
        cache_dir: Optional[str] = None,
        device: Optional[str] = None,
        normalize_embeddings: bool = True,
        max_length: int = 512,
        pooling_strategy: str = "mean",
    ):
        """
        初始化HuggingFace本地Embedding模型
        
        Args:
            model_name: 模型名称
            model_path: 模型路径，如果为None则使用默认路径
            cache_dir: 缓存目录
            device: 设备，如果为None则自动选择
            normalize_embeddings: 是否规范化嵌入向量
            max_length: 最大长度
            pooling_strategy: 池化策略，可选值: mean, cls, first_last_avg
        """
        self.max_length = max_length
        self.pooling_strategy = pooling_strategy
        
        super().__init__(
            model_name=model_name,
            model_path=model_path,
            cache_dir=cache_dir,
            device=device,
            normalize_embeddings=normalize_embeddings,
        )
    
    def embed_query(self, text: str) -> List[float]:
        """
        对查询文本进行嵌入
        
        Args:
            text: 查询文本
            
        Returns:
            嵌入向量
        """
        return self._get_embedding(text)
    
    def _get_embedding(self, text: str) -> List[float]:
        """
        获取文本的嵌入向量
        
        Args:
            text: 文本
            
        Returns:
            嵌入向量
        """
        # 使用tokenizer进行编码
        inputs = self.tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt"
        ).to(self.device)
        
        # 关闭梯度计算，减少内存使用
        with torch.no_grad():
            outputs = self.model(**inputs)
            
            # 根据不同的池化策略获取嵌入向量
            if self.pooling_strategy == "cls":
                # 使用[CLS]标记的嵌入作为文本的表示
                embeddings = outputs.last_hidden_state[:, 0, :]
            elif self.pooling_strategy == "mean":
                # 使用所有标记的平均嵌入
                attention_mask = inputs["attention_mask"]
                embeddings = self._mean_pooling(outputs.last_hidden_state, attention_mask)
            elif self.pooling_strategy == "first_last_avg":
                # 使用第一层和最后一层的平均嵌入
                first_hidden = outputs.hidden_states[1]
                last_hidden = outputs.hidden_states[-1]
                attention_mask = inputs["attention_mask"]
                first_mean = self._mean_pooling(first_hidden, attention_mask)
                last_mean = self._mean_pooling(last_hidden, attention_mask)
                embeddings = (first_mean + last_mean) / 2
            else:
                raise ValueError(f"不支持的池化策略: {self.pooling_strategy}")
        
        # 规范化嵌入向量
        if self.normalize_embeddings:
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        
        # 转换为列表
        embeddings_list = embeddings[0].cpu().numpy().tolist()
        
        return embeddings_list
    
    def _mean_pooling(self, token_embeddings, attention_mask):
        """
        对标记嵌入进行平均池化
        
        Args:
            token_embeddings: 标记嵌入
            attention_mask: 注意力掩码
            
        Returns:
            池化后的嵌入向量
        """
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


def get_embedding_from_config(config_id: Optional[int] = None, config: Optional[Dict] = None) -> Embeddings:
    """
    从数据库配置获取embedding模型
    
    Args:
        config_id: 配置ID
        config: 配置字典（如果提供，则直接使用，否则从数据库查询）
        
    Returns:
        Embedding模型实例
    """
    if config is None and config_id is not None:
        # 从数据库获取配置
        try:
            # 导入必要的模块
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
            
            from app.services.model_config_service import ModelConfigService
            from app.database import get_db
            
            # 获取数据库连接
            db = next(get_db())
            model_config = ModelConfigService.get_model_config_by_id(db, config_id)
            
            if not model_config:
                raise ValueError(f"未找到ID为 {config_id} 的模型配置")
            
            if model_config.model_type != "embedding":
                raise ValueError(f"配置ID {config_id} 不是embedding模型，而是 {model_config.model_type}")
            
            config = {
                "provider": model_config.provider,
                "model_name": model_config.model_name,
                "api_key": model_config.api_key,
                "endpoint": model_config.endpoint,
            }
            
        except Exception as e:
            logger.error(f"从数据库获取embedding配置失败: {e}")
            raise
    
    if not config:
        raise ValueError("必须提供config_id或config参数")
    
    provider = config.get("provider")
    model_name = config.get("model_name")
    
    if not provider or not model_name:
        raise ValueError("配置中缺少provider或model_name")
    
    if provider in ["openai-compatible", "openai", "deepseek", "anthropic", "vllm"]:
        # 使用远程API
        api_key = config.get("api_key")
        endpoint = config.get("endpoint")
        
        if not api_key:
            raise ValueError(f"{provider} provider需要api_key")
        
        # 为不同provider设置默认endpoint
        if not endpoint:
            default_endpoints = {
                "openai": "https://api.openai.com/v1",
                "deepseek": "https://api.deepseek.com/v1",
                "anthropic": "https://api.anthropic.com/v1",
                "vllm": "http://localhost:8000/v1"
            }
            endpoint = default_endpoints.get(provider)
            if not endpoint and provider != "openai-compatible":
                raise ValueError(f"{provider} provider需要endpoint")
        
        logger.info(f"创建远程embedding模型: {model_name} (provider: {provider})")
        return RemoteEmbeddings(
            api_key=api_key,
            endpoint=endpoint,
            model_name=model_name
        )
    
    elif provider in ["local", "huggingface"]:
        # 使用本地模型
        logger.info(f"创建本地embedding模型: {model_name}")
        return create_local_embeddings(model_name=model_name)
    
    else:
        # 对于未知的provider，尝试作为远程API处理
        logger.warning(f"未知的provider: {provider}，尝试作为远程API处理")
        api_key = config.get("api_key")
        endpoint = config.get("endpoint")
        
        if not api_key or not endpoint:
            raise ValueError(f"未知provider {provider} 需要api_key和endpoint")
        
        logger.info(f"创建远程embedding模型: {model_name} (未知provider: {provider})")
        return RemoteEmbeddings(
            api_key=api_key,
            endpoint=endpoint,
            model_name=model_name
        )


def create_local_embeddings(
    model_name: str = "bge-base-zh-v1.5",
    model_path: Optional[str] = None,
    cache_dir: Optional[str] = None,
    **kwargs
) -> Embeddings:
    """
    创建本地Embedding模型
    
    Args:
        model_name: 模型名称
        model_path: 模型路径，如果为None则使用默认路径
        cache_dir: 缓存目录
        **kwargs: 其他参数
        
    Returns:
        Embedding模型实例
    """
    # 如果提供的是路径，使用该路径的最后一部分作为模型名称
    if model_path and os.path.exists(model_path):
        model_name = os.path.basename(model_path)
    
    logger.info(f"创建本地embedding模型: {model_name}")
    
    # 根据不同的模型选择不同的默认参数
    if "bge" in model_name.lower():
        # BGE模型通常使用"cls"池化策略
        return LocalHuggingFaceEmbeddings(
            model_name=model_name,
            model_path=model_path,
            cache_dir=cache_dir,
            pooling_strategy="cls",
            **kwargs
        )
    elif "text2vec" in model_name.lower():
        # text2vec模型通常使用"mean"池化策略
        return LocalHuggingFaceEmbeddings(
            model_name=model_name,
            model_path=model_path,
            cache_dir=cache_dir,
            pooling_strategy="mean",
            **kwargs
        )
    elif "m3e" in model_name.lower():
        # M3E模型通常使用"mean"池化策略
        return LocalHuggingFaceEmbeddings(
            model_name=model_name,
            model_path=model_path,
            cache_dir=cache_dir,
            pooling_strategy="mean",
            **kwargs
        )
    else:
        # 默认使用"mean"池化策略
        return LocalHuggingFaceEmbeddings(
            model_name=model_name,
            model_path=model_path,
            cache_dir=cache_dir,
            **kwargs
        )


def create_embeddings(use_remote: bool = False, **kwargs) -> Embeddings:
    """
    创建embedding模型（根据参数决定使用本地还是远程）
    
    Args:
        use_remote: 是否使用远程API
        **kwargs: 其他参数
        
    Returns:
        Embedding模型实例
    """
    if use_remote:
        # 使用远程API
        required_keys = ["api_key", "endpoint", "model_name"]
        for key in required_keys:
            if key not in kwargs:
                raise ValueError(f"远程API模式需要参数: {key}")
        
        return RemoteEmbeddings(**kwargs)
    else:
        # 使用本地模型
        return create_local_embeddings(**kwargs)


 