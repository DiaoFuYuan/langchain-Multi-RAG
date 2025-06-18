from .document_loaders.unstrcutured_loader import UnstructuredLoader
from .text_splitter.chinese_recursive_text_splitter import ChineseRecursiveTextSplitter
import os 
import mimetypes
from typing import Optional
from langchain_huggingface import HuggingFaceEmbeddings
import torch
from langchain_community.vectorstores import FAISS
import hashlib
import json
from datetime import datetime
import gc

def test_chunk(chunks):
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}:")
        print(f"Content: {chunk.page_content}")
        print(f"Metadata: {chunk.metadata}")
        print("-" * 50)

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

class RAGPipeline:
    def __init__(
        self, 
        file_path: str, 
        vector_store_path: str = None,
        embedding_config_id: Optional[int] = None,
        embedding_config: Optional[dict] = None,
        use_local_embedding: bool = True
    ):
        """
        初始化RAG管道
        
        Args:
            file_path: 文件路径
            vector_store_path: 向量存储路径
            embedding_config_id: embedding模型配置ID（从数据库获取）
            embedding_config: embedding模型配置字典（直接传入配置）
            use_local_embedding: 是否使用本地embedding模型（当未提供配置时的默认行为）
        """
        self.file_path = file_path
        # 如果指定了vector_store_path，使用指定路径，否则使用默认路径
        if vector_store_path:
            self.vector_store_path = vector_store_path
        else:
            self.vector_store_path = os.path.join(os.path.dirname(file_path), "vector_store")
        
        self.file_info_path = os.path.join(self.vector_store_path, "file_info.json")
        
        # 获取最佳设备
        device = _get_optimal_device()
        
        # 获取embedding模型实例
        self.embeddings = self._init_embeddings(
            device, 
            embedding_config_id, 
            embedding_config, 
            use_local_embedding
        )
        
        # 确保向量库目录存在
        if not os.path.exists(self.vector_store_path):
            os.makedirs(self.vector_store_path)
        
        # 初始化 FAISS GPU 支持
        self._initialize_faiss_gpu()

    def _init_embeddings(
        self, 
        device: str, 
        embedding_config_id: Optional[int] = None,
        embedding_config: Optional[dict] = None,
        use_local_embedding: bool = True
    ):
        """
        初始化embedding模型
        
        Args:
            device: 设备
            embedding_config_id: embedding模型配置ID
            embedding_config: embedding模型配置字典
            use_local_embedding: 是否使用本地embedding模型
            
        Returns:
            Embedding模型实例
        """
        try:
            # 导入embedding模块
            from .embedding_model.local_embeddings import get_embedding_from_config, create_local_embeddings
            
            # 如果提供了配置ID或配置字典，优先使用
            if embedding_config_id is not None or embedding_config is not None:
                print(f"使用数据库配置的embedding模型 (ID: {embedding_config_id})")
                return get_embedding_from_config(
                    config_id=embedding_config_id,
                    config=embedding_config
                )
            
            # 否则根据use_local_embedding参数决定
            if use_local_embedding:
                # 使用本地embedding模型
                current_dir = os.path.dirname(os.path.abspath(__file__))
                embedding_model_path = os.path.join(current_dir, "embedding_model", "bce-embedding-base_v1")
                
                print(f"使用本地embedding模型: {embedding_model_path}")
                return create_local_embeddings(
                    model_name="bce-embedding-base_v1",
                    model_path=embedding_model_path,
                    device=device
                )
            else:
                # 如果不使用本地模型但也没有提供配置，使用HuggingFace默认实现
                print("使用HuggingFace默认embedding模型")
                try:
                    from langchain_huggingface import HuggingFaceEmbeddings
                except ImportError:
                    from langchain_community.embeddings import HuggingFaceEmbeddings
                
                current_dir = os.path.dirname(os.path.abspath(__file__))
                embedding_model_path = os.path.join(current_dir, "embedding_model", "bce-embedding-base_v1")
                
                return HuggingFaceEmbeddings(
                    model_name=embedding_model_path,
                    model_kwargs={"device": device},
                    encode_kwargs={"normalize_embeddings": True}
                )
                
        except Exception as e:
            print(f"初始化embedding模型失败: {e}")
            print("回退到HuggingFace默认实现")
            
            # 回退到原来的实现
            try:
                from langchain_huggingface import HuggingFaceEmbeddings
            except ImportError:
                from langchain_community.embeddings import HuggingFaceEmbeddings
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            embedding_model_path = os.path.join(current_dir, "embedding_model", "bce-embedding-base_v1")
            
            return HuggingFaceEmbeddings(
                model_name=embedding_model_path,
                model_kwargs={"device": device},
                encode_kwargs={"normalize_embeddings": True}
            )

    def _initialize_faiss_gpu(self):
        """初始化 FAISS GPU 支持"""
        self.faiss_gpu_available = False
        self.gpu_resources = None
        self.faiss = None
        
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
    
    def _convert_index_to_gpu(self, vectorstore):
        """将 FAISS 索引转换为 GPU 版本"""
        if not self.faiss_gpu_available or not hasattr(vectorstore, 'index'):
            return vectorstore
        
        try:
            index = vectorstore.index
            index_type = type(index).__name__
            
            # 检查索引是否已在 GPU 上
            if 'Gpu' in index_type:
                print(f"索引已在 GPU 上，类型: {index_type}")
                return vectorstore
            
            print(f"原始索引类型: {index_type}，准备转换为 GPU")
            
            # 将索引转移到 GPU
            gpu_index = self.faiss.index_cpu_to_gpu(
                self.gpu_resources, 
                0,  # GPU 设备 ID
                index
            )
            
            # 替换向量存储中的索引
            vectorstore.index = gpu_index
            gpu_index_type = type(gpu_index).__name__
            
            print(f"成功将 FAISS 索引转移到 GPU，索引大小: {gpu_index.ntotal}，GPU 索引类型: {gpu_index_type}")
            return vectorstore
            
        except Exception as e:
            print(f"GPU 索引转换失败: {e}")
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

    def _clear_gpu_memory(self):
        """清理GPU/NPU显存"""
        try:
            # 清理NPU内存
            try:
                import torch_npu
                if torch.npu.is_available():
                    torch.npu.empty_cache()
                    torch.npu.synchronize()
                    print("已清理NPU显存")
            except ImportError:
                pass
            
            # 清理CUDA内存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                print("已清理GPU显存")
            
            # 强制垃圾回收
            gc.collect()
        except Exception as e:
            print(f"清理显存时出现警告: {str(e)}")

    def _get_file_hash(self, file_path):
        """获取文件的MD5哈希值"""
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        return file_hash

    def _load_file_info(self):
        """加载文件信息记录"""
        if os.path.exists(self.file_info_path):
            with open(self.file_info_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_file_info(self, file_info):
        """保存文件信息记录"""
        with open(self.file_info_path, 'w', encoding='utf-8') as f:
            json.dump(file_info, f, ensure_ascii=False, indent=2)

    def load_single_document(self, file_path: str):
        """加载单个文档并更新向量库"""
        try:
            if not os.path.exists(file_path):
                print(f"文件不存在: {file_path}")
                return False
                
            if not os.path.isfile(file_path):
                print(f"路径不是文件: {file_path}")
                return False
            
            # 加载现有的文件信息
            file_info = self._load_file_info()
            
            # 检查是否已存在向量库
            vectorstore = None
            
            faiss_index_path = os.path.join(self.vector_store_path, "index.faiss")
            if os.path.exists(faiss_index_path):
                try:
                    # 尝试加载现有的向量库
                    vectorstore = FAISS.load_local(
                        self.vector_store_path, 
                        self.embeddings,
                        allow_dangerous_deserialization=True
                    )
                    print(f"已加载现有向量库: {self.vector_store_path}")
                    
                    # 转换为 GPU 索引并优化
                    vectorstore = self._convert_index_to_gpu(vectorstore)
                    vectorstore = self._optimize_gpu_index(vectorstore)
                    
                except Exception as e:
                    print(f"加载向量库失败: {e}")
                    # 如果加载失败，将创建新的向量库
                    vectorstore = None
            
            file_hash = self._get_file_hash(file_path)
            
            # 检查文件是否已处理过且未变更
            if file_path in file_info and file_info[file_path]["hash"] == file_hash:
                print(f"文件 {file_path} 未发生变化，跳过处理")
                return True
                
            print(f"正在处理文件: {file_path}")
            
            # 文档加载阶段
            self.unstructured_loader = UnstructuredLoader(file_path)
            doc, file_type = self.unstructured_loader.load_file()
            
            # 清理加载器占用的内存
            del self.unstructured_loader
            self._clear_gpu_memory()
            
            # 检查是否成功加载了文档
            if not doc:
                print(f"文件 {file_path} 未成功加载")
                return False
            
            # 更新文件信息
            file_info[file_path] = {
                "hash": file_hash,
                "last_updated": datetime.now().isoformat(),
                "file_type": file_type
            }
            
            # 根据文件类型选择不同的分块大小
            if file_type == "excel":
                chunk_size = 3000
                chunk_overlap = 0
            else:
                chunk_size = 1500  # 增加块大小，减少块数量
                chunk_overlap = 150  # 保持10%的重叠率
            
            # 使用相同的分词器但不同的参数
            text_splitter = ChineseRecursiveTextSplitter(
                keep_separator=True,
                is_separator_regex=True,
                chunk_size=chunk_size, 
                chunk_overlap=chunk_overlap)
            
            chunks = text_splitter.split_documents(doc)
            
            # 清理文档和分词器占用的内存
            del doc
            del text_splitter
            self._clear_gpu_memory()
            
            # 确保每个块都包含文件源信息
            for chunk in chunks:
                if 'source' not in chunk.metadata:
                    chunk.metadata['source'] = file_path
            
            # 将文档添加到向量库
            if vectorstore is None:
                vectorstore = FAISS.from_documents(chunks, self.embeddings)
                print(f"创建新的向量库: {self.vector_store_path}")
                
                # 转换为 GPU 索引并优化
                vectorstore = self._convert_index_to_gpu(vectorstore)
                vectorstore = self._optimize_gpu_index(vectorstore)
            else:
                vectorstore.add_documents(chunks)
                
                # 重新转换和优化（因为添加了新文档）
                vectorstore = self._convert_index_to_gpu(vectorstore)
                vectorstore = self._optimize_gpu_index(vectorstore)
            
            # 清理chunks占用的内存
            del chunks
            self._clear_gpu_memory()
            
            print(f"已处理文件: {file_path}, 向量化完成")
            
            # 保存向量库和文件信息
            if vectorstore:
                try:
                    # 确保向量存储目录存在
                    if not os.path.exists(self.vector_store_path):
                        os.makedirs(self.vector_store_path, exist_ok=True)
                    
                    # 检查路径是否包含中文字符
                    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in self.vector_store_path)
                    
                    if has_chinese:
                        # 如果路径包含中文，使用临时英文路径保存，然后移动文件
                        import tempfile
                        import shutil
                        
                        # 创建临时目录
                        temp_dir = tempfile.mkdtemp()
                        print(f"使用临时路径保存向量库: {temp_dir}")
                        
                        # 检查是否为 GPU 索引，如果是则转换为 CPU 索引后保存
                        if hasattr(vectorstore, 'index') and 'Gpu' in type(vectorstore.index).__name__:
                            print("检测到 GPU 索引，转换为 CPU 索引后保存")
                            try:
                                import faiss
                                # 将 GPU 索引转换为 CPU 索引
                                cpu_index = faiss.index_gpu_to_cpu(vectorstore.index)
                                # 临时替换索引
                                original_index = vectorstore.index
                                vectorstore.index = cpu_index
                                # 保存到临时目录
                                vectorstore.save_local(temp_dir)
                                # 恢复 GPU 索引
                                vectorstore.index = original_index
                                print("GPU 索引转换保存完成")
                            except Exception as e:
                                print(f"GPU 索引转换保存失败: {e}")
                                # 如果转换失败，尝试直接保存
                                vectorstore.save_local(temp_dir)
                        else:
                            # 保存到临时目录
                            vectorstore.save_local(temp_dir)
                        
                        # 移动文件到目标目录
                        temp_index_file = os.path.join(temp_dir, "index.faiss")
                        temp_pkl_file = os.path.join(temp_dir, "index.pkl")
                        
                        target_index_file = os.path.join(self.vector_store_path, "index.faiss")
                        target_pkl_file = os.path.join(self.vector_store_path, "index.pkl")
                        
                        if os.path.exists(temp_index_file):
                            shutil.move(temp_index_file, target_index_file)
                        if os.path.exists(temp_pkl_file):
                            shutil.move(temp_pkl_file, target_pkl_file)
                            
                        # 清理临时目录
                        shutil.rmtree(temp_dir)
                        print(f"向量库文件已移动到: {self.vector_store_path}")
                    else:
                        # 如果路径不包含中文，直接保存
                        abs_vector_path = os.path.abspath(self.vector_store_path)
                        print(f"准备保存向量库到: {abs_vector_path}")
                        os.makedirs(abs_vector_path, exist_ok=True)
                        
                        # 检查是否为 GPU 索引，如果是则转换为 CPU 索引后保存
                        if hasattr(vectorstore, 'index') and 'Gpu' in type(vectorstore.index).__name__:
                            print("检测到 GPU 索引，转换为 CPU 索引后保存")
                            try:
                                import faiss
                                # 将 GPU 索引转换为 CPU 索引
                                cpu_index = faiss.index_gpu_to_cpu(vectorstore.index)
                                # 临时替换索引
                                original_index = vectorstore.index
                                vectorstore.index = cpu_index
                                # 保存
                                vectorstore.save_local(abs_vector_path)
                                # 恢复 GPU 索引
                                vectorstore.index = original_index
                                print("GPU 索引转换保存完成")
                            except Exception as e:
                                print(f"GPU 索引转换保存失败: {e}")
                                # 如果转换失败，尝试直接保存
                                vectorstore.save_local(abs_vector_path)
                        else:
                            vectorstore.save_local(abs_vector_path)
                    
                    # 清理向量库占用的内存
                    del vectorstore
                    self._clear_gpu_memory()
                    
                    self._save_file_info(file_info)
                    print(f"单个文档向量化完成: {file_path}")
                    return True
                    
                except Exception as e:
                    print(f"保存向量库失败: {e}")
                    print(f"向量存储路径: {self.vector_store_path}")
                    print(f"路径是否存在: {os.path.exists(self.vector_store_path)}")
                    import traceback
                    traceback.print_exc()
                    return False
            else:
                print("向量库创建失败")
                return False
                
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")
            import traceback
            traceback.print_exc()
            # 即使出错也要清理显存
            self._clear_gpu_memory()
            return False

    def load_documents(self):
        """加载文档并增量更新向量库"""
        # 获取目录下所有文件
        if not os.path.exists(self.file_path):
            print(f"文件路径不存在: {self.file_path}")
            return
            
        file_paths = os.listdir(self.file_path)
        # 过滤掉元数据文件和其他非文档文件
        filtered_files = []
        for file_path_name in file_paths:
            # 跳过元数据文件和隐藏文件
            if file_path_name.startswith('.') or file_path_name == 'documents_metadata.json':
                print(f"跳过非文档文件: {file_path_name}")
                continue
            filtered_files.append(os.path.join(self.file_path, file_path_name))
        
        file_ob_paths = filtered_files
        
        # 加载现有的文件信息
        file_info = self._load_file_info()
        
        # 检查是否已存在向量库
        vectorstore = None
        
        faiss_index_path = os.path.join(self.vector_store_path, "index.faiss")
        if os.path.exists(faiss_index_path):
            try:
                # 尝试加载现有的向量库
                vectorstore = FAISS.load_local(
                    self.vector_store_path, 
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                print(f"已加载现有向量库: {self.vector_store_path}")
                
                # 转换为 GPU 索引并优化
                vectorstore = self._convert_index_to_gpu(vectorstore)
                vectorstore = self._optimize_gpu_index(vectorstore)
                
            except Exception as e:
                print(f"加载向量库失败: {e}")
                # 如果加载失败，将创建新的向量库
                vectorstore = None
        
        updated = False
        total_processed = 0
        
        for file in file_ob_paths:
            if not os.path.isfile(file):
                continue
                
            file_hash = self._get_file_hash(file)
            
            # 检查文件是否已处理过且未变更
            if file in file_info and file_info[file]["hash"] == file_hash:
                print(f"文件 {file} 未发生变化，跳过处理")
                continue
                
            print("--------------------------------正在处理{}文件".format(file))
            try:
                self.unstructured_loader = UnstructuredLoader(file)
                doc, file_type = self.unstructured_loader.load_file()
                
                # 检查是否成功加载了文档
                if not doc:
                    print(f"文件 {file} 未成功加载，跳过")
                    continue
                
                # 更新文件信息
                file_info[file] = {
                    "hash": file_hash,
                    "last_updated": datetime.now().isoformat(),
                    "file_type": file_type
                }
                updated = True
                
                # 根据文件类型选择不同的分块大小
                if file_type == "excel":
                    chunk_size = 3000
                    chunk_overlap = 0
                else:
                    chunk_size = 1500  # 增加块大小，减少块数量
                    chunk_overlap = 150  # 保持10%的重叠率
                
                # 使用相同的分词器但不同的参数
                text_splitter = ChineseRecursiveTextSplitter(
                    keep_separator=True,
                    is_separator_regex=True,
                    chunk_size=chunk_size, 
                    chunk_overlap=chunk_overlap)
                
                chunks = text_splitter.split_documents(doc)
                
                # 确保每个块都包含文件源信息
                for chunk in chunks:
                    if 'source' not in chunk.metadata:
                        chunk.metadata['source'] = file
                
                # 将文档添加到向量库
                if vectorstore is None:
                    vectorstore = FAISS.from_documents(chunks, self.embeddings)
                    print(f"创建新的向量库: {self.vector_store_path}")
                    
                    # 转换为 GPU 索引并优化
                    vectorstore = self._convert_index_to_gpu(vectorstore)
                    vectorstore = self._optimize_gpu_index(vectorstore)
                else:
                    vectorstore.add_documents(chunks)
                    
                    # 重新转换和优化（因为添加了新文档）
                    vectorstore = self._convert_index_to_gpu(vectorstore)
                    vectorstore = self._optimize_gpu_index(vectorstore)
                
                total_processed += 1
                print(f"已处理文件: {file}, 生成 {len(chunks)} 个块")
                
            except Exception as e:
                print(f"处理文件 {file} 时出错: {e}")
                import traceback
                traceback.print_exc()
        
        # 如果有更新，保存向量库和文件信息
        if updated:
            if vectorstore:
                try:
                    # 确保向量存储目录存在
                    if not os.path.exists(self.vector_store_path):
                        os.makedirs(self.vector_store_path, exist_ok=True)
                    
                    # 检查路径是否包含中文字符
                    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in self.vector_store_path)
                    
                    if has_chinese:
                        # 如果路径包含中文，使用临时英文路径保存，然后移动文件
                        import tempfile
                        import shutil
                        
                        # 创建临时目录
                        temp_dir = tempfile.mkdtemp()
                        print(f"使用临时路径保存向量库: {temp_dir}")
                        
                        # 检查是否为 GPU 索引，如果是则转换为 CPU 索引后保存
                        if hasattr(vectorstore, 'index') and 'Gpu' in type(vectorstore.index).__name__:
                            print("检测到 GPU 索引，转换为 CPU 索引后保存")
                            try:
                                import faiss
                                # 将 GPU 索引转换为 CPU 索引
                                cpu_index = faiss.index_gpu_to_cpu(vectorstore.index)
                                # 临时替换索引
                                original_index = vectorstore.index
                                vectorstore.index = cpu_index
                                # 保存到临时目录
                                vectorstore.save_local(temp_dir)
                                # 恢复 GPU 索引
                                vectorstore.index = original_index
                                print("GPU 索引转换保存完成")
                            except Exception as e:
                                print(f"GPU 索引转换保存失败: {e}")
                                # 如果转换失败，尝试直接保存
                                vectorstore.save_local(temp_dir)
                        else:
                            # 保存到临时目录
                            vectorstore.save_local(temp_dir)
                        
                        # 移动文件到目标目录
                        temp_index_file = os.path.join(temp_dir, "index.faiss")
                        temp_pkl_file = os.path.join(temp_dir, "index.pkl")
                        
                        target_index_file = os.path.join(self.vector_store_path, "index.faiss")
                        target_pkl_file = os.path.join(self.vector_store_path, "index.pkl")
                        
                        if os.path.exists(temp_index_file):
                            shutil.move(temp_index_file, target_index_file)
                        if os.path.exists(temp_pkl_file):
                            shutil.move(temp_pkl_file, target_pkl_file)
                            
                        # 清理临时目录
                        shutil.rmtree(temp_dir)
                        print(f"向量库文件已移动到: {self.vector_store_path}")
                    else:
                        # 如果路径不包含中文，直接保存
                        abs_vector_path = os.path.abspath(self.vector_store_path)
                        print(f"准备保存向量库到: {abs_vector_path}")
                        os.makedirs(abs_vector_path, exist_ok=True)
                        
                        # 检查是否为 GPU 索引，如果是则转换为 CPU 索引后保存
                        if hasattr(vectorstore, 'index') and 'Gpu' in type(vectorstore.index).__name__:
                            print("检测到 GPU 索引，转换为 CPU 索引后保存")
                            try:
                                import faiss
                                # 将 GPU 索引转换为 CPU 索引
                                cpu_index = faiss.index_gpu_to_cpu(vectorstore.index)
                                # 临时替换索引
                                original_index = vectorstore.index
                                vectorstore.index = cpu_index
                                # 保存
                                vectorstore.save_local(abs_vector_path)
                                # 恢复 GPU 索引
                                vectorstore.index = original_index
                                print("GPU 索引转换保存完成")
                            except Exception as e:
                                print(f"GPU 索引转换保存失败: {e}")
                                # 如果转换失败，尝试直接保存
                                vectorstore.save_local(abs_vector_path)
                        else:
                            vectorstore.save_local(abs_vector_path)
                    
                    self._save_file_info(file_info)
                    print(f"向量库已保存到: {self.vector_store_path}, 共处理 {total_processed} 个文件")
                except Exception as e:
                    print(f"保存向量库失败: {e}")
                    print(f"向量存储路径: {self.vector_store_path}")
                    print(f"路径是否存在: {os.path.exists(self.vector_store_path)}")
                    import traceback
                    traceback.print_exc()
            else:
                print("没有文件被成功处理，向量库未更新")
        else:
            print("没有检测到新文件或文件变更，向量库保持不变")


if __name__ == "__main__":
    rag_pipeline = RAGPipeline(r"D:\ai\web_new\data\knowledge_base\测试用\content")
    rag_pipeline.load_documents()
    print(rag_pipeline.load_documents())
    

   
