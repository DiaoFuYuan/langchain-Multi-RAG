#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG检索器模块

提供基于FAISS向量存储的文档检索功能，支持多知识库检索和中文路径处理。
"""

import os
import sys
import json
import tempfile
import shutil
from typing import List, Dict, Any, Optional, Union, Tuple
from dotenv import load_dotenv

# 配置路径和环境
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, '.env')

# 加载环境变量
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"已加载环境变量文件: {env_path}")
else:
    print(f"环境变量文件不存在: {env_path}")

# 确保可以导入当前目录的模块
if current_dir not in sys.path:
    sys.path.append(current_dir)

load_dotenv()


class SimpleRetrieverService:
    """简化的检索器服务类（总是可用的后备方案）"""
    
    def __init__(self, vectorstore, top_k: int = 5):
        self.vectorstore = vectorstore
        self.top_k = top_k
        
    def get_relevant_documents(self, query: str) -> List:
        """获取相关文档"""
        if hasattr(self.vectorstore, 'similarity_search'):
            return self.vectorstore.similarity_search(query, k=self.top_k)
        return []
        
    def get_relevant_documents_with_scores(self, query: str) -> List[Tuple]:
        """获取带分数的相关文档"""
        if hasattr(self.vectorstore, 'similarity_search_with_score'):
            return self.vectorstore.similarity_search_with_score(query, k=self.top_k)
        return []


class RetrieverServiceFactory:
    """检索器服务工厂类"""
    
    def __init__(self, embedding_config=None):
        self._initialize_dependencies()
        self._initialize_embeddings(embedding_config)
    
    def _initialize_dependencies(self):
        """初始化依赖库"""
        try:
            import torch
            from langchain_community.vectorstores import FAISS
            from langchain_core.documents import Document
            
            # 尝试导入新的HuggingFaceEmbeddings
            try:
                from langchain_huggingface import HuggingFaceEmbeddings
                print("使用新的langchain-huggingface包")
            except ImportError:
                # 备用方案：使用旧的包
                from langchain_community.embeddings import HuggingFaceEmbeddings
                print("使用旧的langchain-community包")
            
            self.torch = torch
            self.FAISS = FAISS
            self.HuggingFaceEmbeddings = HuggingFaceEmbeddings
            self.Document = Document
            self.dependencies_available = True
            print("成功导入所有必要的库")
            
            # 初始化 FAISS GPU 支持
            self._initialize_faiss_gpu()
            
            # 尝试导入高级检索器
            try:
                # 尝试绝对导入
                try:
                    from dfy_langchain.retrievers.ensemble_modules.basic_ensemble import EnsembleRetrieverService
                    from dfy_langchain.retrievers.vectorstore_modules.basic_vectorstore import VectorstoreRetrieverService
                    from dfy_langchain.retrievers.ensemble_modules.keyword_ensemble import KeywordEnsembleRetrieverService
                except ImportError:
                    # 回退到相对导入
                    from .retrievers.ensemble import EnsembleRetrieverService
                    from .retrievers.vectorstore import VectorstoreRetrieverService
                    from .retrievers.keyword_ensemble import KeywordEnsembleRetrieverService
                
                self.EnsembleRetrieverService = EnsembleRetrieverService
                self.VectorstoreRetrieverService = VectorstoreRetrieverService
                self.KeywordEnsembleRetrieverService = KeywordEnsembleRetrieverService
                self.advanced_retrievers_available = True
                print("成功导入高级检索器")
            except ImportError as e:
                print(f"导入高级检索器失败: {e}")
                self.advanced_retrievers_available = False
                
        except ImportError as e:
            print(f"导入库失败: {e}")
            self.dependencies_available = False
            self.advanced_retrievers_available = False
    
    def _initialize_faiss_gpu(self):
        """初始化 FAISS GPU 支持"""
        self.faiss_gpu_available = False
        self.gpu_resources = None
        
        try:
            import faiss
            self.faiss = faiss
            
            # 检查 GPU 可用性
            if hasattr(faiss, 'get_num_gpus') and faiss.get_num_gpus() > 0:
                print(f"检测到 {faiss.get_num_gpus()} 个 GPU")
                
                # 创建 GPU 资源
                self.gpu_resources = faiss.StandardGpuResources()
                self.faiss_gpu_available = True
                print("FAISS GPU 支持已启用")
            else:
                print("未检测到 GPU 或 FAISS GPU 不可用，使用 CPU 模式")
                
        except ImportError:
            print("FAISS 库未安装或不支持 GPU")
        except Exception as e:
            print(f"初始化 FAISS GPU 失败: {e}")
    
    def _initialize_embeddings(self, embedding_config=None):
        """初始化嵌入模型"""
        if not self.dependencies_available:
            self.embeddings = None
            return
        
        # 如果提供了embedding配置，优先使用远程模型
        if embedding_config:
            try:
                self.embeddings = self._create_remote_embeddings(embedding_config)
                if self.embeddings:
                    return
                print("远程embedding模型创建失败，回退到本地模型")
            except Exception as e:
                print(f"创建远程embedding模型失败: {e}，回退到本地模型")
        
        # 创建本地embedding模型
        self._create_local_embeddings()
    
    def _create_remote_embeddings(self, embedding_config):
        """创建远程embedding模型"""
        try:
            # 动态导入远程embedding模型
            from embedding_model.local_embeddings import get_embedding_from_config
            
            print(f"RAG检索使用远程embedding模型: {embedding_config['model_name']} (provider: {embedding_config['provider']})")
            return get_embedding_from_config(config=embedding_config)
            
        except ImportError as e:
            print(f"无法导入远程embedding模块: {e}")
            return None
        except Exception as e:
            print(f"创建远程embedding模型失败: {e}")
            return None
    
    def _create_local_embeddings(self):
        """创建本地embedding模型"""
        # 获取嵌入模型路径
        embedding_model = os.getenv("EMBEDDING_MODEL_PATH", None)
        if embedding_model:
            # 如果环境变量提供了路径，检查是否为绝对路径
            if os.path.isabs(embedding_model):
                embedding_model_path = embedding_model
            else:
                # 相对路径转换为绝对路径
                embedding_model_path = os.path.join(current_dir, embedding_model)
        else:
            # 默认路径：相对于当前目录的embedding_model/bce-embedding-base_v1
            embedding_model_path = os.path.join(current_dir, "embedding_model", "bce-embedding-base_v1")
        
        print(f"当前目录: {current_dir}")
        print(f"嵌入模型路径: {embedding_model_path}")
        print(f"嵌入模型路径是否存在: {os.path.exists(embedding_model_path)}")
        
        # 检查嵌入模型目录
        embedding_dir = os.path.dirname(embedding_model_path)
        if os.path.exists(embedding_dir):
            print(f"嵌入模型目录内容: {os.listdir(embedding_dir)}")
        
        # 创建嵌入模型
        try:
            device = "cuda" if self.torch.cuda.is_available() else "cpu"
            self.embeddings = self.HuggingFaceEmbeddings(
                model_name=embedding_model_path,
                model_kwargs={"device": device},
                encode_kwargs={"normalize_embeddings": True}
            )
            print(f"成功创建本地嵌入模型，使用设备: {device}")
        except Exception as e:
            print(f"创建本地嵌入模型失败: {e}")
            self.embeddings = None
    
    def _convert_index_to_gpu(self, vectorstore):
        """将 FAISS 索引转换为 GPU 版本"""
        if not self.faiss_gpu_available or not hasattr(vectorstore, 'index'):
            return vectorstore
        
        try:
            # 获取原始索引
            cpu_index = vectorstore.index
            
            # 检查索引是否已经在 GPU 上
            # GPU 索引的类名通常包含 'Gpu' 字符串
            index_type = type(cpu_index).__name__
            if 'Gpu' in index_type:
                print(f"索引已经在 GPU 上，类型: {index_type}")
                return vectorstore
            
            print(f"原始索引类型: {index_type}，准备转换为 GPU")
            
            # 将索引转移到 GPU
            gpu_index = self.faiss.index_cpu_to_gpu(
                self.gpu_resources, 
                0,  # GPU 设备 ID
                cpu_index
            )
            
            # 替换向量存储中的索引
            vectorstore.index = gpu_index
            gpu_index_type = type(gpu_index).__name__
            print(f"成功将 FAISS 索引转移到 GPU，索引大小: {gpu_index.ntotal}，GPU 索引类型: {gpu_index_type}")
            
            return vectorstore
            
        except Exception as e:
            print(f"将索引转移到 GPU 失败: {e}，继续使用 CPU 索引")
            return vectorstore
    
    def _optimize_gpu_index(self, vectorstore):
        """优化 GPU 索引性能"""
        if not self.faiss_gpu_available or not hasattr(vectorstore, 'index'):
            return vectorstore
        
        try:
            index = vectorstore.index
            index_type = type(index).__name__
            
            # 如果索引在 GPU 上，进行性能优化
            if 'Gpu' in index_type:
                print(f"正在优化 GPU 索引，类型: {index_type}")
                
                # 设置搜索参数以优化性能
                if hasattr(index, 'nprobe'):
                    # 对于 IVF 索引，设置合适的 nprobe 值
                    index.nprobe = min(32, max(1, index.nlist // 4))
                    print(f"设置 GPU 索引 nprobe 为: {index.nprobe}")
                
                print("GPU 索引性能优化完成")
            else:
                print(f"索引不在 GPU 上，类型: {index_type}，跳过 GPU 优化")
            
            return vectorstore
            
        except Exception as e:
            print(f"GPU 索引优化失败: {e}")
            return vectorstore
    
    def create_retriever_service(self, vectorstore, retriever_type="auto", **kwargs):
        """
        创建检索器服务
        
        参数:
            vectorstore: 向量存储
            retriever_type: 检索器类型 ("auto", "keyword_ensemble", "vectorstore", "hierarchical")
            **kwargs: 其他参数
        
        返回:
            检索器服务实例
        """
        
        # 如果指定了分层检索
        if retriever_type == "hierarchical":
            hierarchical_retriever = self._create_hierarchical_retriever(vectorstore, **kwargs)
            if hierarchical_retriever:
                return hierarchical_retriever
            # 如果分层检索失败，回退到关键词组合检索
            print("分层检索创建失败，回退到关键词组合检索")
            return self._create_keyword_ensemble_retriever(vectorstore, **kwargs)
        
        # 如果指定了关键词组合检索
        if retriever_type == "keyword_ensemble":
            return self._create_keyword_ensemble_retriever(vectorstore, **kwargs)
        
        # 如果指定了向量检索
        if retriever_type == "vectorstore":
            return self._create_vectorstore_retriever(vectorstore, **kwargs)
        
        # 自动选择最佳检索器
        if retriever_type == "auto":
            return self._create_auto_retriever(vectorstore, **kwargs)
        
        raise ValueError(f"不支持的检索器类型: {retriever_type}")    
    

    
    def _create_keyword_ensemble_retriever(self, vectorstore, **kwargs):
        """创建关键词组合检索器"""
        if not self.advanced_retrievers_available:
            return SimpleRetrieverService(vectorstore, kwargs.get('top_k', 10))
        
        try:
            return self.KeywordEnsembleRetrieverService.from_vectorstore(
                vectorstore=vectorstore,
                top_k=kwargs.get('top_k', 10),
                score_threshold=kwargs.get('score_threshold', 0.3),
                keyword_match_threshold=kwargs.get('keyword_match_threshold', 1),
                context_window=kwargs.get('context_window', 150),
                enable_ranking=kwargs.get('enable_ranking', True),
                weight_keyword_freq=kwargs.get('weight_keyword_freq', 0.4),
                weight_keyword_pos=kwargs.get('weight_keyword_pos', 0.3),
                weight_keyword_coverage=kwargs.get('weight_keyword_coverage', 0.3)
            )
        except Exception as e:
            print(f"创建KeywordEnsembleRetrieverService失败: {e}")
            # 回退到向量检索
            return self._create_vectorstore_retriever(vectorstore, **kwargs)
    
    def _create_vectorstore_retriever(self, vectorstore, **kwargs):
        """创建向量检索器"""
        if not self.advanced_retrievers_available:
            return SimpleRetrieverService(vectorstore, kwargs.get('top_k', 10))
        
        try:
            # 只传递VectorstoreRetrieverService需要的参数
            return self.VectorstoreRetrieverService.from_vectorstore(
                vectorstore=vectorstore,
                top_k=kwargs.get('top_k', 5),
                score_threshold=kwargs.get('score_threshold', 0.3)
            )
        except Exception as e:
            print(f"创建VectorstoreRetrieverService失败: {e}")
            return SimpleRetrieverService(vectorstore, kwargs.get('top_k', 10))
    
    def _create_auto_retriever(self, vectorstore, **kwargs):
        """自动选择最佳检索器"""
        # 检查文档数量
        doc_count = self._estimate_document_count(vectorstore)
        
        # 检查是否强制使用向量存储检索器
        force_vectorstore = kwargs.get('force_vectorstore', False)
        
        if force_vectorstore:
            print(f"强制使用向量检索({doc_count}个文档)")
            return self._create_vectorstore_retriever(vectorstore, **kwargs)
        
        # 优先尝试分层检索（不受文档数量限制）
        print(f"检测到知识库({doc_count}个文档)，优先尝试分层检索")
        try:
            hierarchical_retriever = self._create_hierarchical_retriever(vectorstore, **kwargs)
            if hierarchical_retriever:
                print("✅ 使用分层检索")
                return hierarchical_retriever
            print("⚠️  分层检索不可用，回退到关键词组合检索")
        except Exception as e:
            print(f"⚠️  分层检索创建失败，回退到关键词组合检索: {e}")
        
        # 回退到关键词组合检索
        if doc_count > 50:
            print(f"使用关键词组合检索({doc_count}个文档)")
            try:
                return self._create_keyword_ensemble_retriever(vectorstore, **kwargs)
            except Exception as e:
                print(f"关键词组合检索创建失败，回退到向量检索: {e}")
        
        # 最后回退到简单向量检索
        print(f"使用向量检索({doc_count}个文档)")
        return self._create_vectorstore_retriever(vectorstore, **kwargs)
    
    def _create_hierarchical_retriever(self, vectorstore, **kwargs):
        """创建分层检索器"""
        try:
            # 尝试多种导入方式
            HierarchicalRetrieverService = None
            
            # 方式1：尝试绝对导入
            try:
                from dfy_langchain.retrievers.hierarchical_retriever import HierarchicalRetrieverService
            except ImportError:
                pass
            
            # 方式2：尝试相对导入
            if HierarchicalRetrieverService is None:
                try:
                    from .retrievers.hierarchical_retriever import HierarchicalRetrieverService
                except ImportError:
                    pass
            
            # 方式3：动态导入
            if HierarchicalRetrieverService is None:
                import importlib.util
                hierarchical_path = os.path.join(current_dir, "retrievers", "hierarchical_retriever.py")
                if os.path.exists(hierarchical_path):
                    spec = importlib.util.spec_from_file_location("hierarchical_retriever", hierarchical_path)
                    hierarchical_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(hierarchical_module)
                    HierarchicalRetrieverService = hierarchical_module.HierarchicalRetrieverService
            
            if HierarchicalRetrieverService is None:
                raise ImportError("无法导入 HierarchicalRetrieverService")
            
            # 获取知识库ID和向量存储路径信息
            knowledge_base_id = kwargs.get('knowledge_base_id')
            vectorstore_path = None
            
            if knowledge_base_id:
                # 尝试从知识库管理器获取向量存储路径
                try:
                    # 直接使用当前模块中的KnowledgeBaseManager类
                    # 避免相对导入问题
                    kb_manager = KnowledgeBaseManager(self)
                    kb_name = kb_manager.resolve_knowledge_base_name(knowledge_base_id)
                    if kb_name:
                        vectorstore_path = os.path.abspath(os.path.join("data", "knowledge_base", kb_name, "vector_store"))
                        print(f"🔍 获取到向量存储路径: {vectorstore_path}")
                except Exception as e:
                    print(f"⚠️ 获取向量存储路径失败: {e}")
                    # 如果获取失败，尝试直接构造路径
                    try:
                        # 加载知识库配置
                        config_path = os.path.join("data", "knowledge_base", "knowledge_bases.json")
                        if os.path.exists(config_path):
                            import json
                            with open(config_path, 'r', encoding='utf-8') as f:
                                config = json.load(f)
                            kb_info = config.get(knowledge_base_id)
                            if kb_info:
                                kb_name = kb_info.get('name')
                                if kb_name:
                                    vectorstore_path = os.path.abspath(os.path.join("data", "knowledge_base", kb_name, "vector_store"))
                                    print(f"🔍 通过配置文件获取到向量存储路径: {vectorstore_path}")
                    except Exception as e2:
                        print(f"⚠️ 通过配置文件获取路径也失败: {e2}")
            
            # 提取分层检索特有的参数，避免重复传递
            hierarchical_kwargs = {
                'vectorstore': vectorstore,
                'vectorstore_path': vectorstore_path,  # 传递向量存储路径
                'top_k': kwargs.get('top_k', 5),
                'score_threshold': kwargs.get('score_threshold', 0.3),
                'summary_top_k': kwargs.get('summary_top_k', 10),
                'summary_score_threshold': kwargs.get('summary_score_threshold', 0.4),
                'chunk_score_threshold': kwargs.get('chunk_score_threshold', 0.3),
                'enable_summary_fallback': kwargs.get('enable_summary_fallback', True)
            }
            
            # 添加其他不冲突的参数
            for key, value in kwargs.items():
                if key not in hierarchical_kwargs:
                    hierarchical_kwargs[key] = value
            
            return HierarchicalRetrieverService.from_vectorstore(**hierarchical_kwargs)
        except ImportError as e:
            print(f"无法导入分层检索器: {e}")
            return None
        except Exception as e:
            print(f"创建分层检索器失败: {e}")
            return None
    
    def _estimate_document_count(self, vectorstore):
        """估算向量存储中的文档数量"""
        try:
            if hasattr(vectorstore, 'docstore') and hasattr(vectorstore.docstore, '_dict'):
                return len(vectorstore.docstore._dict)
            elif hasattr(vectorstore, 'index') and hasattr(vectorstore.index, 'ntotal'):
                return vectorstore.index.ntotal
            else:
                # 通过搜索估算
                test_results = vectorstore.similarity_search("", k=1000)
                return len(test_results)
        except Exception:
            return 0


class ChinesePathHandler:
    """中文路径处理器 - 跨平台支持"""
    
    @staticmethod
    def get_short_path(path: str) -> Optional[str]:
        """获取Windows短路径（仅在Windows上有效）"""
        if os.name != 'nt':  # 非Windows系统
            return None
            
        try:
            import ctypes
            from ctypes import wintypes
            
            GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
            GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
            GetShortPathNameW.restype = wintypes.DWORD
            
            buffer_size = 1000
            buffer = ctypes.create_unicode_buffer(buffer_size)
            result = GetShortPathNameW(path, buffer, buffer_size)
            
            if result > 0:
                return buffer.value
            return None
        except Exception as e:
            print(f"获取短路径失败: {e}")
            return None
    
    @staticmethod
    def create_temp_copy(source_path: str) -> Optional[str]:
        """创建临时副本 - 跨平台"""
        try:
            # 使用英文前缀创建临时目录，确保路径不包含中文
            import uuid
            temp_dir = tempfile.mkdtemp(
                prefix=f"faiss_temp_{uuid.uuid4().hex[:8]}_", 
                dir=tempfile.gettempdir()
            )
            temp_path = os.path.join(temp_dir, "vector_store")
            
            # 确保源路径存在
            if not os.path.exists(source_path):
                print(f"源路径不存在: {source_path}")
                return None
                
            # 复制整个目录
            shutil.copytree(source_path, temp_path)
            print(f"成功创建临时副本，源: {source_path}")
            print(f"临时路径: {temp_path}")
            return temp_path
        except Exception as e:
            print(f"创建临时副本失败: {e}")
            return None
    
    @staticmethod
    def cleanup_temp_path(temp_path: str):
        """清理临时路径 - 跨平台"""
        if temp_path and os.path.exists(temp_path):
            try:
                # 获取临时目录的根目录（通常是temp_path的父目录）
                temp_root = os.path.dirname(temp_path)
                # 检查是否是我们创建的临时目录（包含faiss_temp前缀）
                if os.path.basename(temp_root).startswith('faiss_temp_'):
                    shutil.rmtree(temp_root)
                    print(f"清理临时文件: {temp_root}")
                else:
                    # 如果不确定，只清理vector_store目录本身
                    shutil.rmtree(temp_path)
                    print(f"清理临时文件: {temp_path}")
            except Exception as e:
                print(f"清理临时文件失败: {e}")
                # 尝试强制删除
                try:
                    import time
                    time.sleep(0.1)  # 短暂等待，释放文件句柄
                    if os.path.exists(temp_path):
                        shutil.rmtree(temp_path, ignore_errors=True)
                except:
                    pass
    
    @staticmethod
    def has_chinese_chars(text: str) -> bool:
        """检查字符串是否包含中文字符"""
        return any('\u4e00' <= char <= '\u9fff' for char in text)
    
    @staticmethod
    def needs_path_processing(path: str) -> bool:
        """判断路径是否需要特殊处理"""
        # 检查是否包含中文字符
        if ChinesePathHandler.has_chinese_chars(path):
            return True
        
        # 在Windows上，还可以检查其他可能有问题的字符
        if os.name == 'nt':
            # Windows上某些特殊字符可能导致问题
            problematic_chars = ['？', '？', '：', '｜', '＊', '＜', '＞', '＂']
            return any(char in path for char in problematic_chars)
        
        return False
    
    @classmethod
    def process_chinese_path(cls, path: str) -> Tuple[str, Optional[str]]:
        """
        处理中文路径 - 跨平台
        返回: (处理后的路径, 临时路径或None)
        """
        if not cls.needs_path_processing(path):
            return path, None
        
        print(f"检测到需要处理的路径，尝试处理路径兼容性问题...")
        
        # Linux/Unix系统通常对UTF-8编码的中文路径支持良好
        if os.name != 'nt':
            # 在Linux上，首先尝试直接使用原路径
            try:
                # 测试路径是否可以正常访问
                if os.path.exists(path) and os.access(path, os.R_OK):
                    print(f"Linux系统直接使用原路径: {path}")
                    return path, None
            except Exception as e:
                print(f"Linux路径访问测试失败: {e}")
        
        # 创建临时副本（Windows和Linux都适用）
        temp_path = cls.create_temp_copy(path)
        if temp_path:
            print(f"创建临时副本: {temp_path}")
            return temp_path, temp_path
        
        # Windows特有：尝试短路径
        if os.name == 'nt':
            short_path = cls.get_short_path(path)
            if short_path and not cls.has_chinese_chars(short_path):
                print(f"使用Windows短路径: {short_path}")
                return short_path, None
        
        print("无法处理路径，使用原路径")
        return path, None


class KnowledgeBaseManager:
    """知识库管理器"""
    
    def __init__(self, factory: RetrieverServiceFactory):
        self.factory = factory
        self.path_handler = ChinesePathHandler()
        # 添加检索器缓存，键为(knowledge_base_ids_tuple, retriever_type, embedding_config_hash)
        self._retriever_cache = {}
        # 缓存大小限制
        self._max_cache_size = 10
    
    def get_embedding_config_for_kb(self, knowledge_base_id: str) -> Optional[dict]:
        """获取知识库的embedding配置"""
        try:
            # 获取知识库配置
            kb_config = self.load_knowledge_bases_config()
            kb_info = kb_config.get(knowledge_base_id)
            
            if not kb_info:
                print(f"未找到知识库 {knowledge_base_id} 的配置")
                return None
            
            embedding_model_id = kb_info.get("embedding_model_id")
            if not embedding_model_id:
                print(f"知识库 {knowledge_base_id} 未配置embedding模型")
                return None
            
            # 动态导入数据库相关模块（避免循环导入）
            try:
                sys.path.append(os.path.join(os.path.dirname(current_dir), "app"))
                from database import get_db
                from app.services.model_config_service import ModelConfigService
                
                db = next(get_db())
                try:
                    model_config = ModelConfigService.get_model_config_by_id(db, embedding_model_id)
                    if not model_config:
                        print(f"未找到ID为 {embedding_model_id} 的embedding模型配置")
                        return None
                    
                    embedding_config = {
                        "id": model_config.id,
                        "provider": model_config.provider,
                        "model_name": model_config.model_name,
                        "api_key": model_config.api_key,
                        "endpoint": model_config.endpoint,
                        "model_type": model_config.model_type
                    }
                    
                    print(f"RAG检索获取知识库 {knowledge_base_id} 的embedding配置: {model_config.model_name} ({model_config.provider})")
                    return embedding_config
                    
                finally:
                    db.close()
                    
            except ImportError as e:
                print(f"无法导入数据库模块: {e}")
                return None
            except Exception as e:
                print(f"获取embedding配置失败: {e}")
                return None
                
        except Exception as e:
            print(f"获取知识库embedding配置失败: {e}")
            return None
    
    def load_knowledge_bases_config(self) -> Dict[str, Dict]:
        """加载知识库配置"""
        try:
            # 尝试多个可能的配置路径
            possible_paths = [
                os.path.join("data", "knowledge_base", "knowledge_bases.json"),
                os.path.join("..", "data", "knowledge_base", "knowledge_bases.json"),
                os.path.abspath(os.path.join("..", "data", "knowledge_base", "knowledge_bases.json"))
            ]
            
            kb_config_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    kb_config_path = path
                    break
            
            if not kb_config_path:
                print(f"未找到知识库配置文件，尝试的路径: {possible_paths}")
                return {}
            
            print(f"找到配置文件: {kb_config_path}")
            with open(kb_config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 转换为以ID为键的字典
                result = {str(kb["id"]): kb for kb in data.get("knowledge_bases", [])}
                print(f"成功加载配置，包含 {len(result)} 个知识库")
                return result
        except Exception as e:
            print(f"加载知识库配置失败: {e}")
            return {}
    
    def resolve_knowledge_base_name(self, knowledge_base_id: str) -> Optional[str]:
        """解析知识库名称"""
        kb_config = self.load_knowledge_bases_config()
        
        # 通过ID查找
        if knowledge_base_id in kb_config:
            kb_name = kb_config[knowledge_base_id]["name"]
            print(f"通过ID {knowledge_base_id} 找到知识库名称: {kb_name}")
            return kb_name
        
        # 直接使用ID作为名称
        potential_path = os.path.join("data", "knowledge_base", knowledge_base_id)
        if os.path.exists(potential_path):
            print(f"直接使用 {knowledge_base_id} 作为知识库名称")
            return knowledge_base_id
        
        # 通过名称匹配
        for kb_id, kb_info in kb_config.items():
            if kb_info["name"] == knowledge_base_id:
                print(f"通过名称匹配找到知识库: {knowledge_base_id}")
                return knowledge_base_id
        
        print(f"无法找到知识库 {knowledge_base_id}，请检查知识库配置或名称")
        return None
    
    def load_faiss_vectorstore(self, knowledge_base_id: str):
        """加载FAISS向量存储"""
        if not self.factory.dependencies_available or not self.factory.embeddings:
            print("依赖库或嵌入模型不可用")
            return None
        
        kb_name = self.resolve_knowledge_base_name(knowledge_base_id)
        if not kb_name:
            return None
        
        # 尝试多个可能的向量存储路径
        possible_paths = [
            os.path.join("data", "knowledge_base", kb_name, "vector_store"),
            os.path.join("..", "data", "knowledge_base", kb_name, "vector_store"),
            os.path.abspath(os.path.join("..", "data", "knowledge_base", kb_name, "vector_store"))
        ]
        
        vector_store_path = None
        for path in possible_paths:
            if os.path.exists(path):
                vector_store_path = os.path.abspath(path)
                print(f"找到向量存储路径: {vector_store_path}")
                break
        
        if not vector_store_path:
            print(f"知识库 {knowledge_base_id} 的向量存储路径不存在，尝试的路径: {possible_paths}")
            self._debug_missing_path(possible_paths[0])
            return None
        
        return self._load_vectorstore_with_path_handling(knowledge_base_id, vector_store_path, kb_name)
    
    def _debug_missing_path(self, vector_store_path: str):
        """调试缺失路径"""
        parent_dir = os.path.dirname(vector_store_path)
        if os.path.exists(parent_dir):
            print(f"父目录内容: {os.listdir(parent_dir)}")
    
    def _load_vectorstore_with_path_handling(self, knowledge_base_id: str, vector_store_path: str, kb_name: str):
        """使用路径处理加载向量存储"""
        print(f"正在从 {vector_store_path} 加载知识库 {knowledge_base_id} 的向量存储...")
        
        # 检查必需的文件是否存在
        index_file = os.path.join(vector_store_path, "index.faiss")
        pkl_file = os.path.join(vector_store_path, "index.pkl")
        
        print(f"检查文件存在性:")
        print(f"  index.faiss: {os.path.exists(index_file)}")
        print(f"  index.pkl: {os.path.exists(pkl_file)}")
        
        if not os.path.exists(index_file) or not os.path.exists(pkl_file):
            print(f"缺少必需的FAISS文件")
            if os.path.exists(vector_store_path):
                print(f"目录内容: {os.listdir(vector_store_path)}")
            return None
        
        processed_path, temp_path = self.path_handler.process_chinese_path(vector_store_path)
        
        try:
            print(f"尝试从路径加载: {processed_path}")
            vectorstore = self.factory.FAISS.load_local(
                folder_path=processed_path,
                embeddings=self.factory.embeddings,
                allow_dangerous_deserialization=True
            )
            print(f"成功加载知识库 {knowledge_base_id} 的向量存储，包含 {len(vectorstore.docstore._dict)} 个文档")
            
            # 尝试将索引转移到 GPU
            vectorstore = self.factory._convert_index_to_gpu(vectorstore)
            vectorstore = self.factory._optimize_gpu_index(vectorstore)
            
            return vectorstore
            
        except Exception as e:
            print(f"加载知识库 {knowledge_base_id} 的向量存储失败: {e}")
            return self._retry_load_with_encoding(knowledge_base_id, kb_name)
            
        finally:
            if temp_path:
                self.path_handler.cleanup_temp_path(temp_path)
    
    def _retry_load_with_encoding(self, knowledge_base_id: str, kb_name: str):
        """重试加载（编码处理）"""
        try:
            original_path = os.path.abspath(os.path.join("data", "knowledge_base", kb_name, "vector_store"))
            print(f"尝试重新编码路径: {original_path}")
            
            vectorstore = self.factory.FAISS.load_local(
                folder_path=original_path,
                embeddings=self.factory.embeddings,
                allow_dangerous_deserialization=True
            )
            print(f"重新编码后成功加载知识库 {knowledge_base_id} 的向量存储")
            
            # 尝试将索引转移到 GPU
            vectorstore = self.factory._convert_index_to_gpu(vectorstore)
            vectorstore = self.factory._optimize_gpu_index(vectorstore)
            
            return vectorstore
        except Exception as e2:
            print(f"重新编码也失败: {e2}")
            return None
    
    def merge_vectorstores(self, vectorstores: List) -> Optional[Any]:
        """合并多个向量存储"""
        if not vectorstores:
            return None
        
        if len(vectorstores) == 1:
            return vectorstores[0]
        
        merged_vectorstore = vectorstores[0]
        for vs in vectorstores[1:]:
            if vs is not None:
                try:
                    merged_vectorstore.merge_from(vs)
                except Exception as e:
                    print(f"合并向量存储时出错: {e}")
        
        return merged_vectorstore
    
    def create_retriever_service(self, knowledge_base_ids: List[str], **kwargs):
        """创建检索器服务（带缓存）"""
        if not knowledge_base_ids:
            print("没有指定知识库ID")
            return None
        
        # 获取检索器类型
        retriever_type = kwargs.get('retriever_type', 'auto')
        
        # 获取第一个知识库的embedding配置（假设所有知识库使用相同的embedding配置）
        embedding_config = None
        if knowledge_base_ids:
            embedding_config = self.get_embedding_config_for_kb(knowledge_base_ids[0])
        
        # 生成缓存键
        cache_key = self._generate_cache_key(knowledge_base_ids, retriever_type, embedding_config, kwargs)
        
        # 检查缓存
        if cache_key in self._retriever_cache:
            print(f"✅ 从缓存获取检索器服务 (KB: {knowledge_base_ids}, Type: {retriever_type})")
            return self._retriever_cache[cache_key]
        
        print(f"🔄 创建新的检索器服务 (KB: {knowledge_base_ids}, Type: {retriever_type})")
        
        # 如果有embedding配置，创建新的factory实例使用该配置
        if embedding_config:
            print(f"RAG检索使用配置的embedding模型: {embedding_config['model_name']}")
            factory = RetrieverServiceFactory(embedding_config)
        else:
            print("RAG检索使用默认的本地embedding模型")
            factory = self.factory
        
        # 加载所有指定的向量存储（使用配置的embedding模型）
        vectorstores = []
        for kb_id in knowledge_base_ids:
            vs = self._load_faiss_vectorstore_with_factory(kb_id, factory)
            if vs is not None:
                vectorstores.append(vs)
        
        if not vectorstores:
            print("没有成功加载任何向量存储")
            return None
        
        # 合并向量存储
        merged_vectorstore = self.merge_vectorstores(vectorstores)
        if merged_vectorstore is None:
            print("合并向量存储失败")
            return None
        
        # 传递知识库ID给检索器服务
        kwargs['knowledge_base_id'] = knowledge_base_ids[0] if knowledge_base_ids else None
        
        # 创建检索器服务
        retriever_service = factory.create_retriever_service(merged_vectorstore, **kwargs)
        
        if retriever_service:
            # 缓存检索器服务
            self._cache_retriever_service(cache_key, retriever_service)
            print(f"✅ 检索器服务已缓存 (缓存大小: {len(self._retriever_cache)})")
        
        return retriever_service
    
    def _load_faiss_vectorstore_with_factory(self, knowledge_base_id: str, factory: RetrieverServiceFactory):
        """使用指定的factory加载FAISS向量存储"""
        if not factory.dependencies_available or not factory.embeddings:
            print("依赖库或嵌入模型不可用")
            return None
        
        kb_name = self.resolve_knowledge_base_name(knowledge_base_id)
        if not kb_name:
            return None
        
        # 尝试多个可能的向量存储路径
        possible_paths = [
            os.path.join("data", "knowledge_base", kb_name, "vector_store"),
            os.path.join("..", "data", "knowledge_base", kb_name, "vector_store"),
            os.path.abspath(os.path.join("..", "data", "knowledge_base", kb_name, "vector_store"))
        ]
        
        vector_store_path = None
        for path in possible_paths:
            if os.path.exists(path):
                vector_store_path = os.path.abspath(path)
                print(f"找到向量存储路径: {vector_store_path}")
                break
        
        if not vector_store_path:
            print(f"知识库 {knowledge_base_id} 的向量存储路径不存在，尝试的路径: {possible_paths}")
            self._debug_missing_path(possible_paths[0])
            return None
        
        return self._load_vectorstore_with_path_handling_and_factory(knowledge_base_id, vector_store_path, kb_name, factory)
    
    def _load_vectorstore_with_path_handling_and_factory(self, knowledge_base_id: str, vector_store_path: str, kb_name: str, factory: RetrieverServiceFactory):
        """使用指定的factory和路径处理加载向量存储"""
        print(f"正在从 {vector_store_path} 加载知识库 {knowledge_base_id} 的向量存储...")
        
        # 检查必需的文件是否存在
        index_file = os.path.join(vector_store_path, "index.faiss")
        pkl_file = os.path.join(vector_store_path, "index.pkl")
        
        print(f"检查文件存在性:")
        print(f"  index.faiss: {os.path.exists(index_file)}")
        print(f"  index.pkl: {os.path.exists(pkl_file)}")
        
        if not os.path.exists(index_file) or not os.path.exists(pkl_file):
            print(f"缺少必需的FAISS文件")
            if os.path.exists(vector_store_path):
                print(f"目录内容: {os.listdir(vector_store_path)}")
            return None
        
        processed_path, temp_path = self.path_handler.process_chinese_path(vector_store_path)
        
        try:
            print(f"尝试从路径加载: {processed_path}")
            vectorstore = factory.FAISS.load_local(
                folder_path=processed_path,
                embeddings=factory.embeddings,
                allow_dangerous_deserialization=True
            )
            print(f"成功加载知识库 {knowledge_base_id} 的向量存储，包含 {len(vectorstore.docstore._dict)} 个文档")
            
            # 尝试将索引转移到 GPU
            vectorstore = factory._convert_index_to_gpu(vectorstore)
            vectorstore = factory._optimize_gpu_index(vectorstore)
            
            return vectorstore
            
        except Exception as e:
            print(f"加载知识库 {knowledge_base_id} 的向量存储失败: {e}")
            return self._retry_load_with_encoding_and_factory(knowledge_base_id, kb_name, factory)
            
        finally:
            if temp_path:
                self.path_handler.cleanup_temp_path(temp_path)
    
    def _retry_load_with_encoding_and_factory(self, knowledge_base_id: str, kb_name: str, factory: RetrieverServiceFactory):
        """重试加载（编码处理）使用指定的factory"""
        try:
            original_path = os.path.abspath(os.path.join("data", "knowledge_base", kb_name, "vector_store"))
            print(f"尝试重新编码路径: {original_path}")
            
            vectorstore = factory.FAISS.load_local(
                folder_path=original_path,
                embeddings=factory.embeddings,
                allow_dangerous_deserialization=True
            )
            print(f"重新编码后成功加载知识库 {knowledge_base_id} 的向量存储")
            
            # 尝试将索引转移到 GPU
            vectorstore = factory._convert_index_to_gpu(vectorstore)
            vectorstore = factory._optimize_gpu_index(vectorstore)
            
            return vectorstore
        except Exception as e2:
            print(f"重新编码也失败: {e2}")
            return None
    
    def _generate_cache_key(self, knowledge_base_ids: List[str], retriever_type: str, 
                           embedding_config: dict, kwargs: dict) -> str:
        """生成缓存键"""
        import hashlib
        import json
        
        # 创建缓存键的组成部分
        kb_ids_tuple = tuple(sorted(knowledge_base_ids))
        
        # 处理embedding配置
        embedding_hash = "none"
        if embedding_config:
            # 只使用关键配置项生成hash，避免包含敏感信息
            config_for_hash = {
                "provider": embedding_config.get("provider"),
                "model_name": embedding_config.get("model_name"),
                "model_type": embedding_config.get("model_type")
            }
            embedding_hash = hashlib.md5(json.dumps(config_for_hash, sort_keys=True).encode()).hexdigest()[:8]
        
        # 处理其他关键参数
        cache_relevant_kwargs = {
            "top_k": kwargs.get("top_k", 5),
            "score_threshold": kwargs.get("score_threshold", 0.3),
            "summary_top_k": kwargs.get("summary_top_k", 10),
            "summary_score_threshold": kwargs.get("summary_score_threshold", 0.4),
            "chunk_score_threshold": kwargs.get("chunk_score_threshold", 0.3)
        }
        kwargs_hash = hashlib.md5(json.dumps(cache_relevant_kwargs, sort_keys=True).encode()).hexdigest()[:8]
        
        # 生成最终的缓存键
        cache_key = f"{kb_ids_tuple}_{retriever_type}_{embedding_hash}_{kwargs_hash}"
        return cache_key
    
    def _cache_retriever_service(self, cache_key: str, retriever_service):
        """缓存检索器服务"""
        # 如果缓存已满，移除最旧的条目（简单的LRU策略）
        if len(self._retriever_cache) >= self._max_cache_size:
            # 移除第一个（最旧的）条目
            oldest_key = next(iter(self._retriever_cache))
            del self._retriever_cache[oldest_key]
            print(f"🗑️  缓存已满，移除最旧的检索器: {oldest_key}")
        
        # 添加到缓存
        self._retriever_cache[cache_key] = retriever_service
    
    def clear_retriever_cache(self):
        """清空检索器缓存"""
        self._retriever_cache.clear()
        print("🗑️  检索器缓存已清空")
    
    def get_cache_info(self) -> dict:
        """获取缓存信息"""
        return {
            "cache_size": len(self._retriever_cache),
            "max_cache_size": self._max_cache_size,
            "cached_keys": list(self._retriever_cache.keys())
        }


class DocumentSearcher:
    """文档搜索器"""
    
    def __init__(self):
        # 创建默认的factory，但会在search_documents中根据知识库动态创建新的manager
        self.default_factory = RetrieverServiceFactory()
    
    def search_documents(self, query: str, knowledge_base_ids: List[str] = None, 
                        top_k: int = 5, return_scores: bool = False,
                        enable_context_enrichment: bool = True, 
                        enable_ranking: bool = True,
                        keyword_threshold: int = 1,
                        context_window: int = 150,
                        score_threshold: float = 0.3,
                        weight_keyword_freq: float = 0.4,
                        weight_keyword_pos: float = 0.3,
                        weight_keyword_coverage: float = 0.3,
                        retriever_type: str = "auto",
                        force_vectorstore: bool = False) -> List:
        """
        搜索相关文档
        
        参数:
            query: 查询字符串
            knowledge_base_ids: 知识库ID列表
            top_k: 返回的文档数量
            return_scores: 是否返回相关性分数
            enable_context_enrichment: 是否启用上下文增强功能
            enable_ranking: 是否启用相关性排序功能
            keyword_threshold: 关键词匹配阈值（至少包含多少个关键词才算匹配）
            context_window: 上下文窗口大小（字符数）
            score_threshold: 相似度分数阈值
            weight_keyword_freq: 关键词频率权重
            weight_keyword_pos: 关键词位置权重
            weight_keyword_coverage: 关键词覆盖度权重
            retriever_type: 检索器类型 ("auto", "keyword_ensemble", "vectorstore")
            
        返回:
            如果return_scores为True，返回(文档, 分数)的元组列表
            否则，返回文档列表
        """
        if not knowledge_base_ids:
            print("没有指定知识库ID，无法进行检索")
            return []
        

        
        # 为每次搜索创建新的KnowledgeBaseManager，确保使用正确的embedding配置
        kb_manager = KnowledgeBaseManager(self.default_factory)
        
        # 将RAG配置参数传递给检索器服务
        retriever_kwargs = {
            'top_k': top_k,
            'score_threshold': score_threshold,
            'keyword_match_threshold': keyword_threshold,
            'context_window': context_window if enable_context_enrichment else 0,
            'enable_ranking': enable_ranking,
            'weight_keyword_freq': weight_keyword_freq,
            'weight_keyword_pos': weight_keyword_pos,
            'weight_keyword_coverage': weight_keyword_coverage,
            'retriever_type': retriever_type,
            'force_vectorstore': force_vectorstore,
            'knowledge_base_id': knowledge_base_ids[0] if knowledge_base_ids else None  # 传递给分层检索器
        }
        
        retriever_service = kb_manager.create_retriever_service(knowledge_base_ids, **retriever_kwargs)
        if not retriever_service:
            print("无法创建检索器服务")
            return []
        
        return self._execute_search(retriever_service, query, top_k, return_scores,
                                  enable_context_enrichment, enable_ranking, knowledge_base_ids)
    
    def _execute_search(self, retriever_service, query: str, top_k: int, 
                       return_scores: bool, enable_context_enrichment: bool, 
                       enable_ranking: bool, knowledge_base_ids: List[str] = None) -> List:
        """执行搜索"""
        # 保存原始设置
        original_context = getattr(retriever_service, 'context_window', 0) > 0
        original_ranking = getattr(retriever_service, 'enable_ranking', True)
        
        results = []
        
        try:
            # 应用临时设置
            self._apply_search_settings(retriever_service, enable_context_enrichment, 
                                      enable_ranking, original_context, original_ranking)
            
            # 执行检索
            if return_scores:
                results = retriever_service.get_relevant_documents_with_scores(query)
            else:
                results = retriever_service.get_relevant_documents(query)
            
            results = results[:top_k]
            
        except Exception as e:
            print(f"检索过程中出错: {e}")
            results = []
            
        finally:
            # 恢复原始设置
            self._restore_search_settings(retriever_service, original_context, original_ranking)
        
        # 如果向量检索失败或返回空结果，尝试Excel回退检索
        if not results:
            print("⚠️ 向量检索未找到结果，尝试Excel回退检索...")
            try:
                from excel_fallback_retriever import excel_fallback_search
                excel_docs = excel_fallback_search(query, knowledge_base_ids, top_k)
                if excel_docs:
                    print(f"✅ Excel回退检索找到 {len(excel_docs)} 个结果")
                    results = excel_docs
                else:
                    print("❌ Excel回退检索也未找到结果")
            except Exception as e:
                print(f"Excel回退检索失败: {e}")
        
        return results
    
    def _apply_search_settings(self, retriever_service, enable_context_enrichment: bool,
                              enable_ranking: bool, original_context: bool, original_ranking: bool):
        """应用搜索设置"""
        if (hasattr(retriever_service, 'context_window') and 
            enable_context_enrichment != original_context):
            retriever_service.context_window = 150 if enable_context_enrichment else 0
            
        if (hasattr(retriever_service, 'enable_ranking') and 
            enable_ranking != original_ranking):
            retriever_service.enable_ranking = enable_ranking
    
    def _restore_search_settings(self, retriever_service, original_context: bool, 
                                original_ranking: bool):
        """恢复搜索设置"""
        if hasattr(retriever_service, 'context_window'):
            retriever_service.context_window = 150 if original_context else 0
            
        if hasattr(retriever_service, 'enable_ranking'):
            retriever_service.enable_ranking = original_ranking


class DocumentInfoExtractor:
    """文档信息提取器"""
    
    @staticmethod
    def get_document_source_info(doc) -> str:
        """获取文档的详细来源信息"""
        source = doc.metadata.get("source", "未知来源")
        filename = os.path.basename(source) if source else "未知文档"
        
        source_info = [f"文件名: {filename}"]
        
        # 添加各种元数据
        metadata_mappings = {
            "page": "页码",
            "row": "行号", 
            "created_at": "创建时间",
            "author": "作者"
        }
        
        for key, label in metadata_mappings.items():
            if key in doc.metadata:
                source_info.append(f"{label}: {doc.metadata[key]}")
        
        return "\n".join(source_info)
    
    @staticmethod
    def get_document_type(source: str) -> str:
        """获取文档类型"""
        if not source:
            return "未知类型"
        
        type_mappings = {
            (".pdf", ".PDF"): "PDF文档",
            (".docx", ".DOCX"): "Word文档", 
            (".xlsx", ".XLSX"): "Excel文档"
        }
        
        for extensions, doc_type in type_mappings.items():
            if source.endswith(extensions):
                return doc_type
        
        return "其他文档"


# 全局实例
_document_searcher = DocumentSearcher()
_info_extractor = DocumentInfoExtractor()

# 兼容性接口
def search_documents(query: str, knowledge_base_ids: List[str] = None, top_k: int = 5,
                    return_scores: bool = False, enable_context_enrichment: bool = True,
                    enable_ranking: bool = True,
                    keyword_threshold: int = 1,
                    context_window: int = 150,
                    score_threshold: float = 0.3,
                    weight_keyword_freq: float = 0.4,
                    weight_keyword_pos: float = 0.3,
                    weight_keyword_coverage: float = 0.3,
                    force_vectorstore: bool = False,
                    retriever_type: str = "auto") -> List:
    """搜索文档的兼容性接口"""
    return _document_searcher.search_documents(
        query, knowledge_base_ids, top_k, return_scores, 
        enable_context_enrichment, enable_ranking,
        keyword_threshold, context_window, score_threshold,
        weight_keyword_freq, weight_keyword_pos, weight_keyword_coverage,
        retriever_type=retriever_type,
        force_vectorstore=force_vectorstore
    )

def get_document_source_info(doc) -> str:
    """获取文档来源信息的兼容性接口"""
    return _info_extractor.get_document_source_info(doc)


def main():
    """测试主函数"""
    test_queries = ["钟曦瑶投诉的内容"]
    test_kb_ids = ["1", "测试用"]
    show_scores = True
    enable_context = True
    enable_ranking = True
    
    for test_query in test_queries:
        print(f"\n查询: '{test_query}'")
        print(f"使用知识库: {test_kb_ids}")
        print(f"上下文增强: {'已启用' if enable_context else '已禁用'}")
        print(f"相关性排序: {'已启用' if enable_ranking else '已禁用'}")
        
        results = search_documents(
            test_query, 
            knowledge_base_ids=test_kb_ids,
            return_scores=show_scores,
            enable_context_enrichment=enable_context,
            enable_ranking=enable_ranking
        )
        
        print(f"找到 {len(results)} 个相关文档:")
        
        for i, item in enumerate(results, 1):
            if show_scores:
                doc, scores = item
                print(f"\n文档 {i} ({os.path.basename(doc.metadata.get('source', '未知'))}):")
                print(f"上下文增强: {'是' if doc.metadata.get('context_enriched', False) else '否'}")
                print(f"来源信息:\n{get_document_source_info(doc)}")
                print(f"文档类型: {_info_extractor.get_document_type(doc.metadata.get('source', ''))}")
                print(f"相关性分数:")
                for score_name, score_value in scores.items():
                    print(f"  - {score_name}: {score_value:.4f}")
                print(f"内容:\n{doc.page_content}")
            else:
                doc = item
                print(f"\n文档 {i} ({os.path.basename(doc.metadata.get('source', '未知'))}):")
                print(f"来源信息:\n{get_document_source_info(doc)}")
                print(f"内容:\n{doc.page_content}")
            print("-" * 50)


if __name__ == "__main__":
    main()