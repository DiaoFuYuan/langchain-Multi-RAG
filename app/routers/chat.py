from fastapi import Request, APIRouter, HTTPException, Body, Depends
from fastapi.responses import JSONResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json
import asyncio
import time
import logging
from typing import List, Dict, Any
from sse_starlette.sse import EventSourceResponse
import os

# 导入聊天相关模块
from ..chat_ai.chatchat import ChatChat_prompt
from ..chat_ai.config.markdown_helper import markdown_processor  # 导入Markdown处理器
from ..chat_ai.config.load_key import load_key  # 导入键值加载函数
from datetime import datetime

# 导入身份验证依赖项
from ..core.auth_dependency import require_auth_redirect, require_auth_api

# 删除从api模块导入的函数，以避免导入错误

# 设置日志
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat")
templates = Jinja2Templates(directory="templates")

# 创建聊天实例
chat_instance = ChatChat_prompt(memory_type="window", memory_k=5)

# 定义list_knowledge_bases函数，避免循环导入
def list_knowledge_bases(base_dir: str = "data/knowledge_base") -> List[str]:
    """
    列出所有可用的知识库

    Args:
        base_dir: 知识库根目录

    Returns:
        知识库名称列表
    """
    try:
        if not os.path.exists(base_dir):
            logger.warning(f"知识库根目录不存在: {base_dir}")
            return []
        
        # 获取所有子目录
        kb_names = []
        for item in os.listdir(base_dir):
            item_path = os.path.join(base_dir, item)
            # 检查是否是目录且包含vector_store子目录
            if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "vector_store")):
                kb_names.append(item)
        
        return kb_names
    except Exception as e:
        logger.error(f"列出知识库时出错: {str(e)}")
        return []


@router.get("/home")
async def chat_home_page(request: Request, current_user: str = Depends(require_auth_redirect)):
    """渲染聊天主页面，解决/chat/home 404问题"""
    return templates.TemplateResponse(
        "chat/chat_home.html", 
        {"request": request, "current_user": current_user}
    )

@router.post("/api/chat")
async def chat_api(request: Request, current_user: str = Depends(require_auth_api)):
    """标准聊天API，返回完整回复"""
    try:
        data = await request.json()
        message = data.get("message", "")
        system_prompt = data.get("system_prompt", None)
        temperature = data.get("temperature", None)
        
        if not message:
            raise HTTPException(status_code=400, detail="消息不能为空")
        
        # 如果提供了系统提示词，设置给chat实例
        if system_prompt:
            chat_instance.set_system_prompt(system_prompt)
            
        # 如果提供了温度值，设置给chat实例
        if temperature is not None:
            chat_instance.set_temperature(temperature)
        
        # 处理用户输入并获取回复
        response = chat_instance.chat(message)
        
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")

@router.post("/api/chat/stream")
@router.get("/api/chat/stream")
async def chat_stream_api(request: Request, message: str = None, system_prompt: str = None, temperature: float = None, current_user: str = Depends(require_auth_api)):
    """流式聊天API，使用真正的流式响应返回AI生成内容"""
    try:
        logger.info(f"收到流式聊天请求，方法: {request.method}")
        
        # 根据请求方法获取消息
        if request.method == "GET":
            # GET请求，从查询参数获取消息
            logger.info(f"GET请求参数: message={message}, system_prompt={system_prompt}, temperature={temperature}")
            if not message:
                logger.warning("GET请求缺少message参数")
                return JSONResponse(
                    status_code=400,
                    content={"status": "error", "error": "请在查询参数中提供message"}
                )
            model_config = None
        else:
            # POST请求，从请求体获取消息
            try:
                data = await request.json()
                message = data.get("message", "")
                system_prompt = data.get("system_prompt", None)
                temperature = data.get("temperature", None)
                model_config = data.get("model_config", None)
                settings = data.get("settings", {})  # 获取设置参数
                
                # 如果settings中有参数，优先使用settings中的值
                if settings:
                    system_prompt = settings.get("prompt") or system_prompt
                    temperature = settings.get("temperature") or temperature
                
                logger.info(f"POST请求体: message={message[:20]}..., system_prompt={system_prompt}, temperature={temperature}, model_config={model_config}, settings={settings}")
            except Exception as e:
                logger.error(f"解析POST请求体出错: {str(e)}")
                return JSONResponse(
                    status_code=400,
                    content={"status": "error", "error": f"解析请求体失败: {str(e)}"}
                )
            
        if not message:
            logger.warning("消息为空")
            return JSONResponse(
                status_code=400,
                content={"status": "error", "error": "消息不能为空"}
            )
        
        # 检查是否提供了模型配置
        if not model_config:
            logger.warning("未提供模型配置")
            return JSONResponse(
                status_code=400,
                content={"status": "error", "error": "请选择一个模型"}
            )
        
        # 根据模型配置创建聊天实例
        try:
            # 导入模型配置相关的模块
            from ..services.model_config_service import ModelConfigService
            from ..database import get_db
            from sqlalchemy.orm import Session
            
            # 创建数据库会话
            db = next(get_db())
            
            # 获取模型配置详情
            config_id = model_config.get("id")
            if not config_id:
                return JSONResponse(
                    status_code=400,
                    content={"status": "error", "error": "模型配置ID无效"}
                )
            
            # 从数据库获取完整的模型配置
            model_config_obj = ModelConfigService.get_model_config_by_id(db, config_id)
            if not model_config_obj:
                return JSONResponse(
                    status_code=400,
                    content={"status": "error", "error": "找不到指定的模型配置"}
                )
            
            # 根据提供商创建相应的聊天实例
            if model_config_obj.provider == "deepseek":
                from ..chat_ai.deepseek_chat import DeepSeekChat
                current_chat_instance = DeepSeekChat(
                    api_key=model_config_obj.api_key,
                    model_name=model_config_obj.model_name,
                    endpoint=model_config_obj.endpoint
                )
            elif model_config_obj.provider in ["openai", "openai-compatible", "vllm"]:
                from ..chat_ai.openai_chat import OpenAIChat
                current_chat_instance = OpenAIChat(
                    api_key=model_config_obj.api_key,
                    model_name=model_config_obj.model_name,
                    endpoint=model_config_obj.endpoint
                )
            elif model_config_obj.provider == "anthropic":
                from ..chat_ai.anthropic_chat import AnthropicChat
                current_chat_instance = AnthropicChat(
                    api_key=model_config_obj.api_key,
                    model_name=model_config_obj.model_name,
                    endpoint=model_config_obj.endpoint
                )
            else:
                # 使用默认的聊天实例
                current_chat_instance = chat_instance
                logger.warning(f"未知的提供商 {model_config_obj.provider}，使用默认聊天实例")
            
        except Exception as e:
            logger.error(f"创建聊天实例失败: {str(e)}")
            # 如果创建失败，使用默认实例
            current_chat_instance = chat_instance
        
        # 如果提供了系统提示词，设置给chat实例
        if system_prompt:
            success = current_chat_instance.set_system_prompt(system_prompt)
            logger.info(f"设置系统提示词: {success}")
            
        # 如果提供了温度值，设置给chat实例
        if temperature is not None:
            try:
                temp_value = float(temperature)
                success = current_chat_instance.set_temperature(temp_value)
                logger.info(f"设置温度值 {temp_value}: {success}")
            except (ValueError, TypeError) as e:
                logger.warning(f"无效的温度值 {temperature}: {str(e)}")
        
        logger.info(f"开始处理流式消息: {message[:50]}...")
        
        # 创建实际的流式生成器函数
        async def stream_generator():
            try:
                # 发送开始标记
                yield json.dumps({"status": "start"}) + "\n"
                
                # 使用流式生成方法获取回复
                for chunk in current_chat_instance.chat_stream(message):
                    if chunk:
                        # 发送内容块，确保每个块都是独立的JSON对象
                        yield json.dumps({"status": "chunk", "content": chunk}) + "\n"
                        
                        # 为了方便调试，记录一些发送的内容
                        if len(chunk) < 50:
                            logger.info(f"流式发送块: {chunk}")
                        else:
                            logger.info(f"流式发送块 ({len(chunk)}字符): {chunk[:30]}...")
                
                # 发送完成标记
                yield json.dumps({"status": "done"}) + "\n"
                logger.info("流式响应发送完成")
                
            except Exception as e:
                logger.error(f"流式生成过程中出错: {str(e)}")
                # 发送错误消息
                error_data = {"status": "error", "error": f"生成过程中出错: {str(e)}"}
                yield json.dumps(error_data) + "\n"
        
        # 返回流式响应
        return StreamingResponse(
            stream_generator(),
            media_type="application/x-ndjson"  # 使用换行分隔的JSON格式
        )
        
    except Exception as e:
        # 捕获整个处理过程中的错误
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"处理流式聊天请求出错: {str(e)}\n{error_trace}")
        
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": f"处理请求时出错: {str(e)}"}
        )

@router.post("/api/markdown/render")
async def render_markdown(request: Request):
    """将Markdown文本转换为HTML"""
    try:
        data = await request.json()
        markdown_text = data.get("markdown_text", "")
        
        if not markdown_text:
            return JSONResponse(content={"html": ""})
        
        # 使用Markdown处理器转换为HTML
        html_content = markdown_processor.convert_to_html(markdown_text)
        
        # 返回转换后的HTML
        return JSONResponse(content={"html": html_content})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"处理Markdown时出错: {str(e)}"}
        )

@router.get("/api/markdown/css")
async def markdown_css():
    """获取Markdown样式的CSS内容"""
    try:
        # 注意：CSS现在定义在静态文件中，此API路由保留是为了向后兼容
        # 返回空字符串，因为所有样式都已移至静态CSS文件
        return JSONResponse(content={"css": ""})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"获取Markdown CSS时出错: {str(e)}"}
        )

@router.post("/api/settings/system-prompt")
async def update_system_prompt(request: Request):
    """更新系统提示词设置，使设置立即生效"""
    try:
        data = await request.json()
        system_prompt = data.get("system_prompt", "")
        
        if not system_prompt:
            return JSONResponse(
                status_code=400,
                content={"error": "系统提示词不能为空"}
            )
        
        # 更新全局聊天实例的系统提示词
        success = chat_instance.set_system_prompt(system_prompt)
        
        if success:
            return JSONResponse(content={"status": "success", "message": "系统提示词已更新"})
        else:
            return JSONResponse(
                status_code=400,
                content={"error": "系统提示词格式无效或更新失败"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"更新系统提示词时出错: {str(e)}"}
        )

@router.post("/api/settings/update")
async def update_all_settings(request: Request):
    """更新所有聊天设置，使设置立即生效"""
    try:
        # 获取请求数据
        data = await request.json()
        
        # 提取设置参数
        system_prompt = data.get("system_prompt", None)
        memory_type = data.get("memory_type", None)
        temperature = data.get("temperature", None)
        response_style = data.get("response_style", None)
        
        # 状态跟踪
        update_status = {"status": "success"}
        
        # 1. 更新系统提示词
        if system_prompt is not None:
            try:
                success = chat_instance.set_system_prompt(system_prompt)
                update_status["system_prompt"] = success
                if not success:
                    update_status["status"] = "partial"
                    update_status["error_system_prompt"] = "系统提示词格式无效"
            except Exception as e:
                update_status["status"] = "partial"
                update_status["error_system_prompt"] = f"更新系统提示词出错: {str(e)}"
        
        # 2. 更新记忆类型
        if memory_type is not None:
            try:
                # 解析记忆类型
                memory_map = {
                    "近5轮": {"type": "window", "k": 5},
                    "近10轮": {"type": "window", "k": 10},
                    "全部": {"type": "buffer", "k": None},
                    "buffer": {"type": "buffer", "k": None},  # 直接支持buffer类型
                    "window": {"type": "window", "k": 10}     # 直接支持window类型
                }
                
                # 打印接收到的记忆类型，帮助调试
                print(f"收到记忆类型设置请求: {memory_type}")
                
                memory_config = memory_map.get(memory_type)
                if memory_config:
                    success = chat_instance.set_memory_type(memory_config["type"])
                    update_status["memory_type"] = success
                    if not success:
                        update_status["status"] = "partial"
                        update_status["error_memory_type"] = "记忆类型设置失败"
                else:
                    update_status["status"] = "partial"
                    update_status["error_memory_type"] = f"未知的记忆类型: {memory_type}"
            except Exception as e:
                update_status["status"] = "partial"
                update_status["error_memory_type"] = f"更新记忆类型出错: {str(e)}"
        
        # 3. 更新温度值
        if temperature is not None:
            try:
                # 确保温度值是浮点数
                temp_value = float(temperature)
                success = chat_instance.set_temperature(temp_value)
                update_status["temperature"] = success
                if not success:
                    update_status["status"] = "partial"
                    update_status["error_temperature"] = "温度值设置失败"
            except (ValueError, TypeError) as e:
                update_status["status"] = "partial"
                update_status["error_temperature"] = f"无效的温度值: {str(e)}"
            except Exception as e:
                update_status["status"] = "partial"
                update_status["error_temperature"] = f"更新温度值出错: {str(e)}"
        
        # 4. 更新响应风格（目前仅保存到状态，后续可添加实际实现）
        if response_style is not None:
            try:
                # 这里可以添加对响应风格的处理逻辑
                # 目前仅做记录，不实际处理
                update_status["response_style"] = True
            except Exception as e:
                update_status["status"] = "partial"
                update_status["error_response_style"] = f"响应风格更新出错: {str(e)}"
        
        # 返回更新状态
        return JSONResponse(content=update_status)
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"更新设置出错: {error_detail}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": f"更新设置时出错: {str(e)}"}
        )

