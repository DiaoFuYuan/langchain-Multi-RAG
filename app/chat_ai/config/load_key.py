"""
API密钥加载和管理模块
从config.yaml配置文件或环境变量中加载API密钥和配置
"""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# 尝试加载.env文件中的环境变量
load_dotenv()

def load_yaml_config(config_file_path=None):
    """
    加载YAML配置文件
    
    Args:
        config_file_path: 配置文件路径，如果为None则使用默认路径
        
    Returns:
        包含配置信息的字典，加载失败则返回空字典
    """
    # 默认配置文件路径
    if config_file_path is None:
        # 根目录的config.yaml文件
        config_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'config.yaml')
    
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"加载YAML配置文件出错: {e}")
        return {}

def load_key(key_name=None):
    """
    加载指定的API密钥
    
    按照以下优先级加载配置:
    1. 环境变量
    2. config.yaml配置文件
    3. 默认值
    
    Args:
        key_name: 密钥名称，如果为None则返回所有密钥
        
    Returns:
        如果指定了key_name，返回对应的密钥值；
        如果key_name为None，返回包含所有密钥的字典
    """
    # 加载YAML配置
    config = load_yaml_config()
    
    # 从YAML配置中获取相关部分
    llm_config = config.get('llm', {})
    vllm_config = config.get('vllm', {})
    embedding_model_config = config.get('embedding_model', {})
    ollama_config = config.get('ollama', {})
    
    # 获取VLLM配置
    vllm_default_params = vllm_config.get('default_params', {})
    vllm_model_names = vllm_config.get('model_name', [])
    vllm_model_name = vllm_model_names[0] if vllm_model_names else "deepseek-chat"
    
    # 获取Ollama配置
    ollama_default_params = ollama_config.get('default_params', {})
    
    # 常用API密钥，按优先级加载：环境变量 > YAML配置 > 默认值
    keys = {
        # OpenAI/VLLM API密钥
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY") or 
                         vllm_config.get('api_key') or 
                         "sk-4d1c2f1ab80049f1a55b1e2e45694cc5",
        
        # OpenAI/VLLM基础URL
        "OPENAI_BASE_URL": os.getenv("OPENAI_BASE_URL") or 
                          vllm_config.get('url') or 
                          "https://api.deepseek.com",
        
        # OpenAI/VLLM模型
        "OPENAI_API_MODEL": os.getenv("OPENAI_API_MODEL") or 
                           vllm_model_name or 
                           "deepseek-chat",
        
        # HTTP请求超时时间
        "OPENAI_TIMEOUT": int(os.getenv("OPENAI_TIMEOUT") or "60"),
        
        # 最大重试次数
        "OPENAI_MAX_RETRIES": int(os.getenv("OPENAI_MAX_RETRIES") or "3"),
        
        # 模型参数 - 从VLLM/Ollama参数获取
        "OPENAI_TEMPERATURE": float(os.getenv("OPENAI_TEMPERATURE") or 
                                str(vllm_default_params.get('temperature', 0.7))),
        
        "OPENAI_TOP_P": float(os.getenv("OPENAI_TOP_P") or 
                          str(vllm_default_params.get('top_p', 0.95))),
        
        "OPENAI_MAX_TOKENS": int(os.getenv("OPENAI_MAX_TOKENS") or 
                             str(vllm_default_params.get('max_tokens', 4096))),
        
        # Embedding模型配置 - 从embedding_model部分获取
        "EMBEDDING_MODEL_PATH": os.getenv("EMBEDDING_MODEL_PATH") or 
                              embedding_model_config.get('path') or 
                              "app/ai_tools/embedding_model/text2vec-base-chinese",
        
        "EMBEDDING_MODEL_TYPE": os.getenv("EMBEDDING_MODEL_TYPE") or 
                              embedding_model_config.get('type') or 
                              "text2vec",
        
        # Ollama相关配置
        "OLLAMA_URL": os.getenv("OLLAMA_URL") or 
                    ollama_config.get('url') or 
                    "http://localhost:11434",
                    
        "OLLAMA_MODELS": ollama_config.get('models', ["llama3", "mistral", "qwen:14b"])
    }
    
    # 检查API密钥是否正确配置
    if not keys["OPENAI_API_KEY"] or keys["OPENAI_API_KEY"] == "your_api_key_here":
        print("警告: OPENAI_API_KEY 未正确配置，请在config.yaml或环境变量中设置有效的API密钥")
    
    # 返回指定密钥或所有密钥
    if key_name:
        return keys.get(key_name, "")
    return keys 