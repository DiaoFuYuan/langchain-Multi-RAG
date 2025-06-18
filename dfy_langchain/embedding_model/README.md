# Embedding模型使用指南

本文档介绍如何使用本系统的embedding模型，支持本地模型和远程API两种方式。

## 功能特性

- ✅ **本地模型支持**：使用HuggingFace transformers加载本地embedding模型
- ✅ **远程API支持**：支持OpenAI-compatible API调用
- ✅ **数据库配置集成**：从数据库配置中自动获取embedding模型
- ✅ **自动设备检测**：支持NPU、CUDA、CPU自动选择
- ✅ **批处理优化**：支持批量文本处理
- ✅ **统一接口**：兼容LangChain Embeddings接口

## 快速开始

### 1. 使用本地embedding模型

```python
from embedding_model.local_embeddings import create_local_embeddings

# 创建本地embedding模型
embeddings = create_local_embeddings(
    model_name="bge-embedding-base_v1",
    model_path="/path/to/your/model"  # 可选，自动检测
)

# 对单个文本进行embedding
text = "这是一个测试文本"
embedding = embeddings.embed_query(text)
print(f"向量维度: {len(embedding)}")

# 对文档列表进行embedding
documents = ["文档1", "文档2", "文档3"]
doc_embeddings = embeddings.embed_documents(documents)
print(f"处理了 {len(doc_embeddings)} 个文档")
```

### 2. 使用远程API embedding模型

```python
from embedding_model.local_embeddings import RemoteEmbeddings

# 创建远程embedding模型
embeddings = RemoteEmbeddings(
    api_key="your-api-key",
    endpoint="https://api.openai.com/v1",
    model_name="text-embedding-ada-002"
)

# 使用方式与本地模型相同
embedding = embeddings.embed_query("测试文本")
```

### 3. 从数据库配置获取

```python
from embedding_model.local_embeddings import get_embedding_from_config

# 通过配置ID获取
embeddings = get_embedding_from_config(config_id=1)

# 或者直接传入配置字典
config = {
    "provider": "openai-compatible",
    "model_name": "text-embedding-ada-002",
    "api_key": "your-api-key",
    "endpoint": "https://api.openai.com/v1"
}
embeddings = get_embedding_from_config(config=config)
```

## 在RAG管道中使用

### 1. 使用本地模型

```python
from rag_pipeline import RAGPipeline

# 使用本地embedding模型
rag = RAGPipeline(
    file_path="/path/to/documents",
    use_local_embedding=True
)

rag.load_documents()
```

### 2. 使用远程API

```python
# 通过配置字典
embedding_config = {
    "provider": "openai-compatible",
    "model_name": "text-embedding-ada-002",
    "api_key": "your-api-key",
    "endpoint": "https://api.openai.com/v1"
}

rag = RAGPipeline(
    file_path="/path/to/documents",
    embedding_config=embedding_config
)

rag.load_documents()
```

### 3. 使用数据库配置

```python
# 通过配置ID
rag = RAGPipeline(
    file_path="/path/to/documents",
    embedding_config_id=1  # 数据库中的配置ID
)

rag.load_documents()
```

## 支持的模型类型

### 本地模型

- **BGE系列**：bge-base-zh-v1.5, bge-large-zh-v1.5, bce-embedding-base_v1
- **text2vec系列**：text2vec-base-chinese, text2vec-large-chinese
- **M3E系列**：m3e-base, m3e-large
- **其他HuggingFace兼容模型**

### 远程API

- **OpenAI**：text-embedding-ada-002, text-embedding-3-small, text-embedding-3-large
- **OpenAI-compatible API**：任何兼容OpenAI embedding API格式的服务

## 配置说明

### 本地模型配置

```python
embeddings = create_local_embeddings(
    model_name="bge-embedding-base_v1",  # 模型名称
    model_path="/path/to/model",         # 模型路径（可选）
    cache_dir="/path/to/cache",          # 缓存目录（可选）
    device="cuda",                       # 设备（可选，自动检测）
    normalize_embeddings=True,           # 是否规范化向量
    max_length=512,                      # 最大长度
    pooling_strategy="mean"              # 池化策略
)
```

### 远程API配置

```python
embeddings = RemoteEmbeddings(
    api_key="your-api-key",              # API密钥
    endpoint="https://api.example.com",  # API端点
    model_name="embedding-model",        # 模型名称
    timeout=30,                          # 超时时间（秒）
    max_batch_size=100                   # 批处理大小
)
```

## 数据库配置

在Web界面中配置embedding模型：

1. 访问 `/config/model-config` 页面
2. 选择 "OpenAI-API-compatible" 供应商
3. 设置模型类型为 "embedding"
4. 填写模型名称、API密钥和端点
5. 测试连接确保配置正确
6. 保存配置

配置保存后，可以通过配置ID在代码中使用：

```python
# 获取配置ID（从数据库或Web界面）
config_id = 1

# 在RAG管道中使用
rag = RAGPipeline(
    file_path="/path/to/documents",
    embedding_config_id=config_id
)
```

## 性能优化

### 本地模型优化

1. **设备选择**：优先使用NPU > CUDA > CPU
2. **批处理**：对大量文档使用 `embed_documents` 而不是循环调用 `embed_query`
3. **内存管理**：系统自动清理GPU/NPU内存

### 远程API优化

1. **批处理**：自动将大量文本分批处理，避免单次请求过大
2. **超时设置**：合理设置超时时间，避免长时间等待
3. **错误重试**：建议在应用层实现重试机制

## 故障排除

### 常见问题

1. **本地模型加载失败**
   - 检查模型路径是否正确
   - 确保模型文件完整（config.json, pytorch_model.bin等）
   - 检查transformers库版本

2. **远程API调用失败**
   - 验证API密钥是否有效
   - 检查端点URL格式
   - 确认网络连接正常

3. **内存不足**
   - 降低批处理大小
   - 使用较小的模型
   - 启用内存清理功能

### 调试模式

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 扩展开发

### 添加新的本地模型支持

1. 继承 `LocalEmbeddings` 类
2. 实现 `embed_query` 方法
3. 在 `create_local_embeddings` 函数中添加模型配置

### 添加新的远程API支持

1. 继承 `RemoteEmbeddings` 类或创建新类
2. 实现特定的API调用逻辑
3. 在 `get_embedding_from_config` 函数中添加provider支持

## API参考

详细的API文档请参考代码中的docstring注释。

主要类和函数：
- `LocalEmbeddings`: 本地模型基类
- `LocalHuggingFaceEmbeddings`: HuggingFace本地模型实现
- `RemoteEmbeddings`: 远程API模型实现
- `create_local_embeddings()`: 创建本地模型的便捷函数
- `get_embedding_from_config()`: 从配置获取模型的函数
- `create_embeddings()`: 统一的模型创建函数 