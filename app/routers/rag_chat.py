"""
RAG聊天路由
提供基于知识库的智能对话功能
"""

import os
import json
import sys
import asyncio
from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, HTTPException, Request, Query, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

# 添加dfy_langchain目录到路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
dfy_langchain_path = os.path.join(project_root, "dfy_langchain")

if dfy_langchain_path not in sys.path:
    sys.path.insert(0, dfy_langchain_path)

# 尝试导入真正的RAG生成器
RAGGenerator = None
try:
    from rag_generation import RAGGenerator
    print("成功导入dfy_langchain.RAGGenerator")
except ImportError as e:
    print(f"无法导入dfy_langchain.RAGGenerator: {e}")
    try:
        # 尝试使用绝对导入
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'dfy_langchain'))
        from rag_generation import RAGGenerator
        print("使用绝对路径成功导入RAGGenerator")
    except ImportError as e2:
        print(f"绝对路径导入也失败: {e2}")
        RAGGenerator = None

router = APIRouter(prefix="/rag", tags=["RAG聊天"])
templates = Jinja2Templates(directory="templates")

# 全局RAG生成器实例
rag_generator = None

# 添加数据库依赖导入
from app.database import get_db
from app.services.model_config_service import ModelConfigService

class ModelConfig(BaseModel):
    """模型配置模型"""
    model_id: Optional[int] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None
    endpoint: Optional[str] = None
    display_name: Optional[str] = None

class ChatMessage(BaseModel):
    """聊天消息模型"""
    message: str
    knowledge_bases: List[str] = []
    knowledge_base_ids: List[Union[str, int]] = []
    history: List[dict] = []
    session_id: Optional[str] = None
    # RAG配置参数 - 基础检索配置
    top_k: Optional[int] = 10
    threshold: Optional[float] = 0.3
    context_window: Optional[int] = 150
    keyword_threshold: Optional[int] = 1
    # RAG配置参数 - 增强功能
    enable_context_enrichment: Optional[bool] = True
    enable_ranking: Optional[bool] = True
    rerank: Optional[bool] = False
    # RAG配置参数 - 生成器配置
    temperature: Optional[float] = 0.3
    memory_window: Optional[int] = 5
    # 修复字段名冲突：model_config改为selected_model
    selected_model: Optional[ModelConfig] = None

class KnowledgeBaseInfo(BaseModel):
    """知识库信息模型"""
    id: int
    name: str
    description: str
    status: str

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    knowledge_bases: List[str] = []
    knowledge_base_ids: List[Union[str, int]] = []
    history: List[dict] = []
    session_id: Optional[str] = None
    # RAG配置参数 - 基础检索配置
    top_k: Optional[int] = 10
    threshold: Optional[float] = 0.3
    context_window: Optional[int] = 150
    keyword_threshold: Optional[int] = 1
    # RAG配置参数 - 增强功能
    enable_context_enrichment: Optional[bool] = True
    enable_ranking: Optional[bool] = True
    rerank: Optional[bool] = False
    # RAG配置参数 - 生成器配置
    temperature: Optional[float] = 0.3
    memory_window: Optional[int] = 5
    # 检索器类型配置
    retriever_type: Optional[str] = "auto"
    # 修复字段名冲突：model_config改为selected_model
    selected_model: Optional[ModelConfig] = None

def get_model_config_from_db(db: Session, model_id: int) -> Optional[dict]:
    """从数据库获取模型配置"""
    try:
        model_config = ModelConfigService.get_model_config_by_id(db, model_id)
        if model_config:
            return {
                "provider": model_config.provider,
                "model_name": model_config.model_name,
                "api_key": model_config.api_key,
                "endpoint": model_config.endpoint,
                "organization": model_config.organization
            }
        return None
    except Exception as e:
        print(f"获取模型配置失败: {e}")
        return None

def create_dynamic_rag_generator(model_config: dict = None, rag_config: dict = None):
    """创建动态RAG生成器"""
    if RAGGenerator is None:
        print("RAGGenerator类不可用")
        return None
    
    try:
        # 设置知识库路径
        kb_path = os.path.join("data", "knowledge_base")
        
        # 设置RAG配置参数，使用前端传递的值或默认值
        if rag_config is None:
            rag_config = {}
        
        # 添加详细的调试日志
        print("=" * 60)
        print("🔧 RAG配置参数详情:")
        print(f"  📊 接收到的rag_config: {rag_config}")
        
        # 基础检索配置
        top_k = rag_config.get("top_k", int(os.getenv("RAG_TOP_K", "5")))
        threshold = rag_config.get("threshold", float(os.getenv("RAG_THRESHOLD", "0.7")))
        context_window = rag_config.get("context_window", int(os.getenv("RAG_CONTEXT_WINDOW", "150")))
        keyword_threshold = rag_config.get("keyword_threshold", int(os.getenv("RAG_KEYWORD_THRESHOLD", "1")))
        
        # 增强功能配置
        enable_context_enrichment = rag_config.get("enable_context_enrichment", 
                                                   os.getenv("ENABLE_CONTEXT_ENRICHMENT", "true").lower() == "true")
        enable_ranking = rag_config.get("enable_ranking", 
                                       os.getenv("ENABLE_RANKING", "true").lower() == "true")
        rerank = rag_config.get("rerank", 
                               os.getenv("ENABLE_RERANK", "false").lower() == "true")
        
        # 生成器配置
        temperature = rag_config.get("temperature", float(os.getenv("RAG_TEMPERATURE", "0.3")))
        memory_window = rag_config.get("memory_window", int(os.getenv("RAG_MEMORY_WINDOW", "5")))
        
        print(f"  🎯 基础检索配置:")
        print(f"    - top_k: {top_k}")
        print(f"    - threshold: {threshold}")
        print(f"    - context_window: {context_window}")
        print(f"    - keyword_threshold: {keyword_threshold}")
        print(f"  🚀 增强功能配置:")
        print(f"    - enable_context_enrichment: {enable_context_enrichment}")
        print(f"    - enable_ranking: {enable_ranking}")
        print(f"    - rerank: {rerank}")
        print(f"  🎛️ 生成器配置:")
        print(f"    - temperature: {temperature}")
        print(f"    - memory_window: {memory_window}")
        print("=" * 60)
        
        # 如果有模型配置，使用用户选择的模型；否则使用默认配置
        if model_config:
            # 处理模型提供商兼容性问题
            provider = model_config["provider"]
            
            # 将所有OpenAI兼容的提供商统一处理
            openai_compatible_providers = ["openai-compatible", "deepseek"]
            if provider in openai_compatible_providers:
                provider = "openai"  # 统一映射为openai
                print(f"✅ 提供商映射: {model_config['provider']} -> {provider}")
            
            # 规范化API URL
            api_url = model_config["endpoint"]
            if api_url:
                # 确保URL以正确的路径结尾
                api_url = api_url.rstrip('/')
                if not api_url.endswith('/v1'):
                    api_url += '/v1'
                
                # 验证URL格式
                if not (api_url.startswith('http://') or api_url.startswith('https://')):
                    print(f"警告：API URL格式可能不正确: {api_url}")
            
            print(f"使用用户选择的模型配置: {provider} - {model_config['model_name']}")
            print(f"原始提供商: {model_config['provider']}")
            print(f"规范化后的API URL: {api_url}")
            
            # 在创建生成器前验证API配置
            if not model_config.get("api_key"):
                print("警告：API密钥未配置")
                return None
            
            rag_generator = RAGGenerator(
                model_name=model_config["model_name"],
                model_provider=provider,  # 使用转换后的provider
                temperature=temperature,
                top_k=top_k,
                enable_context_enrichment=enable_context_enrichment,
                enable_ranking=enable_ranking,
                memory_window_size=memory_window,
                knowledge_base_path=kb_path,
                api_key=model_config["api_key"],
                api_url=api_url,
                # 传递新增的RAG配置参数
                keyword_threshold=keyword_threshold,
                context_window=context_window,
                score_threshold=threshold,
                weight_keyword_freq=0.4,  # 使用默认权重
                weight_keyword_pos=0.3,
                weight_keyword_coverage=0.3
            )
        else:
            print("使用默认模型配置")
            rag_generator = RAGGenerator(
                model_name=os.getenv("RAG_MODEL_NAME", "deepseek-chat"),
                model_provider=os.getenv("RAG_MODEL_PROVIDER", "openai"),
                temperature=temperature,
                top_k=top_k,
                enable_context_enrichment=enable_context_enrichment,
                enable_ranking=enable_ranking,
                memory_window_size=memory_window,
                knowledge_base_path=kb_path,
                # 传递新增的RAG配置参数
                keyword_threshold=keyword_threshold,
                context_window=context_window,
                score_threshold=threshold,
                weight_keyword_freq=0.4,  # 使用默认权重
                weight_keyword_pos=0.3,
                weight_keyword_coverage=0.3
            )
        
        print("✅ 动态RAG生成器初始化成功")
        return rag_generator
    except Exception as e:
        print(f"❌ 动态RAG生成器初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def init_rag_generator():
    """初始化RAG生成器"""
    global rag_generator
    if rag_generator is None and RAGGenerator is not None:
        try:
            # 设置知识库路径
            kb_path = os.path.join("data", "knowledge_base")
            
            print("开始初始化真正的RAG生成器...")
            rag_generator = RAGGenerator(
                model_name=os.getenv("RAG_MODEL_NAME", "deepseek-chat"),
                model_provider=os.getenv("RAG_MODEL_PROVIDER", "openai"),
                temperature=float(os.getenv("RAG_TEMPERATURE", "0.3")),
                top_k=int(os.getenv("RAG_TOP_K", "5")),
                enable_context_enrichment=True,
                enable_ranking=True,
                memory_window_size=10,
                knowledge_base_path=kb_path,
                # 传递新增的RAG配置参数
                keyword_threshold=int(os.getenv("RAG_KEYWORD_THRESHOLD", "1")),
                context_window=int(os.getenv("RAG_CONTEXT_WINDOW", "150")),
                score_threshold=float(os.getenv("RAG_THRESHOLD", "0.7")),
                weight_keyword_freq=0.4,  # 使用默认权重
                weight_keyword_pos=0.3,
                weight_keyword_coverage=0.3
            )
            print("RAG生成器初始化成功 - 使用真正的dfy_langchain实现")
            return rag_generator
        except Exception as e:
            print(f"RAG生成器初始化失败: {e}")
            import traceback
            traceback.print_exc()
            rag_generator = None
    
    # 如果RAGGenerator为None或初始化失败，返回None而不是创建简化版本
    if rag_generator is None:
        print("无法初始化RAG生成器，检查dfy_langchain模块和环境配置")
        return None
    
    return rag_generator

def load_knowledge_bases() -> List[Dict[str, Any]]:
    """加载知识库列表"""
    try:
        kb_file = os.path.join("data", "knowledge_base", "knowledge_bases.json")
        if os.path.exists(kb_file):
            with open(kb_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("knowledge_bases", [])
        return []
    except Exception as e:
        print(f"加载知识库列表失败: {e}")
        return []

@router.get("/api/knowledge-bases")
async def get_knowledge_bases():
    """获取知识库列表API"""
    try:
        knowledge_bases = load_knowledge_bases()
        
        # 为每个知识库添加文档数量
        from app.services.knowledge_base_service import KnowledgeBaseService
        kb_service = KnowledgeBaseService()
        
        for kb in knowledge_bases:
            kb_name = kb.get("name", "")
            if kb_name:
                kb["document_count"] = kb_service.count_knowledge_base_documents(kb_name)
            else:
                kb["document_count"] = 0
        
        return {
            "success": True,
            "knowledge_bases": knowledge_bases
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识库列表失败: {str(e)}")

@router.post("/api/chat")
async def rag_chat(chat_request: ChatMessage, db: Session = Depends(get_db)):
    """RAG聊天API"""
    try:
        # 获取知识库ID列表，优先使用knowledge_base_ids，并确保类型一致性
        kb_ids_raw = chat_request.knowledge_base_ids or chat_request.knowledge_bases
        kb_ids = [str(id) for id in kb_ids_raw]  # 统一转换为字符串
        
        # 获取模型配置
        model_config = None
        if chat_request.selected_model and chat_request.selected_model.model_id:
            model_config = get_model_config_from_db(db, chat_request.selected_model.model_id)
            if not model_config:
                print(f"无法获取模型配置，model_id: {chat_request.selected_model.model_id}")
        
        # 准备RAG配置参数
        rag_config = {
            # 基础检索配置
            "top_k": chat_request.top_k,
            "threshold": chat_request.threshold,
            "context_window": chat_request.context_window,
            "keyword_threshold": chat_request.keyword_threshold,
            # 增强功能配置
            "enable_context_enrichment": chat_request.enable_context_enrichment,
            "enable_ranking": chat_request.enable_ranking,
            "rerank": chat_request.rerank,
            # 生成器配置
            "temperature": chat_request.temperature,
            "memory_window": chat_request.memory_window
        }
        
        # 创建动态RAG生成器
        generator = create_dynamic_rag_generator(model_config, rag_config)
        if generator is None:
            # 如果RAG生成器不可用，返回简单的回复
            return {
                "success": True,
                "answer": "抱歉，RAG系统当前不可用。这是一个模拟回复：您询问了 \"" + chat_request.message + "\"，但我暂时无法基于知识库回答。",
                "query": chat_request.message,
                "source_documents": [],
                "knowledge_bases_used": kb_ids
            }
        
        # 处理日志中的模型提供商显示
        display_provider = model_config['provider'] if model_config else ""
        if display_provider == "openai-compatible":
            display_provider = "openai"
        model_info = f" (使用模型: {display_provider} - {model_config['model_name']})" if model_config else ""
        print(f"使用RAG配置 - top_k: {rag_config['top_k']}, threshold: {rag_config['threshold']}, "
              f"context_window: {rag_config['context_window']}, temperature: {rag_config['temperature']}{model_info}")
        
        # 使用RAG生成器进行查询和生成
        result = generator.retrieve_and_generate(
            query=chat_request.message,
            knowledge_base_ids=kb_ids,
            return_source_documents=True
        )
        
        # 格式化源文档信息
        source_docs = []
        if "source_documents" in result:
            seen_sources = set()  # 用于记录已经见过的源文件
            
            for doc in result["source_documents"]:
                source_name = os.path.basename(doc.metadata.get("source", "未知来源"))
                
                # 如果这个源文件还没有被添加过，则添加
                if source_name not in seen_sources:
                    seen_sources.add(source_name)
                    source_docs.append({
                        "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                        "source": source_name,
                        "page": doc.metadata.get("page", None)
                    })
        
        return {
            "success": True,
            "answer": result.get("answer", "无法生成回答"),
            "query": result.get("query", chat_request.message),
            "source_documents": source_docs,
            "knowledge_bases_used": kb_ids,
            "config_used": {
                "top_k": rag_config['top_k'],
                "threshold": rag_config['threshold'],
                "context_window": rag_config['context_window'],
                "keyword_threshold": rag_config['keyword_threshold'],
                "enable_context_enrichment": rag_config['enable_context_enrichment'],
                "enable_ranking": rag_config['enable_ranking'],
                "rerank": rag_config['rerank'],
                "temperature": rag_config['temperature'],
                "memory_window": rag_config['memory_window'],
                "model_config": model_config
            }
        }
        
    except Exception as e:
        print(f"RAG聊天处理失败: {e}")
        # 返回错误信息而不是抛出异常
        return {
            "success": False,
            "error": f"聊天处理失败: {str(e)}",
            "answer": "抱歉，处理您的请求时出现错误，请稍后重试。",
            "query": chat_request.message,
            "source_documents": [],
            "knowledge_bases_used": kb_ids
        }

def get_rag_generator():
    """获取RAG生成器实例"""
    return init_rag_generator()

@router.post("/api/chat-stream")
async def rag_chat_stream(chat_request: ChatRequest, db: Session = Depends(get_db)):
    """
    流式RAG聊天API (支持服务器发送事件)
    """
    async def generate_stream():
        try:
            # 获取知识库ID列表
            kb_ids_raw = chat_request.knowledge_base_ids or chat_request.knowledge_bases
            kb_ids = [str(id) for id in kb_ids_raw]
            
            # 获取模型配置
            model_config = None
            if chat_request.selected_model and chat_request.selected_model.model_id:
                model_config = get_model_config_from_db(db, chat_request.selected_model.model_id)
                if not model_config:
                    error_msg = f"无法获取模型配置，model_id: {chat_request.selected_model.model_id}"
                    print(error_msg)
                    yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                    return
            
            # 验证模型配置
            if model_config:
                if not model_config.get("api_key"):
                    error_msg = "模型配置中缺少API密钥，请检查配置"
                    yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                    return
                
                if not model_config.get("endpoint"):
                    error_msg = "模型配置中缺少API端点，请检查配置"
                    yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                    return
            
            # 准备RAG配置参数
            rag_config = {
                # 基础检索配置
                "top_k": chat_request.top_k,
                "threshold": chat_request.threshold,
                "context_window": chat_request.context_window,
                "keyword_threshold": chat_request.keyword_threshold,
                # 增强功能配置
                "enable_context_enrichment": chat_request.enable_context_enrichment,
                "enable_ranking": chat_request.enable_ranking,
                "rerank": chat_request.rerank,
                # 生成器配置
                "temperature": chat_request.temperature,
                "memory_window": chat_request.memory_window
            }
            
            # 创建动态RAG生成器
            generator = create_dynamic_rag_generator(model_config, rag_config)
            if generator is None:
                error_msg = "RAG系统当前不可用，请检查配置和依赖。"
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                return
            
            # 处理日志中的模型提供商显示
            display_provider = model_config['provider'] if model_config else ""
            if display_provider == "openai-compatible":
                display_provider = "openai"
            model_info = f" (使用模型: {display_provider} - {model_config['model_name']})" if model_config else ""
            print(f"流式RAG配置 - top_k: {rag_config['top_k']}, threshold: {rag_config['threshold']}, "
                  f"context_window: {rag_config['context_window']}, temperature: {rag_config['temperature']}{model_info}")
            
            # 发送开始信号
            yield f"data: {json.dumps({'type': 'start'})}\n\n"
            
            # 执行真正的RAG检索和生成
            print(f"执行RAG查询: {chat_request.message}, 知识库: {kb_ids}")
            
            try:
                result = generator.retrieve_and_generate(
                    query=chat_request.message,
                    knowledge_base_ids=kb_ids,
                    return_source_documents=True,
                    retriever_type=chat_request.retriever_type or "auto"  # 传递检索器类型
                )
            except Exception as api_error:
                # 检查是否是API连接错误
                error_str = str(api_error)
                if "404" in error_str and "Not Found" in error_str:
                    error_msg = f"API端点不可用 (404错误)。可能的原因：\n1. API服务器宕机\n2. 端点URL不正确\n3. 需要添加/v1路径\n\n当前配置：{model_config.get('endpoint') if model_config else '默认配置'}"
                elif "Connection" in error_str or "timeout" in error_str.lower():
                    error_msg = f"无法连接到API服务器。请检查：\n1. 网络连接\n2. API服务器状态\n3. 端点URL是否正确\n\n错误详情：{error_str}"
                elif "401" in error_str or "Unauthorized" in error_str:
                    error_msg = f"API密钥验证失败。请检查：\n1. API密钥是否正确\n2. API密钥是否有效\n3. 是否有权限访问该模型"
                else:
                    error_msg = f"API调用失败：{error_str}"
                
                print(f"RAG API调用失败: {error_msg}")
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                return
            
            # 获取生成的回答
            answer = result.get("answer", "未能生成回答")
            
            # 逐字符流式发送回答
            for char in answer:
                yield f"data: {json.dumps({'type': 'message', 'content': char})}\n\n"
                await asyncio.sleep(0.03)  # 控制发送速度，模拟真实的生成过程
            
            # 发送源文档信息（如果有）
            source_documents = result.get("source_documents", [])
            if source_documents:
                # 使用集合来去重源文档
                seen_sources = set()
                unique_sources = []
                
                for doc in source_documents:
                    source_name = os.path.basename(doc.metadata.get("source", "未知来源"))
                    # 只有当源文档名称未出现过时才添加
                    if source_name not in seen_sources:
                        seen_sources.add(source_name)
                        unique_sources.append(source_name)
                
                if unique_sources:
                    source_info = "\n\n📚 参考来源:\n"
                    for i, source_name in enumerate(unique_sources[:3], 1):  # 只显示前3个不重复的源文档
                        source_info += f"{i}. {source_name}\n"
                    
                    # 发送源文档信息
                    for char in source_info:
                        yield f"data: {json.dumps({'type': 'message', 'content': char})}\n\n"
                        await asyncio.sleep(0.01)
            
            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            print(f"流式RAG聊天处理失败: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': f'处理请求时发生错误: {str(e)}'})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@router.post("/api/clear-history")
async def clear_chat_history():
    """清除聊天历史"""
    try:
        generator = get_rag_generator()
        if generator:
            generator.clear_history()
        return {"success": True, "message": "聊天历史已清除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除历史失败: {str(e)}")

@router.get("/api/test")
async def test_rag_system():
    """测试RAG系统状态"""
    try:
        generator = init_rag_generator()
        if generator is None:
            return {
                "success": False,
                "message": "RAG生成器未初始化",
                "status": "offline"
            }
        
        # 简单测试查询
        test_result = generator.retrieve_and_generate(
            query="测试查询",
            return_source_documents=False
        )
        
        return {
            "success": True,
            "message": "RAG系统运行正常",
            "status": "online",
            "test_result": test_result
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"RAG系统测试失败: {str(e)}",
            "status": "error"
        } 