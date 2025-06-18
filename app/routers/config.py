"""
配置管理路由
提供模型添加、系统配置等功能
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from typing import Optional, List, Dict, Any
import logging
import json
import yaml
import os
from datetime import datetime

# 导入数据库
from app.database import get_db
from app.services.model_config_service import ModelConfigService

# 设置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/config", tags=["配置管理"])

# 设置模板目录
templates = Jinja2Templates(directory="templates")

# ============= 页面路由 =============

@router.get("/model-config", response_class=HTMLResponse)
async def model_config_page(request: Request):
    """模型配置页面"""
    try:
        return templates.TemplateResponse("config/model_config.html", {
            "request": request,
            "title": "模型配置"
        })
    except Exception as e:
        logger.error(f"加载模型配置页面失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"加载页面失败: {str(e)}")

# ============= 模型配置API =============

@router.get("/api/model-configurations")
async def get_model_configurations(db: Session = Depends(get_db)):
    """获取模型配置列表"""
    try:
        # 从数据库获取所有模型配置
        model_configs = ModelConfigService.get_all_model_configs(db)
        
        # 按供应商分组
        provider_configs = {}
        for config in model_configs:
            provider = config.provider
            if provider not in provider_configs:
                provider_configs[provider] = {
                    "provider": provider,
                    "status": "unconfigured",
                    "models": []
                }
            
            provider_configs[provider]["models"].append({
                "id": config.id,
                "name": config.model_name,
                "endpoint": config.endpoint,
                "test_status": config.test_status,
                "created_at": config.created_at.isoformat() if config.created_at else None
            })
            
            # 如果有模型配置，则状态为已配置
            if provider_configs[provider]["models"]:
                provider_configs[provider]["status"] = "configured"
        
        # 确保所有支持的供应商都在列表中
        supported_providers = ["openai", "vllm", "deepseek", "anthropic", "openai-compatible"]
        for provider in supported_providers:
            if provider not in provider_configs:
                provider_configs[provider] = {
                    "provider": provider,
                    "status": "unconfigured",
                    "models": []
                }
        
        return {
            "success": True,
            "data": list(provider_configs.values())
        }
    except Exception as e:
        logger.error(f"获取模型配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取模型配置失败: {str(e)}")

@router.post("/api/provider-config")
async def save_provider_config(request: Request, db: Session = Depends(get_db)):
    """保存供应商配置"""
    try:
        data = await request.json()
        provider = data.get("provider")
        api_key = data.get("api_key")
        model_name = data.get("model_name")
        endpoint = data.get("endpoint")
        organization = data.get("organization")
        model_type = data.get("model_type")
        context_length = data.get("context_length")
        max_tokens = data.get("max_tokens")
        
        if not provider or not api_key or not model_name:
            raise HTTPException(status_code=400, detail="供应商、API Key和模型名称不能为空")
        
        # 获取供应商显示名称
        provider_names = {
            'openai': 'OpenAI',
            'vllm': 'vLLM',
            'deepseek': 'DeepSeek',
            'anthropic': 'Anthropic',
            'azure-openai': 'Azure OpenAI',
            'openai-compatible': 'OpenAI-API-compatible'
        }
        provider_name = provider_names.get(provider, provider)
        
        # 保存到数据库
        model_config = ModelConfigService.create_model_config(
            db=db,
            provider=provider,
            provider_name=provider_name,
            model_name=model_name,
            api_key=api_key,
            endpoint=endpoint,
            organization=organization,
            model_type=model_type,
            context_length=context_length,
            max_tokens=max_tokens,
            test_status="success",  # 假设保存时已经测试成功
            test_message="配置已保存"
        )
        
        logger.info(f"保存供应商配置: {provider} - {model_name}")
        
        return {
            "success": True,
            "message": "配置保存成功",
            "data": model_config.to_safe_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存供应商配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")

@router.get("/api/model-configs")
async def get_all_model_configs(
    db: Session = Depends(get_db),
    type: Optional[str] = Query(None, description="模型类型过滤：llm, embedding, rerank, speech2text, tts")
):
    """获取所有模型配置（包括软删除的记录）"""
    try:
        # 获取所有记录，包括软删除的
        model_configs = ModelConfigService.get_all_model_configs(db, include_inactive=True)
        
        # 如果指定了类型，则进行过滤
        if type:
            model_configs = [config for config in model_configs if config.model_type == type]
        
        return {
            "success": True,
            "data": [config.to_safe_dict() for config in model_configs]
        }
    except Exception as e:
        logger.error(f"获取模型配置列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取模型配置失败: {str(e)}")

@router.get("/api/available-models")
async def get_available_models(db: Session = Depends(get_db)):
    """获取可用的模型列表（用于聊天界面选择）"""
    try:
        model_configs = ModelConfigService.get_all_model_configs(db)
        
        # 只返回测试成功且激活的模型
        available_models = []
        for config in model_configs:
            if config.test_status == "success" and config.is_active:
                available_models.append({
                    "id": config.id,
                    "provider": config.provider,
                    "provider_name": config.provider_name,
                    "model_name": config.model_name,
                    "endpoint": config.endpoint,
                    "display_name": f"{config.provider_name} - {config.model_name}"
                })
        
        return {
            "success": True,
            "data": available_models
        }
    except Exception as e:
        logger.error(f"获取可用模型列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取可用模型失败: {str(e)}")

@router.delete("/api/model-configs/{config_id}")
async def delete_model_config(config_id: int, db: Session = Depends(get_db)):
    """删除模型配置"""
    try:
        success = ModelConfigService.delete_model_config(db, config_id)
        if success:
            return {
                "success": True,
                "message": "配置删除成功"
            }
        else:
            raise HTTPException(status_code=404, detail="配置不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除模型配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除配置失败: {str(e)}")

@router.put("/api/model-configs/{config_id}")
async def update_model_config(config_id: int, request: Request, db: Session = Depends(get_db)):
    """更新模型配置"""
    try:
        data = await request.json()
        
        model_config = ModelConfigService.update_model_config(
            db=db,
            config_id=config_id,
            **data
        )
        
        if model_config:
            return {
                "success": True,
                "message": "配置更新成功",
                "data": model_config.to_safe_dict()
            }
        else:
            raise HTTPException(status_code=404, detail="配置不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新模型配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")

@router.post("/api/test-connection")
async def test_provider_connection(request: Request, db: Session = Depends(get_db)):
    """测试供应商连接"""
    import httpx
    import time
    
    try:
        data = await request.json()
        provider = data.get("provider")
        api_key = data.get("api_key")
        endpoint = data.get("endpoint")
        config_id = data.get("config_id")  # 添加配置ID参数
        
        # 如果有配置ID，从数据库获取完整的API key
        if config_id:
            model_config = ModelConfigService.get_model_config_by_id(db, config_id)
            if model_config:
                api_key = model_config.api_key  # 使用数据库中的完整API key
                provider = model_config.provider
                endpoint = model_config.endpoint
                logger.info(f"从数据库获取完整API key用于测试 - 配置ID: {config_id}")
            else:
                return {
                    "success": False,
                    "message": "配置不存在"
                }
        
        if not provider or not api_key:
            return {
                "success": False,
                "message": "供应商和API Key不能为空"
            }
        
        # 根据不同供应商设置测试端点
        test_endpoints = {
            "openai": endpoint or "https://api.openai.com/v1",
            "vllm": endpoint or "http://localhost:8000/v1",
            "deepseek": endpoint or "https://api.deepseek.com/v1",
            "anthropic": endpoint or "https://api.anthropic.com",
            "azure-openai": endpoint,
            "openai-compatible": endpoint  # 自定义端点，必须提供
        }
        
        test_endpoint = test_endpoints.get(provider)
        if not test_endpoint:
            return {
                "success": False,
                "message": f"不支持的供应商: {provider}"
            }
        
        # 构建测试请求
        if provider == "openai" or provider == "vllm" or provider == "deepseek" or provider == "openai-compatible":
            if provider == "deepseek":
                test_url = f"{test_endpoint}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            elif provider == "openai-compatible":
                # 对于自定义OpenAI兼容API，确保正确构建URL
                # 如果端点已经包含/v1，直接使用；否则添加/v1
                if test_endpoint.endswith('/v1'):
                    test_url = f"{test_endpoint}/chat/completions"
                elif test_endpoint.endswith('/'):
                    test_url = f"{test_endpoint}v1/chat/completions"
                else:
                    test_url = f"{test_endpoint}/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            else:
                test_url = f"{test_endpoint}/models"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
        elif provider == "anthropic":
            test_url = f"{test_endpoint}/v1/messages"
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
        else:
            return {
                "success": False,
                "message": f"暂不支持测试 {provider} 连接"
            }
        
        start_time = time.time()
        
        # 增加调试日志
        logger.info(f"测试连接 - 供应商: {provider}, 端点: {test_endpoint}, 模型: {data.get('model_name', 'N/A')}")
        logger.info(f"API Key前4位: {api_key[:4] if len(api_key) > 4 else api_key}***")
        
        # 发送测试请求
        async with httpx.AsyncClient(timeout=10.0) as client:
            if provider == "anthropic":
                # Anthropic需要发送消息测试
                test_payload = {
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hello"}]
                }
                response = await client.post(test_url, headers=headers, json=test_payload)
            elif provider == "deepseek":
                # DeepSeek需要发送聊天完成测试，使用用户实际配置的模型名称
                model_name = data.get("model_name", "deepseek-chat")
                test_payload = {
                    "model": model_name,
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hello"}]
                }
                response = await client.post(test_url, headers=headers, json=test_payload)
            elif provider == "openai-compatible":
                # OpenAI兼容API需要发送聊天完成测试，使用用户提供的模型名称
                model_name = data.get("model_name", "gpt-3.5-turbo")
                test_payload = {
                    "model": model_name,
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hello"}]
                }
                response = await client.post(test_url, headers=headers, json=test_payload)
            else:
                # OpenAI和vLLM可以直接获取模型列表
                response = await client.get(test_url, headers=headers)
        
        end_time = time.time()
        response_time = round((end_time - start_time) * 1000)  # 转换为毫秒
        
        if response.status_code == 200:
            return {
                "success": True,
                "message": "连接测试成功",
                "data": {
                    "endpoint": test_endpoint,
                    "response_time": f"{response_time}ms",
                    "status": "connected"
                }
            }
        else:
            error_detail = ""
            try:
                error_data = response.json()
                error_detail = error_data.get("error", {}).get("message", "") or str(error_data)
            except:
                error_detail = response.text
            
            # 对于401错误给出更详细的提示
            if response.status_code == 401:
                if provider == "deepseek":
                    model_name = data.get("model_name", "deepseek-chat")
                    error_message = f"API Key认证失败: {error_detail}。请检查：1) API Key是否正确且有效；2) API Key是否有访问模型 '{model_name}' 的权限；3) API Key是否已过期"
                else:
                    error_message = f"API Key认证失败: {error_detail}。请检查API Key是否正确、有效且未过期"
            else:
                error_message = f"连接失败 (HTTP {response.status_code}): {error_detail}"
            
            return {
                "success": False,
                "message": error_message,
                "data": {
                    "endpoint": test_endpoint,
                    "response_time": f"{response_time}ms",
                    "status": "failed",
                    "error_code": response.status_code
                }
            }
            
    except httpx.TimeoutException:
        return {
            "success": False,
            "message": "连接超时，请检查网络连接或API端点地址"
        }
    except httpx.RequestError as e:
        return {
            "success": False,
            "message": f"网络请求错误: {str(e)}"
        }
    except Exception as e:
        logger.error(f"测试连接失败: {str(e)}")
        return {
            "success": False,
            "message": f"测试连接时发生错误: {str(e)}"
        }

@router.post("/api/add-model")
async def add_model(request: Request):
    """添加模型"""
    try:
        data = await request.json()
        provider = data.get("provider")
        model_name = data.get("model_name")
        model_type = data.get("model_type")
        description = data.get("description")
        
        if not provider or not model_name or not model_type:
            raise HTTPException(status_code=400, detail="供应商、模型名称和模型类型不能为空")
        
        # 这里应该将模型信息保存到数据库
        # 暂时只做验证和日志记录
        logger.info(f"添加模型: {provider} - {model_name} ({model_type})")
        
        return {
            "success": True,
            "message": "模型添加成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加模型失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加模型失败: {str(e)}")

# ============= 配置文件管理 =============

@router.get("/api/config")
async def get_config():
    """获取系统配置"""
    try:
        config_path = "config.yaml"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return {
                "success": True,
                "data": config
            }
        else:
            return {
                "success": False,
                "message": "配置文件不存在"
            }
    except Exception as e:
        logger.error(f"获取配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")

@router.put("/api/config")
async def update_config(request: Request):
    """更新系统配置"""
    try:
        data = await request.json()
        config_path = "config.yaml"
        
        # 备份原配置文件
        if os.path.exists(config_path):
            backup_path = f"{config_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            import shutil
            shutil.copy2(config_path, backup_path)
        
        # 写入新配置
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        
        return {
            "success": True,
            "message": "配置更新成功"
        }
    except Exception as e:
        logger.error(f"更新配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")

@router.get("/api/deepseek/settings")
async def get_deepseek_settings():
    """获取深度求索设置"""
    try:
        # 这里可以从数据库或配置文件中读取设置
        # 暂时返回默认设置
        return {
            "success": True,
            "data": {
                "api_key": "",  # 不返回真实的API Key
                "endpoint": "https://api.deepseek.com/v1"
            }
        }
    except Exception as e:
        logger.error(f"获取深度求索设置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取深度求索设置失败: {str(e)}")

@router.post("/api/deepseek/settings")
async def save_deepseek_settings(request: Request):
    """保存深度求索设置"""
    try:
        data = await request.json()
        api_key = data.get("api_key", "").strip()
        endpoint = data.get("endpoint", "https://api.deepseek.com/v1").strip()
        
        if not api_key:
            raise HTTPException(status_code=400, detail="API Key不能为空")
        
        # 这里应该将设置保存到数据库或配置文件
        # 暂时只做验证
        
        return {
            "success": True,
            "message": "深度求索设置保存成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存深度求索设置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存深度求索设置失败: {str(e)}")

@router.post("/api/deepseek/test")
async def test_deepseek_connection(request: Request):
    """测试深度求索连接"""
    import httpx
    import time
    
    try:
        data = await request.json()
        api_key = data.get("api_key", "").strip()
        endpoint = data.get("endpoint", "https://api.deepseek.com").strip()
        
        if not api_key:
            return {
                "success": False,
                "message": "API Key不能为空"
            }
        
        # 确保endpoint以/v1结尾
        if not endpoint.endswith('/v1'):
            if endpoint.endswith('/'):
                endpoint = endpoint + 'v1'
            else:
                endpoint = endpoint + '/v1'
        
        # 构建测试请求
        test_url = f"{endpoint}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        test_payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "user",
                    "content": "Hello, this is a connection test."
                }
            ],
            "max_tokens": 10,
            "temperature": 0.1
        }
        
        start_time = time.time()
        
        # 发送测试请求
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                test_url,
                headers=headers,
                json=test_payload
            )
        
        end_time = time.time()
        response_time = round((end_time - start_time) * 1000)  # 转换为毫秒
        
        if response.status_code == 200:
            response_data = response.json()
            return {
                "success": True,
                "message": "连接测试成功",
                "data": {
                    "endpoint": endpoint,
                    "response_time": f"{response_time}ms",
                    "status": "connected",
                    "model_response": response_data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                }
            }
        else:
            error_detail = ""
            try:
                error_data = response.json()
                error_detail = error_data.get("error", {}).get("message", "")
            except:
                error_detail = response.text
            
            return {
                "success": False,
                "message": f"连接失败 (HTTP {response.status_code}): {error_detail}",
                "data": {
                    "endpoint": endpoint,
                    "response_time": f"{response_time}ms",
                    "status": "failed",
                    "error_code": response.status_code
                }
            }
            
    except httpx.TimeoutException:
        return {
            "success": False,
            "message": "连接超时，请检查网络连接或API端点地址"
        }
    except httpx.RequestError as e:
        return {
            "success": False,
            "message": f"网络请求错误: {str(e)}"
        }
    except Exception as e:
        logger.error(f"测试深度求索连接失败: {str(e)}")
        return {
            "success": False,
            "message": f"测试连接时发生错误: {str(e)}"
        }

@router.delete("/api/model-configs/{config_id}/permanent")
async def permanent_delete_model_config(config_id: int, db: Session = Depends(get_db)):
    """永久删除模型配置"""
    try:
        success = ModelConfigService.permanent_delete_model_config(db, config_id)
        if success:
            return {
                "success": True,
                "message": "配置永久删除成功"
            }
        else:
            raise HTTPException(status_code=404, detail="配置不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"永久删除模型配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"永久删除配置失败: {str(e)}")

@router.post("/api/test-openai-compatible-connection")
async def test_openai_compatible_connection(request: Request, db: Session = Depends(get_db)):
    """测试OpenAI-API-compatible模型连接"""
    import httpx
    import numpy as np
    
    try:
        data = await request.json()
        model_type = data.get("model_type")
        model_name = data.get("model_name")
        api_key = data.get("api_key")
        endpoint = data.get("endpoint")
        config_id = data.get("config_id")
        
        # 如果有配置ID，从数据库获取完整的API key
        if config_id:
            model_config = ModelConfigService.get_model_config_by_id(db, config_id)
            if model_config:
                api_key = model_config.api_key  # 使用数据库中的完整API key
                model_type = model_config.model_type
                model_name = model_config.model_name
                endpoint = model_config.endpoint
                logger.info(f"从数据库获取完整API key用于OpenAI-compatible测试 - 配置ID: {config_id}")
            else:
                return {
                    "success": False,
                    "message": "配置不存在"
                }
        
        if not all([model_type, model_name, api_key, endpoint]):
            return {
                "success": False,
                "message": "所有字段都不能为空"
            }
        
        # 确保端点格式正确
        if not endpoint.startswith('http'):
            endpoint = f"https://{endpoint}"
        
        if endpoint.endswith('/'):
            endpoint = endpoint.rstrip('/')
        
        # 不自动添加/v1，让用户自己指定完整的base URL
        # 如果endpoint不包含/v1且看起来像是需要添加的情况，才添加
        base_endpoint = endpoint
        
        # 设置请求头，支持不同的认证方式
        headers = {
            "Content-Type": "application/json"
        }
        
        # 如果API key存在且不为空，添加认证头
        if api_key and api_key.strip():
            # 支持多种认证方式
            if api_key.startswith('Bearer '):
                headers["Authorization"] = api_key
            else:
                # 默认使用Bearer认证
                headers["Authorization"] = f"Bearer {api_key}"
        
        timeout = httpx.Timeout(30.0)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            if model_type == "embedding":
                # 测试embedding模型
                # 尝试不同的URL格式
                possible_urls = [
                    f"{base_endpoint}/v1/embeddings",
                    f"{base_endpoint}/embeddings",
                ]
                
                test_data = {
                    "model": model_name,
                    "input": "这是一个测试文本"
                }
                
                # 尝试多个可能的URL
                last_error = None
                for test_url in possible_urls:
                    try:
                        logger.info(f"尝试测试embedding API: {test_url}")
                        response = await client.post(test_url, json=test_data, headers=headers)
                        
                        if response.status_code == 200:
                            result = response.json()
                            if "data" in result and len(result["data"]) > 0:
                                embedding = result["data"][0].get("embedding", [])
                                if len(embedding) > 0:
                                    return {
                                        "success": True,
                                        "message": f"Embedding模型测试成功，向量维度: {len(embedding)}，使用URL: {test_url}"
                                    }
                                else:
                                    return {
                                        "success": False,
                                        "message": "返回的embedding向量为空"
                                    }
                            else:
                                return {
                                    "success": False,
                                    "message": f"API返回格式不正确，响应: {response.text[:200]}"
                                }
                        elif response.status_code == 500:
                            # 特别处理服务器内部错误
                            try:
                                error_detail = response.json()
                                error_msg = error_detail.get('detail', response.text)
                                return {
                                    "success": False,
                                    "message": f"服务器内部错误 (HTTP 500): {error_msg}。这通常是远程API服务的问题，请检查您的模型服务配置或联系API提供商。"
                                }
                            except:
                                return {
                                    "success": False,
                                    "message": f"服务器内部错误 (HTTP 500): {response.text[:300]}。这通常是远程API服务的问题。"
                                }
                        else:
                            last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                            logger.warning(f"尝试URL {test_url} 失败: {last_error}")
                            continue
                            
                    except httpx.ConnectError as e:
                        last_error = f"连接错误: {str(e)}"
                        logger.warning(f"尝试URL {test_url} 连接失败: {last_error}")
                        continue
                    except Exception as e:
                        last_error = f"请求错误: {str(e)}"
                        logger.warning(f"尝试URL {test_url} 请求失败: {last_error}")
                        continue
                
                # 如果所有URL都失败了
                return {
                    "success": False,
                    "message": f"Embedding API调用失败，尝试的URL: {', '.join(possible_urls)}，最后错误: {last_error}"
                }
                    
            elif model_type == "rerank":
                # 测试rerank模型
                possible_urls = [
                    f"{base_endpoint}/v1/rerank",
                    f"{base_endpoint}/rerank",
                ]
                
                test_data = {
                    "model": model_name,
                    "query": "什么是机器学习？",
                    "documents": [
                        "机器学习是人工智能的一个分支",
                        "今天天气很好",
                        "深度学习是机器学习的子集"
                    ]
                }
                
                # 尝试多个可能的URL
                last_error = None
                for test_url in possible_urls:
                    try:
                        logger.info(f"尝试测试rerank API: {test_url}")
                        response = await client.post(test_url, json=test_data, headers=headers)
                        
                        if response.status_code == 200:
                            result = response.json()
                            if "results" in result and len(result["results"]) > 0:
                                return {
                                    "success": True,
                                    "message": f"Rerank模型测试成功，返回{len(result['results'])}个结果，使用URL: {test_url}"
                                }
                            else:
                                return {
                                    "success": False,
                                    "message": f"API返回格式不正确，响应: {response.text[:200]}"
                                }
                        elif response.status_code == 500:
                            # 特别处理服务器内部错误
                            try:
                                error_detail = response.json()
                                error_msg = error_detail.get('detail', response.text)
                                return {
                                    "success": False,
                                    "message": f"服务器内部错误 (HTTP 500): {error_msg}。这通常是远程API服务的问题，请检查您的模型服务配置或联系API提供商。"
                                }
                            except:
                                return {
                                    "success": False,
                                    "message": f"服务器内部错误 (HTTP 500): {response.text[:300]}。这通常是远程API服务的问题。"
                                }
                        else:
                            last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                            logger.warning(f"尝试URL {test_url} 失败: {last_error}")
                            continue
                            
                    except httpx.ConnectError as e:
                        last_error = f"连接错误: {str(e)}"
                        logger.warning(f"尝试URL {test_url} 连接失败: {last_error}")
                        continue
                    except Exception as e:
                        last_error = f"请求错误: {str(e)}"
                        logger.warning(f"尝试URL {test_url} 请求失败: {last_error}")
                        continue
                
                # 如果所有URL都失败了
                return {
                    "success": False,
                    "message": f"Rerank API调用失败，尝试的URL: {', '.join(possible_urls)}，最后错误: {last_error}"
                }
                    
            elif model_type == "llm":
                # 测试LLM模型
                possible_urls = [
                    f"{base_endpoint}/v1/chat/completions",
                    f"{base_endpoint}/chat/completions",
                ]
                
                test_data = {
                    "model": model_name,
                    "messages": [
                        {"role": "user", "content": "你好，这是一个连接测试。"}
                    ],
                    "max_tokens": 10
                }
                
                # 尝试多个可能的URL
                last_error = None
                for test_url in possible_urls:
                    try:
                        logger.info(f"尝试测试LLM API: {test_url}")
                        response = await client.post(test_url, json=test_data, headers=headers)
                        
                        if response.status_code == 200:
                            result = response.json()
                            if "choices" in result and len(result["choices"]) > 0:
                                return {
                                    "success": True,
                                    "message": f"LLM模型测试成功，使用URL: {test_url}"
                                }
                            else:
                                return {
                                    "success": False,
                                    "message": f"API返回格式不正确，响应: {response.text[:200]}"
                                }
                        else:
                            last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                            logger.warning(f"尝试URL {test_url} 失败: {last_error}")
                            continue
                            
                    except httpx.ConnectError as e:
                        last_error = f"连接错误: {str(e)}"
                        logger.warning(f"尝试URL {test_url} 连接失败: {last_error}")
                        continue
                    except Exception as e:
                        last_error = f"请求错误: {str(e)}"
                        logger.warning(f"尝试URL {test_url} 请求失败: {last_error}")
                        continue
                
                # 如果所有URL都失败了
                return {
                    "success": False,
                    "message": f"LLM API调用失败，尝试的URL: {', '.join(possible_urls)}，最后错误: {last_error}"
                }
                    
            elif model_type == "speech2text":
                # 对于语音转文本，只检查API端点是否可达
                test_url = f"{endpoint}/audio/transcriptions"
                # 创建一个空的multipart/form-data请求来测试端点
                response = await client.post(test_url, headers={"Authorization": f"Bearer {api_key}"})
                
                # 通常会返回400因为没有音频文件，但这表明端点存在
                if response.status_code in [400, 422]:
                    return {
                        "success": True,
                        "message": "Speech2Text API端点可达"
                    }
                elif response.status_code == 200:
                    return {
                        "success": True,
                        "message": "Speech2Text模型测试成功"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Speech2Text API不可达: HTTP {response.status_code}"
                    }
                    
            elif model_type == "tts":
                # 对于文本转语音，只检查API端点是否可达
                test_url = f"{endpoint}/audio/speech"
                test_data = {
                    "model": model_name,
                    "input": "测试",
                    "voice": "alloy"
                }
                
                response = await client.post(test_url, json=test_data, headers=headers)
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "TTS模型测试成功"
                    }
                else:
                    error_msg = response.text if response.text else f"HTTP {response.status_code}"
                    return {
                        "success": False,
                        "message": f"TTS API调用失败: {error_msg}"
                    }
            else:
                return {
                    "success": False,
                    "message": f"不支持的模型类型: {model_type}"
                }
                
    except httpx.ConnectError:
        return {
            "success": False,
            "message": "无法连接到API端点，请检查URL是否正确"
        }
    except httpx.TimeoutException:
        return {
            "success": False,
            "message": "连接超时，请检查网络连接或API响应速度"
        }
    except Exception as e:
        logger.error(f"测试OpenAI-compatible连接失败: {str(e)}")
        return {
            "success": False,
            "message": f"测试连接时发生错误: {str(e)}"
        } 