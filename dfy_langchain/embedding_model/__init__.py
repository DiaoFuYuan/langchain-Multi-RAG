"""
Embedding模型包初始化

包含了本地embedding模型的实现，提供了替代HuggingFaceEmbeddings的功能
"""

try:
    from .local_embeddings import (
        LocalEmbeddings, 
        LocalHuggingFaceEmbeddings,
        create_local_embeddings,
        RemoteEmbeddings,
        get_embedding_from_config
    )
except ImportError as e:
    # 如果本地embedding模型无法导入，记录错误但不阻止模块初始化
    import logging
    logging.getLogger(__name__).warning(f"无法导入Embedding模型实现，可能缺少必要的依赖: {e}")
    
    # 创建占位类，避免导入错误
    class LocalEmbeddings:
        """占位类，避免导入错误"""
        
        def __init__(self, *args, **kwargs):
            raise NotImplementedError("LocalEmbeddings未实现，可能缺少必要的依赖")
            
    LocalHuggingFaceEmbeddings = LocalEmbeddings
    RemoteEmbeddings = LocalEmbeddings
    
    def create_local_embeddings(*args, **kwargs):
        """占位函数，避免导入错误"""
        raise NotImplementedError("create_local_embeddings未实现，可能缺少必要的依赖")
    
    def get_embedding_from_config(*args, **kwargs):
        """占位函数，避免导入错误"""
        raise NotImplementedError("get_embedding_from_config未实现，可能缺少必要的依赖")

# 导出的类和函数
__all__ = [
    'LocalEmbeddings',
    'LocalHuggingFaceEmbeddings',
    'create_local_embeddings',
    'RemoteEmbeddings',
    'get_embedding_from_config'
] 