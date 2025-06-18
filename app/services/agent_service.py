"""
智能体数据库操作服务
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional, Tuple
from datetime import datetime
import logging
import math

from app.models.agent import Agent, AgentCategory, AgentStatus, AgentTemplate
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse, AgentListResponse
from app.database import get_db

logger = logging.getLogger(__name__)

class AgentService:
    """智能体服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_agent(self, agent_data: AgentCreate, creator_id: int = 1, creator_name: str = "系统用户") -> AgentResponse:
        """创建智能体"""
        try:
            # 根据模板生成系统提示词
            system_prompt = self._generate_system_prompt(agent_data)
            
            # 创建智能体实例
            db_agent = Agent(
                name=agent_data.name,
                description=agent_data.description,
                problem_description=agent_data.problem_description,
                answer_description=agent_data.answer_description,
                category=AgentCategory(agent_data.category) if agent_data.category else AgentCategory.OTHER,
                template=AgentTemplate(agent_data.template) if agent_data.template else AgentTemplate.SIMPLE,
                system_prompt=agent_data.system_prompt or system_prompt,
                is_public=agent_data.is_public if agent_data.is_public is not None else False,
                creator_id=creator_id,
                creator_name=creator_name,
                status=AgentStatus.ACTIVE
            )
            
            self.db.add(db_agent)
            self.db.commit()
            self.db.refresh(db_agent)
            
            logger.info(f"创建智能体成功: {db_agent.name} (ID: {db_agent.id})")
            return self._to_agent_response(db_agent)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建智能体失败: {e}")
            raise e
    
    def get_agent(self, agent_id: int) -> AgentResponse:
        """根据ID获取智能体"""
        db_agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not db_agent:
            raise ValueError(f"智能体 {agent_id} 不存在")
        return self._to_agent_response(db_agent)
    
    def get_agent_by_id(self, agent_id: int) -> Optional[Agent]:
        """根据ID获取智能体原始对象"""
        return self.db.query(Agent).filter(Agent.id == agent_id).first()
    
    def get_agents(self, page: int = 1, page_size: int = 10, **filters) -> AgentListResponse:
        """获取智能体列表（分页）"""
        try:
            query = self.db.query(Agent)
            
            # 搜索过滤
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                query = query.filter(
                    or_(
                        Agent.name.ilike(search_term),
                        Agent.description.ilike(search_term)
                    )
                )
            
            # 分类过滤
            if filters.get('category'):
                query = query.filter(Agent.category == AgentCategory(filters['category']))
            
            # 状态过滤
            if filters.get('status'):
                query = query.filter(Agent.status == AgentStatus(filters['status']))
            
            # 公开性过滤
            if filters.get('is_public') is not None:
                query = query.filter(Agent.is_public == filters['is_public'])
            
            # 创建者过滤
            if filters.get('creator_id'):
                query = query.filter(Agent.creator_id == filters['creator_id'])
            
            # 获取总数
            total = query.count()
            
            # 分页
            offset = (page - 1) * page_size
            agents = query.order_by(Agent.updated_at.desc()).offset(offset).limit(page_size).all()
            
            # 转换为响应格式
            agent_responses = [self._to_agent_response(agent) for agent in agents]
            
            # 计算总页数
            pages = math.ceil(total / page_size) if total > 0 else 1
            
            return AgentListResponse(
                agents=agent_responses,
                total=total,
                page=page,
                page_size=page_size,
                pages=pages
            )
            
        except Exception as e:
            logger.error(f"获取智能体列表失败: {e}")
            raise e
    
    def update_agent(self, agent_id: int, update_data: AgentUpdate) -> AgentResponse:
        """更新智能体"""
        try:
            db_agent = self.get_agent_by_id(agent_id)
            if not db_agent:
                raise ValueError(f"智能体 {agent_id} 不存在")
            
            # 更新字段
            update_dict = update_data.dict(exclude_unset=True)
            for field, value in update_dict.items():
                if field == "category" and value:
                    setattr(db_agent, field, AgentCategory(value))
                elif field == "status" and value:
                    setattr(db_agent, field, AgentStatus(value))
                elif field == "template" and value:
                    setattr(db_agent, field, AgentTemplate(value))
                else:
                    setattr(db_agent, field, value)
            
            # 更新时间
            db_agent.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(db_agent)
            
            logger.info(f"更新智能体成功: {db_agent.name} (ID: {db_agent.id})")
            return self._to_agent_response(db_agent)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新智能体失败: {e}")
            raise e
    
    def delete_agent(self, agent_id: int) -> AgentResponse:
        """删除智能体"""
        try:
            db_agent = self.get_agent_by_id(agent_id)
            if not db_agent:
                raise ValueError(f"智能体 {agent_id} 不存在")
            
            # 保存删除前的信息用于返回
            deleted_agent = self._to_agent_response(db_agent)
            
            self.db.delete(db_agent)
            self.db.commit()
            
            logger.info(f"删除智能体成功: {db_agent.name} (ID: {agent_id})")
            return deleted_agent
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除智能体失败: {e}")
            raise e
    
    def copy_agent(self, agent_id: int, creator_id: int = 1, creator_name: str = "系统用户") -> AgentResponse:
        """复制智能体"""
        try:
            original_agent = self.get_agent_by_id(agent_id)
            if not original_agent:
                raise ValueError(f"原智能体 {agent_id} 不存在")
            
            # 创建副本
            new_agent = Agent(
                name=f"{original_agent.name} - 副本",
                description=original_agent.description,
                problem_description=original_agent.problem_description,
                answer_description=original_agent.answer_description,
                category=original_agent.category,
                template=original_agent.template,
                system_prompt=original_agent.system_prompt,
                is_public=False,  # 副本默认不公开
                creator_id=creator_id,
                creator_name=creator_name,
                status=AgentStatus.ACTIVE
            )
            
            self.db.add(new_agent)
            self.db.commit()
            self.db.refresh(new_agent)
            
            logger.info(f"复制智能体成功: {original_agent.name} -> {new_agent.name} (ID: {new_agent.id})")
            return self._to_agent_response(new_agent)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"复制智能体失败: {e}")
            raise e
    
    def increment_usage_count(self, agent_id: int) -> bool:
        """增加使用次数"""
        try:
            db_agent = self.get_agent_by_id(agent_id)
            if not db_agent:
                return False
            
            db_agent.usage_count = (db_agent.usage_count or 0) + 1
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"增加使用次数失败: {e}")
            return False
    
    def get_category_statistics(self) -> dict:
        """获取分类统计"""
        try:
            stats = {}
            
            # 获取各分类的数量
            for category in AgentCategory:
                count = self.db.query(Agent).filter(Agent.category == category).count()
                stats[category.value] = count
            
            # 总数
            stats['total'] = sum(stats.values())
            
            return stats
            
        except Exception as e:
            logger.error(f"获取分类统计失败: {e}")
            return {}
    
    def _to_agent_response(self, db_agent: Agent) -> AgentResponse:
        """将数据库Agent对象转换为AgentResponse"""
        return AgentResponse(
            id=db_agent.id,
            name=db_agent.name,
            description=db_agent.description,
            problem_description=db_agent.problem_description,
            answer_description=db_agent.answer_description,
            category=db_agent.category.value,
            category_display=Agent.get_category_display_name(db_agent.category),
            template=db_agent.template.value,
            template_display=Agent.get_template_display_name(db_agent.template),
            system_prompt=db_agent.system_prompt,
            status=db_agent.status.value,
            status_display=Agent.get_status_display_name(db_agent.status),
            is_public=db_agent.is_public,
            usage_count=db_agent.usage_count or 0,
            creator_id=db_agent.creator_id,
            creator_name=db_agent.creator_name,
            created_at=db_agent.created_at,
            updated_at=db_agent.updated_at
        )
    
    def _generate_system_prompt(self, agent_data: AgentCreate) -> str:
        """根据智能体数据生成系统提示词"""
        try:
            base_prompt = "你是一个智能助手。"
            
            if agent_data.problem_description:
                base_prompt += f"\n\n问题背景：{agent_data.problem_description}"
            
            if agent_data.answer_description:
                base_prompt += f"\n\n回答要求：{agent_data.answer_description}"
            
            # 根据模板调整提示词
            template_prompts = {
                "simple": "请以简洁明了的方式回答用户问题。",
                "multi-agent": "你需要与其他智能体协作完成复杂任务。",
                "chat-guide": "请在对话开始时提供适当的引导。",
                "knowledge-time": "你可以获取当前时间信息来辅助回答。"
            }
            
            if agent_data.template and agent_data.template in template_prompts:
                base_prompt += f"\n\n{template_prompts[agent_data.template]}"
            
            return base_prompt
            
        except Exception as e:
            logger.error(f"生成系统提示词失败: {e}")
            return "你是一个智能助手，请尽力帮助用户解决问题。"

def get_agent_service(db: Session = None) -> AgentService:
    """获取智能体服务实例"""
    if db is None:
        db = next(get_db())
    return AgentService(db) 